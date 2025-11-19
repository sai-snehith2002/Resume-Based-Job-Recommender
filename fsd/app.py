import os
from flask import Flask, render_template, flash, redirect, url_for, session, request, send_file
from forms import RegisterForm, LoginForm
from models import db, User
from flask_bcrypt import Bcrypt
from functools import wraps
import PyPDF2 as pdf
import google.generativeai as genai
from dotenv import load_dotenv
import json
import csv
import re
from collections import defaultdict
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from bs4 import BeautifulSoup
import requests
import pandas as pd

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Utility functions
def get_unique_entries(input_list):
    return list(set(input_list))

def input_pdf_text(uploaded_file):
    reader = pdf.PdfReader(uploaded_file)
    text = ""
    for page in range(len(reader.pages)):
        page = reader.pages[page]
        text += str(page.extract_text())
    return text

def clean_job_entries(job_entries):
    filtered_entries = [entry for entry in job_entries if entry['company_name'] is not None]
    return filtered_entries

def get_gemini_response(input):
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content(input)
    return response.text

def clean_dict_keys(input_dict):
    cleaned_dict = {}
    for key, value in input_dict.items():
        cleaned_key = key.strip("'{}")
        if isinstance(value, str):
            cleaned_value = value.strip("'{}")
        else:
            cleaned_value = value
        cleaned_dict[cleaned_key] = cleaned_value
    return cleaned_dict

def parse_response_to_dict(response):
    response_lines = response.split(';')
    response_dict = {}
    for line in response_lines:
        if line.strip():
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip()
            if key == "Skills":
                response_dict[key] = [skill.strip() for skill in value.split(',')]
            elif key == 'Languages':
                response_dict[key] = [lang.strip() for lang in value.split(',')]
            elif key == "Companies":
                companies = value.split(',')
                companies_dict = {}
                for company in companies:
                    name, role = company.split(':')
                    companies_dict[name.strip()] = role.strip()
                response_dict[key] = clean_dict_keys(companies_dict)
            elif key == "Experience":
                experiences = value.split(',')
                experiences_dict = {}
                total_experience = 0.0
                for experience in experiences:
                    name, years = experience.split(':')
                    years = years.strip("'{} ")
                    try:
                        years = float(years)
                    except ValueError:
                        years = 0.0
                    experiences_dict[name.strip()] = years
                    total_experience += years
                response_dict[key] = clean_dict_keys(experiences_dict)
                response_dict["Total Years of Experience"] = total_experience
            else:
                response_dict[key] = value
    return response_dict

def read_csv(file_path):
    with open(file_path, mode='r') as file:
        reader = csv.DictReader(file)
        data = [row for row in reader]
    return data

def process_skills(skills):
    return ', '.join(skills)

def calculate_similarity(user_skills, job_skills):
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform([user_skills, job_skills])
    return cosine_similarity(tfidf_matrix)[0, 1]

def find_top_job_titles(user_skills, data, top_n=10):
    job_similarities = defaultdict(float)
    user_skills_processed = process_skills(user_skills)
    for row in data:
        job_skills = row['Key Skills']
        similarity = calculate_similarity(user_skills_processed, job_skills)
        job_similarities[row['Job Title']] = similarity

    top_job_titles = sorted(job_similarities, key=job_similarities.get, reverse=True)[:top_n]
    return top_job_titles

def find_closest_job_title(predicted_job_title, user_experience_dict):
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform([predicted_job_title] + list(user_experience_dict.keys()))
    similarities = cosine_similarity(tfidf_matrix)[0, 1:]
    closest_idx = similarities.argmax()
    closest_job_title = list(user_experience_dict.keys())[closest_idx]
    similarity_score = similarities[closest_idx]
    return closest_job_title, similarity_score

def scraper(url_list):
    id_list = []
    for url in url_list:
        response = requests.get(url)
        list_data = response.text
        list_soup = BeautifulSoup(list_data, "html.parser")
        page_jobs = list_soup.find_all("li")
        for job in page_jobs:
            base_card_div = job.find("div", {"class": "base-card"})
            job_id = base_card_div.get("data-entity-urn").split(":")[3]
            id_list.append(job_id)

    id_list_new = get_unique_entries(id_list)
    job_list = []
    for job_id in id_list_new:
        job_url = f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"
        job_response = requests.get(job_url)
        job_soup = BeautifulSoup(job_response.text, "html.parser")
        job_post = {}
        try:
            job_post["job_title"] = job_soup.find("h2", {"class": "top-card-layout__title font-sans text-lg papabear:text-xl font-bold leading-open text-color-text mb-0 topcard__title"}).text.strip()
        except:
            job_post["job_title"] = None
        try:
            job_post["company_name"] = job_soup.find("a", {"class": "topcard__org-name-link topcard__flavor--black-link"}).text.strip()
        except:
            job_post["company_name"] = None
        try:
            job_post["time_posted"] = job_soup.find("span", {"class": "posted-time-ago__text topcard__flavor--metadata"}).text.strip()
        except:
            job_post["time_posted"] = None
        try:
            job_post['link'] = job_soup.find("a", {"class": "topcard__link"}).get('href')
        except:
            job_post['link'] = None
        job_list.append(job_post)  # list of dictionaries
    jobs_df = pd.DataFrame(clean_job_entries(job_list))
    return jobs_df

def main(user_skills, user_experience_dict):
    file_path = 'jobs_new.csv'
    data = read_csv(file_path)
    top_job_titles = find_top_job_titles(user_skills, data)
    predicted_job_title = top_job_titles[0]
    closest_job_title, similarity_score = find_closest_job_title(predicted_job_title, user_experience_dict)

    if not closest_job_title or similarity_score < 0.2:
        closest_job_title = predicted_job_title
        user_exp = 0
    else:
        user_exp = user_experience_dict[closest_job_title]

    return predicted_job_title, closest_job_title, user_exp, similarity_score

