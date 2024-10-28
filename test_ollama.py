# File: test_ollama.py
import requests
import json

def test_ollama_connection():
    try:
        version_response = requests.get('http://localhost:11434/api/version')
        print(f"Ollama server status: {'Running' if version_response.status_code == 200 else 'Not running'}")
        return version_response.status_code == 200
    except:
        print("Ollama server is not running")
        return False

def test_chat_endpoint():
    test_data = {
        "question": "What are the doctor's specialties and expertise?",
        "doctorusername": "dr-balachandra-bv",
        "usernumber": "12345"
    }
    
    try:
        response = requests.post(
            'http://localhost:5000/ask',
            json=test_data
        )
        print(f"\nTest chat response status: {response.status_code}")
        print(f"Response content: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error testing chat endpoint: {str(e)}")
        return False

if __name__ == "__main__":
    print("Testing Ollama server...")
    if test_ollama_connection():
        print("\nTesting chat endpoint...")
        test_chat_endpoint()
    else:
        print("Please start Ollama server before running tests")