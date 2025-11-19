AI-Powered Resume Parsing & Job Recommendation System
=====================================================

This project is an end-to-end intelligent platform that helps users upload their resume, extract key professional information, predict their most suitable job role using vector similarity, and automatically fetch real-time LinkedIn job openings from the past week.  
The system provides tailored job suggestions based on the candidate’s actual skills, experience, and industry relevance.

-----------------------------------------------------
⭐ Key Features
-----------------------------------------------------

1. User Authentication
----------------------
- Secure Sign-Up & Login using Flask sessions  
- Password hashing with Flask-Bcrypt  
- Personal dashboard after login  

2. Resume Parsing
-----------------
Users upload their resume in PDF format.  
The system extracts:
- Name  
- Email  
- Phone number  
- Highest qualification  
- Skills  
- Experience  
- Companies and roles  

Parsing is powered by **Google Gemini 1.5 Flash API**  
Custom prompt engineering ensures clean, structured extraction.

3. Skill Vectorization & Job Role Prediction
--------------------------------------------
- Extracted skills → cleaned & vectorized using TF-IDF  
- A predefined CSV dataset maps **job roles ↔ skills**  
- Cosine similarity identifies the closest matching job role  

The system determines:
- Predicted Job Title  
- Closest Title based on Experience  
- Similarity Score  

4. Real-Time Job Scraping (LinkedIn Jobs API - guest endpoints)
---------------------------------------------------------------
Once the job role is predicted:
- System generates dynamic LinkedIn API search URLs  
- Scrapes job listings posted within the last **1 week**  
- Extracts:
  - Job title  
  - Company name  
  - Time posted  
  - Job link  

- Removes duplicates  
- Displays results in a clean table for the user  

5. Interactive Dashboard
------------------------
After uploading the resume, the dashboard shows:
- Parsed resume details  
- Predicted job title  
- Closest title based on experience  
- Similarity score  
- Real-time job listings from LinkedIn  

User can also clear all results with a single click.

-----------------------------------------------------
🔧 Tech Stack
-----------------------------------------------------

Backend:
- Python  
- Flask  
- Flask-Bcrypt  
- Flask-SQLAlchemy  
- SQLite  

AI / NLP:
- Google Gemini 1.5 Flash API  
- PyPDF2  
- TF-IDF Vectorizer  
- Cosine Similarity  

Web Scraping:
- BeautifulSoup  
- Requests  
- LinkedIn Guest Jobs API  

Database:
- SQLite (previously PostgreSQL supported)

-----------------------------------------------------
🚀 System Workflow
-----------------------------------------------------

<img width="1896" height="873" alt="home page" src="https://github.com/user-attachments/assets/48da0efd-abc9-4a29-b569-6cce81a9b6b1" />

1. User Registration
--------------------
- User creates account  
- Passwords hashed for security  
- Redirected to Login  

<img width="1892" height="821" alt="sign up page" src="https://github.com/user-attachments/assets/86a9612b-9877-4c3e-be78-aa9ef3bc8f44" />

2. User Login
-------------
- Credentials verified  
- Successful login → Dashboard  

<img width="1905" height="876" alt="login page" src="https://github.com/user-attachments/assets/0d1a4fd3-1e44-48de-9781-ba84a410e688" />

3. Upload Resume
----------------
- User uploads PDF resume  
- System extracts text  
- Gemini API processes and returns structured fields

<img width="1902" height="873" alt="Logged In resume upload page" src="https://github.com/user-attachments/assets/0cd07dec-becf-4f56-b6bf-95230f977bc6" />


4. Intelligent Resume Understanding
-----------------------------------
- Extracted fields cleaned  
- Skills and experience processed for vectorization  

5. Job Role Prediction
----------------------
- TF-IDF vectorization of user skills & dataset skills  
- Cosine similarity predicts top matching job roles  
- Additional logic finds closest role based on experience  

6. Real-Time Job Retrieval
--------------------------
- Generate LinkedIn search URLs  
- Scrape job postings from last 1 week  
- Clean & structure results  

7. Display Results to User
--------------------------
Dashboard shows:
- Parsed resume details  
- Predicted job role  
- Experience-based suggestion  
- Latest LinkedIn job listings  
- Direct application links  