def generate_url_list(predicted_job_title, location):
    title_2B = predicted_job_title.replace(" ","%2B")
    title_20 = predicted_job_title.replace(" ","%20")
    location_20 = location.replace(" ","%20")
    location_2B = location.replace(" ","%2B")

    url_link1 = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={title_2B}&location={location_2B}&start=50"
    url_link2 = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={title_20}&location={location_20}&start=50"
    url_link3 = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={title_20}&location={location_2B}&start=50"
    url_link4 = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={title_2B}&location={location_20}&start=50"

    return [url_link1, url_link2, url_link3, url_link4]


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = "ASDFGHUTHB"
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///flask_auth_db.sqlite3'
    app.config['ALLOWED_EXTENSIONS'] = {'pdf'}

    bcrypt = Bcrypt()

    db.init_app(app)
    bcrypt.init_app(app)

    with app.app_context():
        db.create_all()

    def login_required(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "user_id" not in session:
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function

    def allowed_file(filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

    @app.route('/')
    def index():
        return render_template("home.html")
    
    @app.route('/login', methods = ['POST', 'GET'])
    def login():
        if 'user_id' in session:
            return redirect(url_for('dashboard'))
        form = LoginForm()
        if form.validate_on_submit():
            user = User.query.filter_by(email= form.email.data).first()
            if user and bcrypt.check_password_hash(user.password, form.password.data):
                session['user_id'] = user.id
                session['username'] = user.username
                flash('You have been logged in !', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash("Login Unsuccessful. Please Check and Password", 'danger')
        return render_template("login.html", form=form)
    
    @app.route('/register', methods = ['POST', 'GET'])
    def register():
        if 'user_id' in session:
            return redirect(url_for('dashboard'))
        form = RegisterForm()
        if form.validate_on_submit():
            hased_passsword = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
            user = User(
                username = form.username.data,
                email = form.email.data,
                password = hased_passsword,
            )
            db.session.add(user)
            db.session.commit()
            flash("Your account has been created", 'success')
            return redirect(url_for('login'))
        return render_template("register.html", form = form)
    
    @app.route('/clear', methods=['POST'])
    @login_required
    def clear_dashboard():
        session.pop('response_dict', None)
        session.pop('text', None)
        session.pop('predicted_job_title', None)
        session.pop('closest_job_title', None)
        session.pop('user_exp', None)
        session.pop('similarity_score', None)
        session.pop('jobs', None)
        flash('Page cleared!', 'info')
        return redirect(url_for('dashboard'))
    
    @app.route('/dashboard', methods=['GET', 'POST'])
    @login_required
    def dashboard():
        # Initialize variables
        text = ""
        response_dict = {}
        predicted_job_title = ""
        closest_job_title = ""
        user_exp = ""
        similarity_score = ""
        jobs = pd.DataFrame()

        if request.method == 'POST':
            if 'clear' in request.form:
                # Handle "Clear Page" button
                session.pop('response_dict', None)
                session.pop('text', None)
                session.pop('predicted_job_title', None)
                session.pop('closest_job_title', None)
                session.pop('user_exp', None)
                session.pop('similarity_score', None)
                session.pop('jobs', None)
                flash('Page cleared!', 'info')
                return redirect(url_for('dashboard'))

            file = request.files.get('pdf')
            location = request.form.get('location')

            if file and file.filename.endswith('.pdf'):
                # Read the PDF file from memory
                reader = pdf.PdfReader(file)
                text = ""
                for page in range(len(reader.pages)):
                    text += reader.pages[page].extract_text()

                flash('Text extracted successfully!', 'success')
                input_prompt = f"""
                Resume Text:
                {text}

                Extract the candidate's details from the resume following the below format and instructions.

                Response format should only contain the below fields in the same format:
                Candidate Name: [Name]; Email ID: [email ID]; Phone Number: [number]; Highest Qualification: [Highest qualification]; Skills: [list of all relevant skills only]; Languages: [list of languages the candidate knows (if no laguage found then return empty list)]; Companies: [List all companies in a form of dictionary with company name: job role]; Experience: [List all positions the candidate worked as in a form of dictionary with values as number of year experience in that role];
                """
                response = get_gemini_response(input_prompt)
                response_dict = parse_response_to_dict(response)

                predicted_job_title, closest_job_title, user_exp, similarity_score = main(response_dict['Skills'], response_dict['Experience'])
                url_list = generate_url_list(predicted_job_title, location)

                jobs = scraper(url_list)
            else:
                flash('Invalid file type. Please upload a PDF file.', 'danger')
                return redirect(request.url)

        # Retrieve data from session if available
        if 'response_dict' in session:
            response_dict = session['response_dict']
        if 'text' in session:
            text = session['text']
        if 'predicted_job_title' in session:
            predicted_job_title = session['predicted_job_title']
        if 'closest_job_title' in session:
            closest_job_title = session['closest_job_title']
        if 'user_exp' in session:
            user_exp = session['user_exp']
        if 'similarity_score' in session:
            similarity_score = session['similarity_score']
        if 'jobs' in session:
            jobs = session['jobs']

        return render_template('dashboard.html', jobs=jobs, response_dict=response_dict, text=text,
                            predicted_job_title=predicted_job_title, closest_job_title=closest_job_title,
                            user_exp=user_exp, similarity_score=similarity_score)

    
    @app.route('/logout')
    def logout():
        session.pop('user_id')
        session.pop('username')
        flash('You have been logged out!!', 'success')
        return redirect(url_for('index'))

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5001)
