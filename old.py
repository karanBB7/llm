from flask import Flask, request, jsonify
from langchain.schema import HumanMessage, SystemMessage, AIMessage
from langchain.chat_models import ChatOpenAI
from dotenv import load_dotenv
import threading
import os
import time
from collections import defaultdict
from datetime import datetime
import logging
from typing import Dict, Tuple, Optional
import requests
import json
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

app = Flask(__name__)

Conversation = Dict[str, any]
ConversationKey = Tuple[str, str]

CLEANUP_INTERVAL = 600  
MAX_CONVERSATION_LENGTH = 50
DATA_DIRECTORY = Path("doctor_data")  
CACHE_FILE = DATA_DIRECTORY / "cache_index.json"
CACHE_REFRESH_INTERVAL = 3600  

DATA_DIRECTORY.mkdir(exist_ok=True)

# Locks and caches
file_lock = threading.Lock()
conversations: Dict[ConversationKey, Conversation] = defaultdict(dict)
conversation_lock = threading.Lock()
doctor_data_cache: Dict[str, str] = {}
cache_lock = threading.Lock()
last_cache_refresh = time.time()

def load_cache_index():
    """Load the cache index from file if it exists"""
    try:
        if CACHE_FILE.exists():
            with open(CACHE_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error loading cache index: {e}")
    return {}

def save_cache_index(index):
    """Save the cache index to file"""
    try:
        with open(CACHE_FILE, 'w') as f:
            json.dump(index, f)
    except Exception as e:
        logger.error(f"Error saving cache index: {e}")

def get_doctor_file_path(doctor_name: str) -> Path:
    """Get the file path for a doctor's data"""
    return DATA_DIRECTORY / f"doctorsData/{doctor_name}.txt"

def scrape_doctor_data(doctor_name: str) -> Tuple[bool, Optional[str]]:
    """
    Attempt to scrape doctor data and save it to a file.
    Returns a tuple of (success, error_message)
    """
    try:
        response = requests.post(
            'http://localhost:5001/scrape-doctor',
            json={'doctor_username': doctor_name},
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                # Check if the file exists in response
                if 'data' in data:  
                    try:
                        with open(f"doctorsData/{doctor_name}.txt", 'w', encoding='utf-8') as file:
                            file.write(data['data'])
                        logger.info(f"Successfully scraped and saved data for {doctor_name}")
                        return True, None
                    except Exception as e:
                        error_msg = f"Error saving scraped data: {str(e)}"
                        logger.error(error_msg)
                        return False, error_msg
                else:
                    return True, None  
            else:
                error_msg = data.get('message', 'Unknown error during scraping')
                logger.error(f"Scraping failed for {doctor_name}: {error_msg}")
                return False, error_msg
        else:
            error_msg = f"Scraping service returned status code {response.status_code}"
            logger.error(error_msg)
            return False, error_msg
            
    except requests.exceptions.RequestException as e:
        error_msg = f"Error connecting to scraping service: {str(e)}"
        logger.error(error_msg)
        return False, error_msg

def get_doctor_data(doctor_name: str) -> Optional[str]:
    """
    Retrieve doctor data from cache or file system, scrape if needed.
    """
    with cache_lock:
        if doctor_name in doctor_data_cache:
            return doctor_data_cache[doctor_name]
        
        with file_lock:
            try:
                with open(f"doctorsData/{doctor_name}.txt", 'r', encoding='utf-8') as file:
                    data = file.read()
                    doctor_data_cache[doctor_name] = data
                    logger.info(f"Successfully loaded doctor data for {doctor_name}")
                    return data
            except FileNotFoundError:
                logger.info(f"Doctor data file not found for {doctor_name}, attempting to scrape...")
                
                success, error_msg = scrape_doctor_data(doctor_name)
                
                if success:
                    try:
                        with open(f"doctorsData/{doctor_name}.txt", 'r', encoding='utf-8') as file:
                            data = file.read()
                            doctor_data_cache[doctor_name] = data
                            logger.info(f"Successfully loaded newly scraped data for {doctor_name}")
                            return data
                    except Exception as e:
                        logger.error(f"Error reading newly scraped file for {doctor_name}: {e}")
                        return None
                else:
                    logger.error(f"Failed to scrape data for {doctor_name}: {error_msg}")
                    return None
            except Exception as e:
                logger.error(f"Error reading doctor data for {doctor_name}: {e}")
                return None

def clear_old_cache_entries():
    """Periodically clear old cache entries"""
    global last_cache_refresh
    current_time = time.time()
    
    if current_time - last_cache_refresh > CACHE_REFRESH_INTERVAL:
        with cache_lock:
            doctor_data_cache.clear()
            last_cache_refresh = current_time
            logger.info("Cleared doctor data cache")

def cleanup_old_conversations() -> None:
    """Periodically remove old conversations to prevent memory leaks."""
    while True:
        try:
            current_time = time.time()
            with conversation_lock:
                keys_to_remove = [
                    key for key, value in conversations.items()
                    if current_time - value["last_access"] > CLEANUP_INTERVAL
                ]
                for key in keys_to_remove:
                    conversations.pop(key, None)
            
            clear_old_cache_entries()
            
            time.sleep(60)
        except Exception as e:
            logger.error(f"Error in cleanup thread: {e}")

def get_or_create_conversation(doctor_name: str, user_number: str) -> Optional[list]:
    """Get or create a conversation efficiently."""
    conversation_key = (doctor_name, user_number)
    current_time = time.time()
    
    with conversation_lock:
        if conversation_key in conversations:
            conversations[conversation_key]["last_access"] = current_time
            if len(conversations[conversation_key]["messages"]) > MAX_CONVERSATION_LENGTH:
                conversations[conversation_key]["messages"] = [
                    conversations[conversation_key]["messages"][0]
                ] + conversations[conversation_key]["messages"][-(MAX_CONVERSATION_LENGTH-1):]
            return conversations[conversation_key]["messages"]

        doctor_data = get_doctor_data(doctor_name)
        if doctor_data is None:
            return None
        
        conversations[conversation_key] = {
            "messages": [
                SystemMessage(content=f"""You are a Doctor AI assistant. Here is the doctor's information:
                {doctor_data}
                
                Important guidelines:
                - Answer questions based ONLY on the provided information
                - If information is not available, respond with 'I don't have that information in my records'
                - Keep responses professional and medical in nature
                - Never make assumptions about medical conditions or treatments""")
            ],
            "last_access": current_time
        }
        return conversations[conversation_key]["messages"]

@app.route('/ask', methods=['POST'])
def ask_question():
    """Handle incoming questions efficiently."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        required_fields = ['question', 'doctorusername', 'usernumber']
        if missing_fields := [field for field in required_fields if field not in data]:
            return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400
        
        question = data['question'].strip()
        doctor_name = data['doctorusername'].strip()
        user_number = str(data['usernumber']).strip()
        
        if not question:
            return jsonify({"error": "Question cannot be empty"}), 400
        
        if not (conversation := get_or_create_conversation(doctor_name, user_number)):
            return jsonify({
                "error": f"Unable to retrieve doctor data for: {doctor_name}",
                "details": "Doctor data not available and scraping failed"
            }), 404
        
        chat = ChatOpenAI(
            temperature=0.6,
            max_tokens=500,
            timeout=30
        )
        
        with conversation_lock:
            conversation.append(HumanMessage(content=question))
            try:
                response = chat(conversation)
                conversation.append(AIMessage(content=response.content))
                conversations[(doctor_name, user_number)]["last_access"] = time.time()
            except Exception as e:
                logger.error(f"Error getting AI response: {e}")
                conversation.pop()
                raise
        
        return jsonify({
            "answer": response.content,
            "doctor": doctor_name,
            "user": user_number,
            "timestamp": datetime.now().isoformat(),
            "conversation_length": len(conversation)
        })
        
    except Exception as e:
        logger.error(f"Error processing request: {e}")
        return jsonify({
            "error": "An error occurred processing your request",
            "details": str(e)
        }), 500

cleanup_thread = threading.Thread(target=cleanup_old_conversations, daemon=True)
cleanup_thread.start()

if __name__ == '__main__':
    app.run(debug=True, threaded=True)