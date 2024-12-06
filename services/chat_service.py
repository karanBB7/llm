import sentry_sdk
from langchain.chat_models import ChatOpenAI
import logging

from langchain_community.chat_models import ChatOpenAI  # Updated import

logger = logging.getLogger(__name__)

class ChatService:
    def __init__(self):
        try:
            self.chat_model = ChatOpenAI()
        except Exception as e:
            sentry_sdk.capture_exception(e)
            raise

    def get_response(self, conversation):
        try:
            with sentry_sdk.start_transaction(
                name="chat_service.get_response",
                op="ai.response"
            ):
                response = self.chat_model.predict_messages(conversation)
                return response.content
        except Exception as e:
            sentry_sdk.capture_exception(e)
            logger.error(f"Error getting AI response: {e}")
            raise