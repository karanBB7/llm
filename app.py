from flask import Flask, request, jsonify
from langchain.schema import HumanMessage, SystemMessage, AIMessage
from langchain.chat_models import ChatOpenAI
from dotenv import load_dotenv
import threading
import os
import time
from collections import defaultdict
from datetime import datetime

load_dotenv()

app = Flask(__name__)

file_lock = threading.Lock()

# Modified conversation structure to include timestamps
# Format: {(doctor_name, user_number): {"messages": conversation_list, "last_access": timestamp}}
conversations = defaultdict(dict)
conversation_lock = threading.Lock()

doctor_data_cache = {}
cache_lock = threading.Lock()

CLEANUP_INTERVAL = 600  # 10 minutes in seconds

def cleanup_old_conversations():
    """Background thread to clean up inactive conversations"""
    while True:
        current_time = time.time()
        with conversation_lock:
            # Create a list of keys to remove to avoid modifying dict during iteration
            keys_to_remove = [
                key for key, value in conversations.items()
                if current_time - value["last_access"] > CLEANUP_INTERVAL
            ]
            for key in keys_to_remove:
                conversations.pop(key, None)
        time.sleep(60)  # Check every minute

# Start cleanup thread
cleanup_thread = threading.Thread(target=cleanup_old_conversations, daemon=True)
cleanup_thread.start()

def get_doctor_data(doctor_name):
    """Thread-safe function to get doctor data from file or cache"""
    with cache_lock:
        if doctor_name in doctor_data_cache:
            return doctor_data_cache[doctor_name]
        
        with file_lock:
            try:
                with open(f"{doctor_name}.txt", 'r') as file:
                    data = file.read()
                    doctor_data_cache[doctor_name] = data
                    return data
            except FileNotFoundError:
                return None

def get_or_create_conversation(doctor_name, user_number):
    """Get or create a conversation for a specific doctor-user pair"""
    conversation_key = (doctor_name, user_number)
    current_time = time.time()
    
    with conversation_lock:
        if conversation_key not in conversations:
            doctor_data = get_doctor_data(doctor_name)
            if doctor_data is None:
                return None
            
            conversations[conversation_key] = {
                "messages": [
                    SystemMessage(content=f"You are a Doctor AI assistant. You have access to the following information about a doctor: {doctor_data} "
                                        f"Answer questions based only on provided information (very important). "
                                        f"If the information is not available in the provided data, respond with 'ask something else'.")
                ],
                "last_access": current_time
            }
        else:
            # Update last access time
            conversations[conversation_key]["last_access"] = current_time
        
        return conversations[conversation_key]["messages"]
    
    

@app.route('/ask', methods=['POST'])
def ask_question():
    try:
        data = request.json
        if not data or not all(key in data for key in ['question', 'doctorusername', 'usernumber']):
            return jsonify({"error": "Missing required fields"}), 400
        
        question = data['question']
        doctor_name = data['doctorusername']
        user_number = data['usernumber']
        
        conversation = get_or_create_conversation(doctor_name, user_number)
        if conversation is None:
            return jsonify({"error": f"Doctor data not found for {doctor_name}"}), 404
        
        # Create chat instance for each request
        chat = ChatOpenAI(temperature=0.6)
        
        # Process the question
        with conversation_lock:
            conversation.append(HumanMessage(content=question))
            response = chat(conversation)
            conversation.append(AIMessage(content=response.content))
            
            # Update last access time after processing
            conversations[(doctor_name, user_number)]["last_access"] = time.time()
        
        return jsonify({
            "answer": response.content,
            "doctor": doctor_name,
            "user": user_number,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, threaded=True)