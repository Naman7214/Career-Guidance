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
from werkzeug.security import generate_password_hash, check_password_hash
import logging
from gridfs import GridFS
from io import BytesIO
from PIL import Image
import re
from flask import current_app
import fitz



app = Flask(__name__)
GOOGLE_API_KEY = "AIzaSyCVKshD7_8qSRge-0Zs2-gFlTaIGXrFNB0"
app.secret_key = "EC7C2E214AFFCB4165A1856A62227"
genai.configure(api_key=GOOGLE_API_KEY)
# logging.basicConfig(filename='app.log', level=logging.INFO,
#                     format='%(asctime)s %(levelname)s:%(name)s:%(message)s')

# uri = "mongodb+srv://Grimoires:aaPX19MOAMjkCa2I@guidodb.saqygc9.mongodb.net/?retryWrites=true&w=majority"
# client = MongoClient(uri)
# db = client['GuidoDB']

client = MongoClient('mongodb://localhost:27017/')
db = client['career1']
fs = GridFS(db)
user_mock_history = db['user_mock_history']
user_history = db['user_history']
users = db['users']
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', '.pdf'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def sanitize_string(value):
    """A simple sanitizer that removes special characters from user input."""
    return re.sub(r'[^a-zA-Z0-9]', '', value)


def boldify(text):
    # Split the text by "**" to isolate sections to be bolded
    parts = text.split("**")
    new_text = ""
    # Iterate over the parts and apply bold formatting to every second element
    for i, part in enumerate(parts):
        if i % 2 == 1:  # This means the part should be bolded
            new_text += f"<b>{part}</b><hr>"
        else:  # This part should not be bolded
            new_text += part
    return new_text

def generate_chat_id():
    id = str(uuid.uuid4())
    return id

def register(username,password):
    username = sanitize_string(username)
    if users.find_one({"username": username}):
        return "Username already exists"
    
    hashed_password = generate_password_hash(password)

    users.insert_one({
        "username": username,
        "password": hashed_password
    })

    return True

def user_login(username,password):
    username = sanitize_string(username)
    user = users.find_one({"username": username})

    if user:
        if check_password_hash(user['password'],password):
            return True
        else:
            return False
    else:
        return False

def save_user_history(chat_id, username, history):
    try:
        update_result = user_history.update_one(
            {"chat_id": chat_id},
            {"$set": {"username": username, "history": history}},
            upsert=True
        )
        print(f"Updated {update_result.matched_count} documents.")
    except Exception as e:
        print(f"An error occurred while updating user history: {e}")


def save_user_mock_history(chat_id, username, history):
    try:
        update_result = user_mock_history.update_one(
            {"chat_id": chat_id},
            {"$set": {"username": username, "mock_history": history}},
            upsert=True
        )
        print(f"Updated {update_result.matched_count} documents.")
    except Exception as e:
        print(f"An error occurred while updating user history: {e}")





def get_user_history(chat_id):
    document = user_history.find_one({"chat_id": chat_id})
    return document['history'] if document else []

def get_user_mock_history(chat_id):
    document  = user_mock_history.find_one({"chat_id" : chat_id})
    return document['mock_history'] if document else []

def create_chat(username, chat_id):
    try:
       history = []
       insert_result = user_history.insert_one({"username": username, "chat_id": chat_id, "history":history})
       print("Done")
    except Exception as e:
        print(e)

def get_chat_ids(username):
    try:
        documents = user_history.find({"username": username}, {"chat_id": 1})
        chat_ids = [document["chat_id"] for document in documents]
        return chat_ids
    except Exception as e:
        print(f"An error occurred while retrieving chat IDs: {e}")
        return []

def get_mock_chat_ids(username):
    try:
        documents = user_mock_history.find({"username": username}, {"chat_id": 1})
        chat_ids = [document["chat_id"] for document in documents]
        return chat_ids
    except Exception as e:
        print(f"An error occurred while retrieving chat IDs: {e}")
        return []

def delete_chat_history(chat_id):
    result = user_history.delete_one({'chat_id': chat_id})
    if result.deleted_count == 1:
        return f"Deleted Sucessfully"
    else:
        return f"Not deleted Sucessfully or the file does not exists"


