from flask import Flask, request, jsonify
from bs4 import BeautifulSoup
import requests
import re

app = Flask(__name__)

class WebsiteScraper:
    def __init__(self, url):
        self.url = url
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        self.data = {
            'doctor_info': {},
            'testimonials': [],
            'areaofexpertise': [],
            'faq': [],
            'blogs': [],
            'clinics': []
        }
        self.soup = None
        self.base_url = 'http://13.235.8.91/'

    def clean_text(self, text):
        if text:
            text = re.sub(r'\s+', ' ', text)
            return text.strip()
        return ""

    def get_doctor_name_from_url(self):
        """Extract doctor name from URL"""
        match = re.search(r'/doctor-profile/(.+?)(?:/|$)', self.url)
        if match:
            return match.group(1)
        return "doctor"

    def fetch_page(self):
        """Fetch webpage content"""
        try:
            response = requests.get(self.url, headers=self.headers)
            response.raise_for_status()
            self.soup = BeautifulSoup(response.text, 'html.parser')
            print("Page fetched successfully!")
            return True
        except requests.RequestException as e:
            print(f"Error fetching the page: {e}")
            return False

    def fetch_all_faqs(self, doctor_username):
        try:
            ajax_url = f"{self.base_url}/get_category_faq"
            form_data = {
                'username': str(doctor_username)
            }
            response = requests.post(ajax_url, headers=self.headers, data=form_data)
            print(f"Response status code: {response.status_code}")
            
            json_response = response.json()
            html_content = json_response.get('html', '')
            
            faq_soup = BeautifulSoup(html_content, 'html.parser')
            faq_items = []
            faq_wrappers = faq_soup.find_all('div', class_='faq')
            
            for wrapper in faq_wrappers:
                question = wrapper.find(class_='faq-question')
                answer = wrapper.find(class_='faq-answer')
                if question and answer:
                    question_text = self.clean_text(question.get_text())
                    answer_paragraphs = answer.find_all('p')
                    answer_text = ' '.join([self.clean_text(p.get_text()) for p in answer_paragraphs])
                    
                    faq_items.append({
                        'question': question_text,
                        'answer': answer_text
                    })
            
            return faq_items
                
        except Exception as e:
            print(f"Error fetching FAQs: {e}")
            return []

    def find_by_class(self, class_name):
        """Find element by class name and return its text"""
        if self.soup:
            element = self.soup.find(class_=class_name)
            return self.clean_text(element.text) if element else "Not found"
        return "Not found"

    def extract_data(self, selectors):
        """Extract data using class names"""
        if not self.soup:
            print("Please fetch the page first using fetch_page()")
            return False

        # Extract basic doctor information
        for key, class_name in selectors['doctor_info'].items():
            self.data['doctor_info'][key] = self.find_by_class(class_name)

        # Extract testimonials
        testimonial_wrappers = self.soup.find_all(class_=selectors['testimonial_wrapper'])
        for wrapper in testimonial_wrappers:
            try:
                testimonial = {}
                for key, class_name in selectors['testimonial_items'].items():
                    element = wrapper.find(class_=class_name)
                    testimonial[key] = self.clean_text(element.text) if element else "Not found"
                self.data['testimonials'].append(testimonial)
            except Exception as e:
                print(f"Error extracting testimonial: {e}")

        # Extract areas of expertise
        expertise_wrappers = self.soup.find_all(class_=selectors['expertise_wrapper'])
        for wrapper in expertise_wrappers:
            try:
                expertise_item = {}
                for key, class_name in selectors['expertise_items'].items():
                    element = wrapper.find(class_=class_name)
                    expertise_item[key] = self.clean_text(element.text) if element else "Not found"
                self.data['areaofexpertise'].append(expertise_item)
            except Exception as e:
                print(f"Error extracting expertise: {e}")

        # Extract FAQs
        faq_button = self.soup.find('button', class_='faq-load')
        if faq_button:
            doctor_username = faq_button.get('data-username')
            if doctor_username:
                additional_faqs = self.fetch_all_faqs(doctor_username)
                for faq in additional_faqs:
                    processed_faq = {
                        'Faq Question': faq['question'],
                        'Faq Answer': faq['answer']
                    }
                    self.data['faq'].append(processed_faq)

        # Extract blogs
        blog_wrappers = self.soup.find_all(class_=selectors['blog_wrapper'])
        seen_urls = set()
        filtered_blogs = []

        for wrapper in blog_wrappers:
            try:
                blog_item = {}
                has_content = False
                
                for key, class_name in selectors['blog_items'].items():
                    element = wrapper.find(class_=class_name)
                    
                    if key == 'Blog Url':
                        url_link = wrapper.find('a')
                        href = url_link.get('href') if url_link else None
                        value = self.base_url + href if href and href not in seen_urls else "Not Found"
                        if href:
                            seen_urls.add(href)
                    else:
                        value = self.clean_text(element.text) if element else "Not Found"
                    
                    blog_item[key] = value
                    if value != "Not Found":
                        has_content = True
                
                if has_content and blog_item['Blog Url'] != "Not Found":
                    filtered_blogs.append(blog_item)
                    
            except Exception as e:
                print(f"Error extracting blog: {e}")

        self.data['blogs'] = filtered_blogs

        # Extract clinics
        clinic_wrappers = self.soup.find_all(class_=selectors['clinic_wrapper'])
        for wrapper in clinic_wrappers:
            try:
                clinic_item = {}
                for key, class_name in selectors['clinic_items'].items():
                    element = wrapper.find(class_=class_name)
                    clinic_item[key] = self.clean_text(element.text) if element else "Not found"
                self.data['clinics'].append(clinic_item)
            except Exception as e:
                print(f"Error extracting clinic: {e}")

        return True

    def save_to_txt(self):
        """Save extracted data to a text file"""
        filename = f"{self.get_doctor_name_from_url()}.txt"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                # Write doctor info
                f.write("DOCTOR INFORMATION\n")
                f.write("=" * 50 + "\n\n")
                
                for key, value in self.data['doctor_info'].items():
                    f.write(f"{key.title()}:\n{value}\n\n")
                
                # Write testimonials
                f.write("\nTESTIMONIALS\n")
                f.write("=" * 50 + "\n\n")
                
                for i, testimonial in enumerate(self.data['testimonials'], 1):
                    f.write(f"Testimonial #{i}\n")
                    f.write("-" * 20 + "\n")
                    for key, value in testimonial.items():
                        f.write(f"{key.title()}: {value}\n")
                    f.write("\n")
                    
                # Write areas of expertise
                f.write("\nAREAS OF EXPERTISE\n")
                f.write("=" * 50 + "\n\n")
                
                for i, expertise in enumerate(self.data['areaofexpertise'], 1):
                    f.write(f"Area of Expertise #{i}\n")
                    f.write("-" * 20 + "\n")
                    for key, value in expertise.items():
                        f.write(f"{key.title()}: {value}\n")
                    f.write("\n")
                
                # Write FAQs
                f.write("\nFAQs\n")
                f.write("=" * 50 + "\n\n")
                
                for i, faq in enumerate(self.data['faq'], 1):
                    f.write(f"FAQ #{i}\n")
                    f.write("-" * 20 + "\n")
                    for key, value in faq.items():
                        f.write(f"{key.title()}: {value}\n")
                    f.write("\n")
                
                # Write blogs
                f.write("\nBLOGS AND ARTICLES\n")
                f.write("=" * 50 + "\n\n")
                
                for i, blog in enumerate(self.data['blogs'], 1):
                    f.write(f"Blog #{i}\n")
                    f.write("-" * 20 + "\n")
                    for key, value in blog.items():
                        f.write(f"{key.title()}: {value}\n")
                    f.write("\n")
                
                # Write clinics
                f.write("\nCLINICS\n")
                f.write("=" * 50 + "\n\n")
                
                for i, clinic in enumerate(self.data['clinics'], 1):
                    f.write(f"Clinic #{i}\n")
                    f.write("-" * 20 + "\n")
                    for key, value in clinic.items():
                        f.write(f"{key.title()}: {value}\n")
                    f.write("\n")

            print(f"Data successfully saved to {filename}")
            return filename
        except Exception as e:
            print(f"Error saving to file: {e}")
            return None

