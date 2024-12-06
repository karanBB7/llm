from bs4 import BeautifulSoup
import requests
import logging
from config.scraper_config import HEADERS, SELECTORS, BASE_URL
from utils.text_utils import clean_text

logger = logging.getLogger(__name__)

class WebsiteScraper:
    def __init__(self, url):
        self.url = url
        self.soup = None
        self.data = {
            'doctor_info': {},
            'testimonials': [],
            'areaofexpertise': [],
            'faq': [],
            'blogs': [],
            'clinics': []
        }

    def fetch_page(self):
        """Fetch webpage content"""
        try:
            response = requests.get(self.url, headers=HEADERS)
            response.raise_for_status()
            self.soup = BeautifulSoup(response.text, 'html.parser')
            logger.info("Page fetched successfully!")
            return True
        except requests.RequestException as e:
            logger.error(f"Error fetching the page: {e}")
            return False

    def fetch_all_faqs(self, doctor_username):
        """Fetch FAQs using AJAX"""
        try:
            ajax_url = f"{BASE_URL}/get_category_faq"
            form_data = {'username': str(doctor_username)}
            response = requests.post(ajax_url, headers=HEADERS, data=form_data)
            json_response = response.json()
            html_content = json_response.get('html', '')
            
            faq_soup = BeautifulSoup(html_content, 'html.parser')
            return self._parse_faqs(faq_soup)
                
        except Exception as e:
            logger.error(f"Error fetching FAQs: {e}")
            return []

    def find_by_class(self, class_name):
        """Find element by class name and return its text"""
        if self.soup:
            element = self.soup.find(class_=class_name)
            return clean_text(element.text) if element else "Not found"
        return "Not found"

    def extract_data(self):
        """Extract all data from the webpage"""
        if not self.soup:
            logger.error("Please fetch the page first using fetch_page()")
            return False

        self._extract_doctor_info()
        self._extract_testimonials()
        self._extract_expertise()
        self._extract_faqs()
        self._extract_blogs()
        self._extract_clinics()

        return True

    def _extract_doctor_info(self):
        for key, class_name in SELECTORS['doctor_info'].items():
            self.data['doctor_info'][key] = self.find_by_class(class_name)

    def _extract_testimonials(self):
        for wrapper in self.soup.find_all(class_=SELECTORS['testimonial_wrapper']):
            try:
                testimonial = {}
                for key, class_name in SELECTORS['testimonial_items'].items():
                    element = wrapper.find(class_=class_name)
                    testimonial[key] = clean_text(element.text) if element else "Not found"
                self.data['testimonials'].append(testimonial)
            except Exception as e:
                logger.error(f"Error extracting testimonial: {e}")

    def _extract_expertise(self):
        for wrapper in self.soup.find_all(class_=SELECTORS['expertise_wrapper']):
            try:
                expertise_item = {}
                for key, class_name in SELECTORS['expertise_items'].items():
                    element = wrapper.find(class_=class_name)
                    expertise_item[key] = clean_text(element.text) if element else "Not found"
                self.data['areaofexpertise'].append(expertise_item)
            except Exception as e:
                logger.error(f"Error extracting expertise: {e}")

    def _extract_faqs(self):
        faq_button = self.soup.find('button', class_='faq-load')
        if faq_button:
            doctor_username = faq_button.get('data-username')
            if doctor_username:
                self.data['faq'].extend(self.fetch_all_faqs(doctor_username))

    def _parse_faqs(self, faq_soup):
        faq_items = []
        for wrapper in faq_soup.find_all('div', class_='faq'):
            question = wrapper.find(class_='faq-question')
            answer = wrapper.find(class_='faq-answer')
            if question and answer:
                faq_items.append({
                    'Faq Question': clean_text(question.get_text()),
                    'Faq Answer': clean_text(answer.get_text())
                })
        return faq_items

    def _extract_blogs(self):
        seen_urls = set()
        for wrapper in self.soup.find_all(class_=SELECTORS['blog_wrapper']):
            try:
                blog_item = {}
                has_content = False
                
                for key, class_name in SELECTORS['blog_items'].items():
                    element = wrapper.find(class_=class_name)
                    
                    if key == 'Blog Url':
                        url_link = wrapper.find('a')
                        href = url_link.get('href') if url_link else None
                        value = BASE_URL + href if href and href not in seen_urls else "Not Found"
                        if href:
                            seen_urls.add(href)
                    else:
                        value = clean_text(element.text) if element else "Not Found"
                    
                    blog_item[key] = value
                    if value != "Not Found":
                        has_content = True
                
                if has_content and blog_item['Blog Url'] != "Not Found":
                    self.data['blogs'].append(blog_item)
                    
            except Exception as e:
                logger.error(f"Error extracting blog: {e}")

    def _extract_clinics(self):
        for wrapper in self.soup.find_all(class_=SELECTORS['clinic_wrapper']):
            try:
                clinic_item = {}
                for key, class_name in SELECTORS['clinic_items'].items():
                    element = wrapper.find(class_=class_name)
                    clinic_item[key] = clean_text(element.text) if element else "Not found"
                self.data['clinics'].append(clinic_item)
            except Exception as e:
                logger.error(f"Error extracting clinic: {e}")