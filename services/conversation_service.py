import threading
import time
from typing import Dict, Tuple, Optional, List
from collections import defaultdict
from langchain.schema import SystemMessage, HumanMessage, AIMessage
from config.settings import CLEANUP_INTERVAL, MAX_CONVERSATION_LENGTH
from utils.cache_manager import CacheManager
from services.chat_service import ChatService
import logging

logger = logging.getLogger(__name__)

class ConversationService:
    def __init__(self):
        self.conversations: Dict[Tuple[str, str], Dict] = defaultdict(dict)
        self.conversation_lock = threading.Lock()
        self.cache_manager = CacheManager()
        self.chat_service = ChatService()

    def get_or_create_conversation(self, doctor_name: str, user_number: str) -> Optional[List]:
        conversation_key = (doctor_name, user_number)
        current_time = time.time()
        
        with self.conversation_lock:
            if conversation_key in self.conversations:
                self.conversations[conversation_key]["last_access"] = current_time
                if len(self.conversations[conversation_key]["messages"]) > MAX_CONVERSATION_LENGTH:
                    self.conversations[conversation_key]["messages"] = [
                        self.conversations[conversation_key]["messages"][0]
                    ] + self.conversations[conversation_key]["messages"][-(MAX_CONVERSATION_LENGTH-1):]
                return self.conversations[conversation_key]["messages"]

            doctor_data = self.cache_manager.get_doctor_data(doctor_name)
            if doctor_data is None:
                return None
            
            self.conversations[conversation_key] = {
                "messages": [
                    SystemMessage(content=f"""You are an AI assistant with access ONLY to this doctor's specific information:
                    {doctor_data}

                    RESPONSE RULES:
                    1. Medical Questions:
                    - Only address symptoms matching doctor's expertise
                    - If relevant: Share contact info + links:
                    Profile: https://www.linqmd.com/doctor-profile/{doctor_name}
                    Appointments: https://www.linqmd.com/doctor-profile/{doctor_name}#appointment
                    - If unrelated: "This is outside Dr. {doctor_name}'s expertise"

                    2. Other Questions:
                    - Share only listed info (location/hours/credentials)
                    - For website: Provide both profile & appointment links
                    - Otherwise: "Information not in records"

                    Stay within provided data and expertise.""")
                ],
                "last_access": current_time
            }
            return self.conversations[conversation_key]["messages"]

    def add_message(self, doctor_name: str, user_number: str, message: str) -> Optional[str]:
        conversation = self.get_or_create_conversation(doctor_name, user_number)
        if not conversation:
            return None

        with self.conversation_lock:
            conversation.append(HumanMessage(content=message))
            try:
                response_content = self.chat_service.get_response(conversation)
                conversation.append(AIMessage(content=response_content))
                self.conversations[(doctor_name, user_number)]["last_access"] = time.time()
                return response_content
            except Exception as e:
                logger.error(f"Error getting AI response: {e}")
                conversation.pop()
                raise

def cleanup_old_conversations():
    conversation_service = ConversationService()
    while True:
        try:
            current_time = time.time()
            with conversation_service.conversation_lock:
                keys_to_remove = [
                    key for key, value in conversation_service.conversations.items()
                    if current_time - value["last_access"] > CLEANUP_INTERVAL
                ]
                for key in keys_to_remove:
                    conversation_service.conversations.pop(key, None)
            
            conversation_service.cache_manager.clear_old_cache_entries()
            time.sleep(60)
        except Exception as e:
            logger.error(f"Error in cleanup thread: {e}")