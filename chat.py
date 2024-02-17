from flask import Flask, render_template, request, redirect, session, url_for
from pymongo import MongoClient
import google.generativeai as genai
import textwrap
import pathlib
import json
import uuid

app = Flask(__name__)
GOOGLE_API_KEY = "AIzaSyA6Ga8yGLeMc7pCali3x8Hj3Itjk6ihAmQ"
app.secret_key = "EC7C2E214AFFCB4165A1856A62227"
genai.configure(api_key=GOOGLE_API_KEY)

# Connect to MongoDB
client = MongoClient('mongodb://localhost:27017/')
db = client['career1']
user_history = db['user_history']




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
def send_chat(message, history):
    model = genai.GenerativeModel('gemini-pro')
    
    history.append({'role': 'user',
                    'parts': [message]})
    
    response = model.generate_content(history)

    history.append({'role': 'model',
                    'parts': [response.text]})
    

    return response.text, history

@app.route('/')
def index():
    session.clear()
    return redirect(url_for('landing'))

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



@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))



if __name__ == '__main__':
    app.run(debug=True)