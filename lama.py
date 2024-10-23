from flask import Flask, request, jsonify
import requests  # for Ollama API
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
                with open(f"{doctor_name}.txt", 'r') as file:
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
            
            conversations[conversation_key] = {
                "messages": [
                    {
                        "role": "system",
                        "content": f"You are a Doctor AI assistant. You have access to the following information about a doctor: {doctor_data} "
                                 f"Answer questions based only on provided information (very important). "
                                 f"If the information is not available in the provided data, respond with 'ask something else'."
                    }
                ],
                "last_access": current_time
            }
        else:
            conversations[conversation_key]["last_access"] = current_time
        
        return conversations[conversation_key]["messages"]

def get_ollama_response(messages):
    """Get response from locally running Ollama instance"""
    # Format messages for Ollama
    formatted_messages = []
    for msg in messages:
        formatted_messages.append({
            "role": msg["role"],
            "content": msg["content"]
        })

    # Call local Ollama API
    response = requests.post(
        "http://localhost:11434/api/chat",
        json={
            "model": "llama2",
            "messages": formatted_messages,
            "stream": False
        }
    )
    
    if response.status_code == 200:
        return response.json()["message"]["content"]
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