def delete_mock_chat_history(chat_id):
    result = user_mock_history.delete_one({'chat_id': chat_id})
    if result.deleted_count == 1:
        return f"Deleted Sucessfully"
    else:
        return f"Not deleted Sucessfully or the file does not exists"

  # PyMuPDF is a commonly used library to work with PDFs

def store_documents(username, files):
    file_ids = []

    for file in files:
        content_type = file.content_type
        if content_type.startswith('image') and allowed_file(file.filename):
            try:
                file.stream.seek(0)
                image = Image.open(file.stream)
                file.stream.seek(0)
                image_id = fs.put(file.stream, content_type=content_type)
                file_ids.append(image_id)
            except IOError as e:
                current_app.logger.error(f"Error processing image file: {e}")
        elif content_type == 'application/pdf':
            try:
                file.stream.seek(0)
                pdf = fitz.open("pdf", file.stream.read())
                pdf_images = []
                for page_num in range(len(pdf)):
                    page = pdf[page_num]
                    pix = page.get_pixmap()
                    img = Image.open(BytesIO(pix.tobytes("ppm")))
                    pdf_images.append(img)

                # Combine images into one
                total_height = sum(i.height for i in pdf_images)
                max_width = max(i.width for i in pdf_images)
                combined_image = Image.new('RGB', (max_width, total_height))

                y_offset = 0
                for img in pdf_images:
                    combined_image.paste(img, (0, y_offset))
                    y_offset += img.height

                # Save combined image to a byte stream and store in GridFS
                image_stream = BytesIO()
                combined_image.save(image_stream, format='PNG')
                image_stream.seek(0)
                image_id = fs.put(image_stream, content_type='image/png')
                file_ids.append(image_id)
            except Exception as e:
                current_app.logger.error(f"Error processing PDF file: {e}")
        else:
            current_app.logger.error(f"Unsupported file type: {content_type}")

    if file_ids:
        # Optionally, update user document with new file_ids
        current_app.logger.info(f"Files stored with ids: {file_ids} for username: {username}")
    else:
        current_app.logger.error("No valid files were provided.")




def retrieve_documents(username):
    document = db.mycol.find_one({'username': username})

    if document and 'document_file_ids' in document:
        file_ids = document['document_file_ids']
        for file_id in file_ids:
            file_document = fs.get(file_id)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], f'{username}_document.jpg')

            # Convert document to JPG format
            convert_and_save_as_jpg(file_document, file_path)
        
        print("Files retrieved and saved as JPG for username:", username)
    else:
        print("No files found for username:", username)


def convert_to_jpg(source_stream):
    # Convert the non-image document to JPG format
    image = Image.open(source_stream)
    output_stream = BytesIO()
    image.save(output_stream, format='JPEG')
    output_stream.seek(0)
    return output_stream


def convert_and_save_as_jpg(source_document, destination_path):
    # Convert and save the document as JPG
    image = Image.open(BytesIO(source_document.read()))

    # Convert RGBA to RGB if necessary
    if image.mode == 'RGBA':
        image = image.convert('RGB')

    image.save(destination_path, format='JPEG')

def getPromptForChat():


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

    return prompt

