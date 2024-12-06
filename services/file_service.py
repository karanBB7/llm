import os
import logging
from utils.text_utils import get_doctor_name_from_url

logger = logging.getLogger(__name__)

class FileService:
    @staticmethod
    def save_to_txt(data, url):
        """Save scraped data to a text file"""
        folder_path = "doctorsData"
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            
        filename = os.path.join(folder_path, f"{get_doctor_name_from_url(url)}.txt")
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                FileService._write_section(f, "DOCTOR INFORMATION", data['doctor_info'])
                FileService._write_section(f, "TESTIMONIALS", data['testimonials'])
                FileService._write_section(f, "AREAS OF EXPERTISE", data['areaofexpertise'])
                FileService._write_section(f, "FAQs", data['faq'])
                FileService._write_section(f, "BLOGS AND ARTICLES", data['blogs'])
                FileService._write_section(f, "CLINICS", data['clinics'])

            logger.info(f"Data successfully saved to {filename}")
            return filename
        except Exception as e:
            logger.error(f"Error saving to file: {e}")
            return None

    @staticmethod
    def _write_section(file, title, data):
        """Write a section of data to the file"""
        file.write(f"\n{title}\n")
        file.write("=" * 50 + "\n\n")
        
        if isinstance(data, dict):
            for key, value in data.items():
                file.write(f"{key.title()}:\n{value}\n\n")
        else:
            for i, item in enumerate(data, 1):
                file.write(f"{title.rstrip('S')} #{i}\n")
                file.write("-" * 20 + "\n")
                for key, value in item.items():
                    file.write(f"{key.title()}: {value}\n")
                file.write("\n")