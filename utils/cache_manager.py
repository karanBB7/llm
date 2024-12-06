import json
import logging
import threading
import time
from typing import Dict, Optional
from config.settings import CACHE_FILE, CACHE_REFRESH_INTERVAL
from services.doctor_service import DoctorService

logger = logging.getLogger(__name__)

class CacheManager:
    def __init__(self):
        self.doctor_data_cache: Dict[str, str] = {}
        self.cache_lock = threading.Lock()
        self.last_cache_refresh = time.time()
        self.doctor_service = DoctorService()

    def load_cache_index(self):
        try:
            if CACHE_FILE.exists():
                with open(CACHE_FILE, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading cache index: {e}")
        return {}

    def save_cache_index(self, index):
        try:
            with open(CACHE_FILE, 'w') as f:
                json.dump(index, f)
        except Exception as e:
            logger.error(f"Error saving cache index: {e}")

    def get_doctor_data(self, doctor_name: str) -> Optional[str]:
        with self.cache_lock:
            if doctor_name in self.doctor_data_cache:
                return self.doctor_data_cache[doctor_name]
            
            data = self.doctor_service.read_doctor_data(doctor_name)
            if data is None:
                success, _ = self.doctor_service.scrape_doctor_data(doctor_name)
                if success:
                    data = self.doctor_service.read_doctor_data(doctor_name)
            
            if data:
                self.doctor_data_cache[doctor_name] = data
                return data
            return None

    def clear_old_cache_entries(self):
        current_time = time.time()
        if current_time - self.last_cache_refresh > CACHE_REFRESH_INTERVAL:
            with self.cache_lock:
                self.doctor_data_cache.clear()
                self.last_cache_refresh = current_time
                logger.info("Cleared doctor data cache")