def getPromptForResume():


    prompt = [
         f"""
    Guido The Compass, as an expert system specializing in analyzing student resumes, your mission is to extract and interpret information from key sections to offer tailored improvement suggestions. Each resume's analysis should be uniquely aligned with the following user's interests and expectations to ensure relevance and practicality in the job market:

    1. Field of Interest:{session['interests'][0]}
    2. Salary Expectations : {session['interests'][1]}
    3. Job Experience : {session['interests'][2]}

    

    Given the diverse resume formats, deploy advanced pattern recognition to identify relevant information, including synonyms and format variations. If a resume does not contain recognizable sections or information pertinent to professional qualifications, kindly request a valid resume upload.

    ### Specific Instructions:

    - **Synonym Recognition**: Vigilantly identify synonyms and variations of key terms to ensure no critical information is missed. For instance, 'Work Experience' could also be 'Professional History' or 'Employment Details.'

    - **Format Adaptation**: Flexibly adjust to the resume's layout to capture all pertinent details, regardless of whether they are presented in bullet points, paragraphs, or lists.

    - **Interest-Aligned Analysis**: Direct your analysis towards identifying how well the resume aligns with the user's specified interests, particularly in the areas of field of interest, salary expectations, and job experience level.

    ### Desired Output Format:

    - **Gaps Identified(wrap the summary within <div class="gapsIdentified"></div>)**: Enumerate any gaps or areas that lack detail in each priority section, specifically noting discrepancies between the resume content and the user's career objectives or market demands.

    - **Tailored Recommendations(wrap the summary in form of list(ul and li) within <div class="tailoredRecommendations col-span-2"></div>)**: Provide specific, actionable advice for each identified gap. Explain the relevance of your suggestions to the user's interests and career goals, emphasizing how improvements could enhance job market competitiveness.

    **Example for Synonym Recognition**:
    - 'Projects' might also appear as 'Portfolio Highlights' or 'Major Projects.'
    - 'Skills/Technical Skills' could be listed under 'Expertise,' 'Technical Capabilities,' or 'Skill Set.'

    Tailor your feedback to each resume's unique content, offering personalized and precise suggestions that empower students to effectively optimize their resumes in line with their career aspirations.
    NOTE: you must always generate the content for Work Experience, Projects, Skills/Technical Skills, Gaps Identified, Tailored Recommendations as mentioned above! And most important don't just resopond with the content as it is, make SUMMARY out of it and provide valuable feedback to the users

"""
    ]

    return prompt

def getPromptForMock():


    prompt = [
        f"""

You name is GuidoAI who is a  mock interviewer conducting a practice session for a student applying for a {session['job_pref'][0]} and Candidate Expects a salary in range of {session['job_pref'][1]} . Your goal is to simulate a realistic interview experience and ask a series of relevant questions. Please focus on assessing the candidate's qualifications, experience, problem-solving skills, and interpersonal abilities.
            Also ask only One question at a time to me.
            Also perform certain negotiation with candidate and make a fake offer at the end to conclude the interview.
            You are only allowed to ask a max 10 questions.
            name  of candidate is {session['username']}
1. Start by greeting the candidate and introducing yourself as the interviewer.

2. Inquire about the candidate's background, education, and any relevant certifications.

3. Ask about their previous work experience and how it relates to the job they are applying for.

4. Explore the candidate's technical skills and problem-solving abilities by posing scenario-based questions or challenges related to the job.

5. Assess their understanding of the company and the industry, as well as their motivation for applying.

6. Inquire about teamwork and communication skills by asking about past experiences collaborating with colleagues or leading projects.

8. Ask the candidate to provide examples of challenges they've faced in the past and how they overcame them.

9. Gauge their adaptability and ability to learn quickly by posing hypothetical situations or asking about their experiences in fast-paced environments.

10. Allow the candidate to ask questions about the company or the role at the end of the interview.

Above are the points which you have to keep in mind.
Also note that this is an Chatbot like interface so proceed with respect to that.

Provide constructive feedback on their performance, highlighting strengths and suggesting areas for improvement.

Remember to maintain a professional and realistic tone throughout the interview, adapting follow-up questions based on the candidate's responses. Aim to create a positive and beneficial experience for the student to help them prepare for actual job interviews.

Also don't give response in following format:

[Interviewer]: "Welcome [Candidate Name], I'm GuidoAI, the interviewer for today's practice session. Thank you for taking the time to be here."

[Interviewer]: Good morning/afternoon [candidate's name]. My name is GuidoAI, and I'll be your interviewer today. Thank you for taking the time to come in and interview with us.

[Interviewer]: Can you tell me a little bit about your background, education, and any relevant certifications you have?


Don't start with this "[Interviewer]:" don't include this.


"""
    ]

    return prompt


def send_chat(message, history):
    model = genai.GenerativeModel('gemini-pro')
    
    history.append({'role': 'user',
                    'parts': [message]})
    
    response = model.generate_content(history)

    history.append({'role': 'model',
                    'parts': [boldify(response.text)]})
    

    return boldify(response.text), history

def resume_report(file_path):
    GuidoAI = genai.GenerativeModel('gemini-pro-vision')
    resume = PIL.Image.open(file_path)
    prompt = getPromptForResume()
    response = GuidoAI.generate_content([prompt[0],resume])
    print(response.text)
    return boldify(response.text)
    # return response.text






