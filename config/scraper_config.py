# Scraper configuration and constants

BASE_URL = 'http://13.235.8.91/'
AUTH_TOKEN = "X7#mP9$kL2@nR5vQ8*lifeoncode"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Content-Type': 'application/x-www-form-urlencoded'
}

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