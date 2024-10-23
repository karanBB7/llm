from flask import Flask, request, jsonify
from langchain.schema import HumanMessage, SystemMessage, AIMessage
from langchain.chat_models import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

chat = ChatOpenAI(temperature=0.6)

with open('data.txt', 'r') as file:
    doctor_data = file.read()

conversation = [
    SystemMessage(content=f"You are a question-answering AI assistant. You have access to the following information about a doctor: {doctor_data} Answer questions based only on this information (very important). If the information is not available in the provided data, respond with 'ask something else'.")
]

@app.route('/ask', methods=['POST'])
def ask_question():
    data = request.json
    if not data or 'question' not in data:
        return jsonify({"error": "No question provided"}), 400
    
    question = data['question']
    
    conversation.append(HumanMessage(content=question))
    
    response = chat(conversation)
    
    conversation.append(AIMessage(content=response.content))
    
    return jsonify({"answer": response.content})

if __name__ == '__main__':
    app.run(debug=True)