@app.route('/')
def index():
    session.pop('chat_id', None)
    return render_template('layout.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        register(username,password)

        # Redirect to the login page
        return redirect(url_for('login'))

    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # Check if username and password match your authentication logic
        Flag = user_login(username,password)

        if Flag is True:
            print("Login Successfull!!")
            session['username'] = username
            return redirect(url_for('options'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))



@app.route('/options')
def options():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('options.html')


@app.route('/skills', methods = ['GET','POST'])
def skills():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':   
        data = request.form.get('data')
        if data:
            selected_interests = json.loads(data)  # Convert JSON string back to Python list
            print(selected_interests)
            session['interests'] = selected_interests
            print(session['interests'][0])
        return redirect(url_for('resume'))

    return render_template('skillSelection.html')

@app.route('/mock_option', methods = ['GET','POST'])
def mock_option():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':   
        data = request.form.get('data')
        if data:
            job_pref = json.loads(data)  # Convert JSON string back to Python list
            print(job_pref)
            session['job_pref'] = job_pref
            print(session['job_pref'][0])
        return redirect(url_for('mock_chat'))

    return render_template('mock_selection.html')



@app.route('/resume')
def resume():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    return render_template('resume.html')



@app.route('/upload', methods=['POST'])
def upload_file():
    if 'username' not in session:
        return redirect(url_for('login'))

    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)

    if request.method == 'POST':
        files = request.files.getlist('file')
        if not files:
            flash('No selected file')
            return redirect(request.url)

        username = session.get('username', 'default_user')

        # Call store_documents function to store the documents in MongoDB
        store_documents(username, files)

        # Call retrieve_documents function to retrieve and save the documents in the uploads folder
        retrieve_documents(username)

        # Perform resume_report on the saved resume
        report = resume_report(os.path.join(app.config['UPLOAD_FOLDER'], f"{username}_document.jpg"))
        session['report'] = report

        return redirect(url_for('report'))

    return jsonify({'status': 'success', 'message': 'File uploaded successfully'}), 200



@app.route('/report')
def report():
    if 'username' not in session:
        return redirect(url_for('login'))
    report = session.get('report','Unknown')
    return render_template('report.html',report=report)





@app.route('/chat', methods=['GET', 'POST'])
def chat():
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']
    chats = get_chat_ids(username)
    session['chats'] = chats
    
    return render_template('chat.html', chats = chats)

@app.route('/mock_chat', methods=['GET', 'POST'])
def mock_chat():
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']
    chats = get_mock_chat_ids(username)
    print("Into Mock_chat")
    print(chats)
    session['chats'] = chats
    
    return render_template('mockChat.html', chats = chats)


@app.route('/new_chat', methods = ['GET','POST'])
def new_chat():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    username = session.get('username')
    history = []
    chat_id = generate_chat_id()
    save_user_history(chat_id, username, history)
    session['chat_id'] = chat_id
    # return redirect(url_for('chating'))
    return jsonify({'success': True})

@app.route('/new_mock_chat', methods = ['GET','POST'])
def new_mock_chat():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    username = session.get('username')
    history = []
    chat_id = generate_chat_id()
    print("Into New Chat")
    print(chat_id)
    save_user_mock_history(chat_id, username, history)
    session['chat_id'] = chat_id
    # return redirect(url_for('chating'))
    return jsonify({'success': True})

@app.route('/delete_chat' , methods = ['GET', 'POST'])
def delete_chat():
    if 'username' not in session:
        return redirect(url_for('login'))
    data = request.json
    chat_id = data.get('chat_id')
    if 'chat_id' in session:
        session.pop('chat_id')

    delete_chat_history(chat_id)
    return jsonify({'message': 'Success'})

@app.route('/delete_mock_chat' , methods = ['GET', 'POST'])
def delete_mock_chat():
    if 'username' not in session:
        return redirect(url_for('login'))
    data = request.json
    chat_id = data.get('chat_id')
    if 'chat_id' in session:
        session.pop('chat_id')

    delete_mock_chat_history(chat_id)
    return jsonify({'message': 'Success'})
    

@app.route('/chat_id', methods = ['GET','POST'])
def chat_id():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    data = request.json
    chat_id = data.get('chat_id')
    session['chat_id'] = chat_id
    # return redirect(url_for('chating'))
    return jsonify({'message': 'Success'})


