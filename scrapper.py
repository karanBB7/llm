from flask import Flask, request, jsonify
import logging
from utils.auth import require_basic_auth
from services.scraper_service import WebsiteScraper
from services.file_service import FileService
from config.scraper_config import BASE_URL

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/scrape-doctor', methods=['POST'])
@require_basic_auth
def scrape_doctor():
    try:
        data = request.get_json()
        if not data or 'doctor_username' not in data:
            return jsonify({'error': 'doctor_username is required'}), 400

        doctor_username = data['doctor_username']
        url = f"{BASE_URL}/doctor-profile/{doctor_username}"

        # Initialize and run scraper
        scraper = WebsiteScraper(url)
        if scraper.fetch_page():
            if scraper.extract_data():
                filename = FileService.save_to_txt(scraper.data, url)
                if filename:
                    return jsonify({
                        'success': True,
                        'message': f'Data scraped and saved to {filename}',
                        'filename': filename
                    })
                else:
                    return jsonify({'error': 'Failed to save data to file'}), 500
            else:
                return jsonify({'error': 'Failed to extract data'}), 500
        else:
            return jsonify({'error': 'Failed to fetch the page'}), 404

    except Exception as e:
        logger.error(f"Error processing request: {e}")
        return jsonify({
            'error': 'An error occurred processing your request',
            'details': str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)