SELECTORS = {
    'doctor_info': {
        'Doctor Name': 'doctor-name',
        'Speciality': 'speciality',
        'Certification': 'certification',
        'Phone Number': 'callto',
        'Email Address': 'mailto', 
        'Experience': 'experience',
        'Patients': 'patients',
        'Doctor Overview': 'doctor-overview',
        'Doctor Speciality': 'doctor-speciality',
        'Doctor Expertise Summary': 'doctor-expertise',
        'Doctor Awards': 'doctor-awards',
        'Doctor Qualification summary': 'doctor-qualification'
    },
    'testimonial_wrapper': 'test-wrapp',
    'testimonial_items': {
        'title': 'testimonial-title',
        'content': 'testimonial-content',
        'patient name': 'testimonial-patientname'
    },
    'expertise_wrapper': 'expcontent',
    'expertise_items': {
        'Expertise Title': 'expertise-title',
        'Expertise Content': 'exp-cont'
    },
    'faq_wrapper': 'faq',
    'faq_items': {
        'Faq Question': 'faq-question',
        'Faq Answer': 'faq-answer'
    },
    'blog_wrapper': 'articele-wrapper',
    'blog_items': {
        'Blog Title': 'blog-title',
        'Blog Date': 'blog-date',
        'Blog Url': 'blog-url'
    },
    'clinic_wrapper': 'forscrapper',
    'clinic_items': {
        'Clinic Address': 'clinic-address',
        'Clinic Name': 'clinic-name',
        'Clinic Map Link': 'clinic-maplink'
    }
}

@app.route('/scrape-doctor', methods=['POST'])
def scrape_doctor():
    try:
        data = request.get_json()
        if not data or 'doctor_username' not in data:
            return jsonify({'error': 'doctor_username is required'}), 400

        doctor_username = data['doctor_username']
        url = f"http://13.235.8.91/doctor-profile/{doctor_username}"

        # Initialize and run scraper
        scraper = WebsiteScraper(url)
        if scraper.fetch_page():
            if scraper.extract_data(SELECTORS):
                filename = scraper.save_to_txt()
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
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)