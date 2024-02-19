from flask import Flask, render_template, request, redirect, session, url_for, flash, jsonify
from werkzeug.utils import secure_filename
import os
from pymongo import MongoClient
import google.generativeai as genai
import textwrap
import pathlib
import json
import uuid
import PIL.Image

app = Flask(__name__)
GOOGLE_API_KEY = "AIzaSyA6Ga8yGLeMc7pCali3x8Hj3Itjk6ihAmQ"
app.secret_key = "EC7C2E214AFFCB4165A1856A62227"
genai.configure(api_key=GOOGLE_API_KEY)



# Connect to MongoDB
client = MongoClient('mongodb://localhost:27017/')
db = client['career1']
user_history = db['user_history']
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS




def save_user_history(username, history):
    user_history.update_one(
        {"username": username},
        {"$set": {"history": history}},
        upsert=True
    )




def get_user_history(username):
    document = user_history.find_one({"username": username})
    return document['history'] if document else []

def generate_user_id():
    return str(uuid.uuid4())

prompt = [
    """
    You are an Expert in career guidance and your task is to help students explore and identify potential career paths that align with their interests, skills, personality, and aspirations. To accomplish this, follow these steps:
    Note : you are being used as a chat bot so follow these steps one at a time and sequentially. That also means you will have to ask questions when required to understand the skill set of the student and answer only when you have all the information.
    ask only one question at a time.
    Ask minimum of 10 questions and maximum 15 before suggesting the user any of the career path and that too only one question at a time in order to better understand the user.
    Also the questions should not be marked with number when being asked to user.
    If any of the response from the user is unrelated to given context, don't answer those questions and instead request them to be more focused on the current conversation.
    Don't write any sort of code for user, don't answer any general apptitude type question for the user.
    1. Gather Information
    2. Analyze Responses
    3. Provide Insights
    4. Educational Guidance
    5. Personalized Recommendations
    6. Encourage Exploration
    7. Address Concerns
    8. Promote Reflection
    9. Follow-up
    Also note that these are college students and handle with that in mind
    Your role is to guide, inform, and inspire the student in their career exploration journey, helping them make informed decisions about their future.
    start coversation with some greetings.
"""
]

prompt1 =[
    """
    You are an expert system specialized in analyzing student resumes to provide meaningful insights and tailored suggestions for improvement. Given the diverse formats of resumes, your task involves intelligently parsing and understanding information from the following key sections, ranked by their importance:

1. Work Experience (Highest Priority)
2. Projects (2nd Highest Priority)
3. Skills/Technical Skills (3rd Highest Priority)

Keep in mind that resumes can vary greatly in structure and terminology. Employ advanced pattern recognition to identify relevant information, considering synonyms and variations of the above-listed terms. Adapt to the format in which the data is presented, whether it's bullet points, paragraphs, or lists.

### Specific Instructions:

- **Synonym Recognition**: Actively look for variations and synonyms of the key terms to ensure comprehensive data extraction.
- **Format Adaptation**: Analyze the resume's layout to adjust your parsing strategy, ensuring that no critical information is overlooked due to unconventional formatting.
- **Conditional Recommendations**: Only provide recommendations when necessary, focusing on areas that truly require improvement based on the priority levels.

### Desired Output Format:
- **Gaps Identified**: Clearly list any gaps or areas lacking sufficient detail in each priority section.
- **Recommendations**: For each identified gap, offer specific, actionable advice on how the student can enhance their resume. Detail the significance of your suggestions and how they align with the student's career objectives or the job market demands.

**Example for Synonym Recognition**:
- Work Experience might also be listed as "Professional Experience," "Career History," or "Job Background."
- Projects could be under "Project Experience," "Portfolio," or "Key Projects."
- Skills/Technical Skills might be found as "Competencies," "Technical Proficiency," or "Professional Skills."

**Note**: Tailor your analysis to the unique context of each resume, providing personalized and precise feedback that empowers students to optimize their resumes effectively.
"""
]

def send_chat(message, history):
    model = genai.GenerativeModel('gemini-pro')
    
    history.append({'role': 'user',
                    'parts': [message]})
    
    response = model.generate_content(history)

    history.append({'role': 'model',
                    'parts': [response.text]})
    

    return response.text, history


def resume_report(file_path):
    GuidoAI = genai.GenerativeModel('gemini-pro-vision')
    resume = PIL.Image.open(file_path)
    response = GuidoAI.generate_content([prompt1[0],resume])
    return response.text




@app.route('/')
def index():
    session.clear()
    return redirect(url_for('landing'))

@app.route('/resume')
def resume():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    return render_template('resume.html')

@app.route('/landing')
def landing():
    return render_template('layout.html')




@app.route('/chat', methods=['GET', 'POST'])
def chat():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    updated_history = []
    user_message_skipped = False

    username = session['username']
    
    if 'history' not in session:
        session['history'] = get_user_history(username)

    if session['history'] == []:
        initial_prompt = prompt[0]
        session['response'], history = send_chat(initial_prompt, [])
        session['history'] = history
        updated_history = [{"text": part, "role": item['role']}
                       for item in history
                       for part in item['parts']
                       if not (item['role'] == 'user' and not user_message_skipped and (user_message_skipped := True))]
        save_user_history(username, history)
        # session['history'] = get_user_history(username)

    else:
        history = session['history']
        updated_history = [{"text": part, "role": item['role']}
                       for item in history
                       for part in item['parts']
                       if not (item['role'] == 'user' and not user_message_skipped and (user_message_skipped := True))]
        

    if request.method == 'POST':
        user_message_skipped = False
        user_message = request.form['message']
        response, history = send_chat(user_message, history)
        session['response'] = response
        session['history'] = history
        updated_history = [{"text": part, "role": item['role']}
                       for item in history
                       for part in item['parts']
                       if not (item['role'] == 'user' and not user_message_skipped and (user_message_skipped := True))]
        save_user_history(username, history)
        # session['history'] = get_user_history(username)

    print(updated_history)
    
    return render_template('chat.html', messages=updated_history)





@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # Check if username and password match your authentication logic

        # For simplicity, let's assume any non-empty username is valid
        if username:
            session['username'] = username
            return redirect(url_for('chat'))
    
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # Perform user signup logic here
        save_user_history(username, [])

        # Redirect to the login page
        return redirect(url_for('login'))

    return render_template('signup.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    if 'username' not in session:
        return redirect(url_for('login'))

    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)
    if request.method == 'POST':
        file = request.files['file']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            username = session.get('username', 'default_user')
            filename = f"{username}_cv.{filename.rsplit('.', 1)[1].lower()}"  
            print("saving")
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            print("saved")
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            print(file_path)
            print("Opening")
            with open(file_path, 'rb') as file:
                resume = file.read()
            print("Opened")
            report = resume_report(file_path)
            print(report)
            session['report'] = report
            return redirect(url_for('report'))
    return jsonify({'status': 'success', 'message': 'File uploaded successfully'}), 200



@app.route('/report')
def report():
    if 'username' not in session:
        return redirect(url_for('login'))
    report = session.get('report','Unknown')
    return render_template('report.html',report=report)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))



if __name__ == '__main__':
    app.run(debug=True)