@app.route('/chating', methods = ['GET','POST'])
def chating():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    updated_history = []
    user_message_skipped = False

    username = session['username']
    chat_id = session.get('chat_id')
    
    chats = get_chat_ids(username)
    history = get_user_history(chat_id)

    if history == []:
        prompt = getPromptForChat()
        initial_prompt = prompt[0]
        session['response'], history = send_chat(initial_prompt, [])
        updated_history = [{"text": part, "role": item['role']}
                       for item in history
                       for part in item['parts']
                       if not (item['role'] == 'user' and not user_message_skipped and (user_message_skipped := True))]
        save_user_history(session['chat_id'],username, history)

    else:
        updated_history = [{"text": part, "role": item['role']}
                       for item in history
                       for part in item['parts']
                       if not (item['role'] == 'user' and not user_message_skipped and (user_message_skipped := True))]
        

    if request.method == 'POST':
        user_message_skipped = False
        user_message = request.form['message']
        response, history = send_chat(user_message, history)
        session['response'] = response
        updated_history = [{"text": part, "role": item['role']}
                       for item in history
                       for part in item['parts']
                       if not (item['role'] == 'user' and not user_message_skipped and (user_message_skipped := True))]
        save_user_history(session['chat_id'],username, history)
    return render_template('chat.html', messages=updated_history, chats = chats)




@app.route('/chat_ajax', methods=['POST'])
def chat_ajax():
    if 'username' not in session:
        return jsonify({'status': 'error', 'message': 'User not logged in'}), 403
    
    username = session.get('username')
    data = request.get_json()
    user_message = data.get('message', '')
    history = get_user_history(session['chat_id'])
    if not user_message:
        return jsonify({'status': 'error', 'message': 'No message provided'}), 400
    
    response, history = send_chat(user_message,history)
  
    save_user_history(session['chat_id'],username, history)
    return jsonify({'status': 'success', 'response': response}), 200


@app.route('/mock_interview', methods = ['GET','POST'])
def mock_interview():
    if 'username' not in session:
        return redirect(url_for('login'))
    updated_history = []
    user_message_skipped = False

    username = session['username']
    chat_id = session.get('chat_id')
    print(chat_id)
    chats = get_mock_chat_ids(username)
    print(chats)
    history = get_user_mock_history(chat_id)

    if history == []:
        prompt = getPromptForMock()
        initial_prompt = prompt[0]
        session['response'], history = send_chat(initial_prompt, [])
        updated_history = [{"text": part, "role": item['role']}
                       for item in history
                       for part in item['parts']
                       if not (item['role'] == 'user' and not user_message_skipped and (user_message_skipped := True))]
        save_user_mock_history(session['chat_id'],username, history)

    else:
        updated_history = [{"text": part, "role": item['role']}
                       for item in history
                       for part in item['parts']
                       if not (item['role'] == 'user' and not user_message_skipped and (user_message_skipped := True))]
        

    if request.method == 'POST':
        print("Hello")
        user_message_skipped = False
        user_message = request.form['message']
        response, history = send_chat(user_message, history)
        session['response'] = response
        updated_history = [{"text": part, "role": item['role']}
                       for item in history
                       for part in item['parts']
                       if not (item['role'] == 'user' and not user_message_skipped and (user_message_skipped := True))]
        save_user_mock_history(session['chat_id'],username, history)
    return render_template('mockChat.html', messages=updated_history, chats = chats)



@app.route('/mock_chat_ajax', methods=['POST'])
def mock_chat_ajax():
    if 'username' not in session:
        return jsonify({'status': 'error', 'message': 'User not logged in'}), 403
    
    username = session.get('username')
    data = request.get_json()
    user_message = data.get('message', '')
    history = get_user_mock_history(session['chat_id'])
    if not user_message:
        return jsonify({'status': 'error', 'message': 'No message provided'}), 400
    
    # Assume `send_chat` function processes the message and updates `session['history']`
    response, history = send_chat(user_message,history)
  
    save_user_mock_history(session['chat_id'],username, history)
    return jsonify({'status': 'success', 'response': response}), 200





if __name__ == '__main__':
    app.run(debug=True)