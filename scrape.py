import requests
from bs4 import BeautifulSoup
import re


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
        self.base_url = '/'.join(url.split('/')[:3])  

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
            
            # Extract FAQ items
            faq_items = []
            faq_wrappers = faq_soup.find_all('div', class_='faq')
            
            for wrapper in faq_wrappers:
                question = wrapper.find(class_='faq-question')
                answer = wrapper.find(class_='faq-answer')
                if question and answer:
                    # Clean and extract the text
                    question_text = self.clean_text(question.get_text())
                    # For answer, get all paragraph texts
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
        for exp_wrapper in expertise_wrappers:
            try:
                expertise_item = {}
                for key, class_name in selectors['expertise_items'].items():
                    element = exp_wrapper.find(class_=class_name)
                    expertise_item[key] = self.clean_text(element.text) if element else "Not found"
                self.data['areaofexpertise'].append(expertise_item)
            except Exception as e:
                print(f"Error extracting Areas of expertise: {e}")


        faq_wrappers = self.soup.find_all(class_=selectors['faq_wrapper'])
        for faq_wrapper in faq_wrappers:
            try:
                faq_item = {}
                for key, class_name in selectors['faq_items'].items():
                    element = faq_wrapper.find(class_=class_name)
                    faq_item[key] = self.clean_text(element.text) if element else "Not Found"
                self.data['faq'].append(faq_item)
            except Exception as e:
                print(f"Error extracting visible FAQ: {e}")


        faq_button = self.soup.find('button', class_='faq-load')
        if faq_button:
            doctor_username = faq_button.get('data-username')
            print(f"user id: {doctor_username}")
            
            if doctor_username:
                # Fetch all FAQs using AJAX
                additional_faqs = self.fetch_all_faqs(doctor_username)
                
                # Add only new FAQs (avoid duplicates)
                existing_questions = {faq['Faq Question'] for faq in self.data['faq']}
                
                for faq_item in additional_faqs:
                    if faq_item['question'] not in existing_questions:
                        processed_faq = {
                            'Faq Question': faq_item['question'],
                            'Faq Answer': faq_item['answer']
                        }
                        self.data['faq'].append(processed_faq)
                        existing_questions.add(faq_item['question'])


        # Extract areas of clinics

        clinic_wrappers = self.soup.find_all(class_=selectors['clinic_wrapper'])
        for clinic_wrapper in clinic_wrappers:
            try:
                clinic_item = {}
                for key, class_name in selectors['clinic_items'].items():
                    element = clinic_wrapper.find(class_=class_name)
                    clinic_item[key] = self.clean_text(element.text) if element else "Not found"
                self.data['clinics'].append(clinic_item)
            except Exception as e:
                print(f"Error extracting Clinics: {e}")
                
        else:
            print("No FAQ load button found")


        blog_wrappers = self.soup.find_all(class_=selectors['blog_wrapper'])
        seen_urls = set()
        filtered_blogs = []

        for blog_wrapper in blog_wrappers:
            try:
                blog_item = {}
                has_content = False
                
                for key, class_name in selectors['blog_items'].items():
                    element = blog_wrapper.find(class_=class_name)
                    
                    if key == 'Blog Url':
                        url_link = blog_wrapper.find('a')
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
                print(f"Error extracting Blogs: {e}")

        self.data['blogs'] = filtered_blogs




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
                f.write("\nAreas Of Expertise\n")
                f.write("=" * 50 + "\n\n")

                for j, expertise_item in enumerate(self.data['areaofexpertise'], 1):
                    f.write(f"Area of Expertise #{j}\n")
                    f.write("-" * 20 + "\n")
                    for key, value in expertise_item.items():
                        f.write(f"{key.title()}: {value}\n")
                    f.write("\n")
                    
                # Write FAQs
                f.write("\nFAQ\n")
                f.write("=" * 50 + "\n\n")
                
                for k, faq_item in enumerate(self.data['faq'], 1):
                    f.write(f"FAQ #{k}\n")
                    f.write("-" * 20 + "\n")
                    for key, value in faq_item.items():
                        f.write(f"{key.title()}: {value}\n")
                    f.write("\n")
                    
                # Write Blogs
                f.write("\nBLOGS AND ARTICLES\n")  # Fixed typo and made consistent with other headers
                f.write("=" * 50 + "\n\n")
                
                for l, blog_item in enumerate(self.data['blogs'], 1):
                    f.write(f"Blog #{l}\n")  # Changed "blogs" to "Blog" for consistency
                    f.write("-" * 20 + "\n")
                    for key, value in blog_item.items():
                        f.write(f"{key.title()}: {value}\n")
                    f.write("\n")

                # Write Clinics
                f.write("\nClinic\n")  # Fixed typo and made consistent with other Clinic
                f.write("=" * 50 + "\n\n")
                
                for l, clinic_item in enumerate(self.data['clinics'], 1):
                    f.write(f"Clinic #{l}\n")  # Changed "blogs" to "Blog" for consistency
                    f.write("-" * 20 + "\n")
                    for key, value in clinic_item.items():
                        f.write(f"{key.title()}: {value}\n")
                    f.write("\n")


            print(f"Data successfully saved to {filename}")
            return filename
        except Exception as e:
            print(f"Error saving to file: {e}")
            return None

def main():
    # URL to scrape
    url = "http://13.235.8.91/doctor-profile/dr-balachandra-bv"
    
    # Define selectors using only class names
    selectors = {
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

        'blog_wrapper' : 'articele-wrapper',
        'blog_items':{
            'Blog Title' : 'blog-title',
            'Blog Date' : 'blog-date',
            'Blog Url' : 'blog-url'
        },

        'clinic_wrapper' : 'forscrapper',
        'clinic_items':{
            'Clinic Address' : 'clinic-address',
            'Clinic Name' : 'clinic-name',
            'Clinic Map Link' : 'clinic-maplink'
        }
    }

    # Initialize and run scraper
    scraper = WebsiteScraper(url)
    if scraper.fetch_page():
        if scraper.extract_data(selectors):
            scraper.save_to_txt()

if __name__ == "__main__":
    main()