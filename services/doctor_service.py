import requests
import logging
from typing import Tuple, Optional
from pathlib import Path
from config.settings import DATA_DIRECTORY

logger = logging.getLogger(__name__)

class DoctorService:
    @staticmethod
    def get_doctor_file_path(doctor_name: str) -> Path:
        return DATA_DIRECTORY / f"doctorsData/{doctor_name}.txt"

    @staticmethod
    def scrape_doctor_data(doctor_name: str) -> Tuple[bool, Optional[str]]:
        try:
            response = requests.post(
                'http://localhost:5001/scrape-doctor',
                json={'doctor_username': doctor_name},
                headers={'Content-Type': 'application/json'},
                auth=('', 'X7#mP9$kL2@nR5vQ8*lifeoncode'),
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
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

    @staticmethod
    def read_doctor_data(doctor_name: str) -> Optional[str]:
        try:
            with open(f"doctorsData/{doctor_name}.txt", 'r', encoding='utf-8') as file:
                return file.read()
        except Exception:
            return None