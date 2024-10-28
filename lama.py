# File: lama.py
from flask import Flask, request, jsonify
import requests
import threading
import os
import time
from collections import defaultdict
from datetime import datetime

lama = Flask(__name__)

file_lock = threading.Lock()
conversations = defaultdict(dict)
conversation_lock = threading.Lock()
doctor_data_cache = {}
cache_lock = threading.Lock()
CLEANUP_INTERVAL = 600

def cleanup_old_conversations():
    while True:
        current_time = time.time()
        with conversation_lock:
            keys_to_remove = [
                key for key, value in conversations.items()
                if current_time - value["last_access"] > CLEANUP_INTERVAL
            ]
            for key in keys_to_remove:
                conversations.pop(key, None)
        time.sleep(60)

cleanup_thread = threading.Thread(target=cleanup_old_conversations, daemon=True)
cleanup_thread.start()

def get_doctor_data(doctor_name):
    with cache_lock:
        if doctor_name in doctor_data_cache:
            return doctor_data_cache[doctor_name]
        
        with file_lock:
            try:
                with open(f"data.txt", 'r', encoding='utf-8') as file:
                    data = file.read()
                    doctor_data_cache[doctor_name] = data
                    return data
            except FileNotFoundError:
                return None

def get_or_create_conversation(doctor_name, user_number):
    conversation_key = (doctor_name, user_number)
    current_time = time.time()
    
    with conversation_lock:
        if conversation_key not in conversations:
            doctor_data = get_doctor_data(doctor_name)
            if doctor_data is None:
                return None
            
            # Modified system prompt to be more explicit and restrictive
            system_message = {
                "role": "system",
                "content": (
                    "Never mention any other doctors or make up any information.\n\n"
                    "### DOCTOR'S INFORMATION ###\n"
                    f"{doctor_data}\n\n"
                    "### STRICT RULES ###\n"
                    "1. ONLY use the exact information provided above\n"
                    "2. If asked about anything not in this data, say 'That information i dont have'\n"
                    "4. Never add or infer information\n"
                    "5. Never use general medical knowledge - only use what's in the data\n"
                    "7. If listing items, use bullet points or numbers"
                    "8. keep the content as short as possible"
                )
            }
            
            conversations[conversation_key] = {
                "messages": [system_message],
                "last_access": current_time
            }
        else:
            conversations[conversation_key]["last_access"] = current_time
        
        return conversations[conversation_key]["messages"]

def get_ollama_response(messages):
    formatted_messages = []
    for msg in messages:
        formatted_messages.append({
            "role": msg["role"],
            "content": msg["content"]
        })

    # Added more chat context to prevent generic responses
    prefix_message = {
        "role": "assistant",
        "content": "I understand that I must only provide information from the given data. I will not mention any other doctors or make up information."
    }
    formatted_messages.insert(1, prefix_message)

    response = requests.post(
        "http://localhost:11434/api/chat",
        json={
            "model": "llama2",
            "messages": formatted_messages,
            "stream": False,
            "temperature": 0.6,     # Reduced temperature further
            "top_p": 0.1,           # More restrictive sampling
            "num_ctx": 4096,        # Maximum context length
            "repeat_penalty": 1.2    # Prevent repetitive responses
        }
    )
    
    if response.status_code == 200:
        response_content = response.json()["message"]["content"]
        # Check if response mentions Dr. Smith and return error if it does
        if "dr. smith" in response_content.lower() or "dr smith" in response_content.lower():
            return "ERROR: Response contained incorrect doctor reference. Please try your question again."
        return response_content
    else:
        raise Exception(f"Ollama API error: {response.text}")


@lama.route('/ask', methods=['POST'])
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
        
        with conversation_lock:
            conversation.append({
                "role": "user",
                "content": question
            })
            
            response = get_ollama_response(conversation)
            
            conversation.append({
                "role": "assistant",
                "content": response
            })
            
            conversations[(doctor_name, user_number)]["last_access"] = time.time()
        
        return jsonify({
            "answer": response,
            "doctor": doctor_name,
            "user": user_number,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    lama.run(debug=True, threaded=True)