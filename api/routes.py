from flask import Blueprint, jsonify, request
from datetime import datetime
import sentry_sdk
from services.conversation_service import ConversationService
import logging

logger = logging.getLogger(__name__)

app_routes = Blueprint('app_routes', __name__)
conversation_service = ConversationService()

@app_routes.route('/ask', methods=['POST'])
def ask_question():
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
        
        response_content = conversation_service.add_message(doctor_name, user_number, question)
        if response_content is None:
            return jsonify({
                "error": f"Unable to retrieve doctor data for: {doctor_name}",
                "details": "Doctor data not available and scraping failed"
            }), 404
        
        return jsonify({
            "answer": response_content,
            "doctor": doctor_name,
            "user": user_number,
            "timestamp": datetime.now().isoformat(),
            "conversation_length": len(conversation_service.get_or_create_conversation(doctor_name, user_number))
        })
        
    except Exception as e:
        logger.error(f"Error processing request: {e}")
        return jsonify({
            "error": "An error occurred processing your request",
            "details": str(e)
        }), 500

@app_routes.route('/test-sentry')
def test_sentry():
    try:
        with sentry_sdk.configure_scope() as scope:
            scope.set_extra("test_type", "manual_test")
            scope.set_tag("endpoint", "test-sentry")
        raise Exception("This is a test exception")
    except Exception as e:
        sentry_sdk.capture_exception(e)
        return jsonify({"message": "Test error sent to Sentry"}), 500