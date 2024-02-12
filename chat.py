from flask import Flask, render_template, request, redirect, session, url_for, send_file
import google.generativeai as genai
import textwrap
from IPython.display import Markdown
from IPython.display import display
import pathlib
import json




app = Flask(__name__)
GOOGLE_API_KEY= "AIzaSyA6Ga8yGLeMc7pCali3x8Hj3Itjk6ihAmQ"
app.secret_key = "EC7C2E214AFFCB4165A1856A62227"
genai.configure(api_key=GOOGLE_API_KEY)

history =[]

def to_markdown(text):
  text = text.replace('•', '  *')
  return Markdown(textwrap.indent(text, '> ', predicate=lambda _: True))


prompt = [
    """
    You are an Expert in career guidance and your task is to help students explore and identify potential career paths that align with their interests, skills, personality, and aspirations. To accomplish this, follow these steps:
    Note : you are being used as a chat bot so follow these steps one at a time and sequentially. That also means you will have to ask questions when required to understand the skill set of the student and answer only when you have all the information.
    ask only one question at a time.
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

"""
]


def send_chat(message,history):

    model = genai.GenerativeModel('gemini-pro')
    
    history.append({'role':'user',
                 'parts':[message]})
    
    response = model.generate_content(history)

    history.append({'role':'model',
                 'parts':[response.text]})
    
    print("genearted")

    return response.text, history




@app.route('/')
def index():
   session.clear() 
   return redirect(url_for('chat'))

@app.route('/chat', methods=['GET', 'POST'])
def chat():
    updated_history = []

    if 'history' not in session:
        session['history'] =  []

    if 'response' not in session or not session['response']:
        initial_prompt = prompt[0]
        session['response'] , history = send_chat(initial_prompt,[])
        # print(session['response'])
        session['history'] = history
        # print(history)
    else:
        history = session['history']

    
    if request.method == 'POST':
        user_message = request.form['message']
        response , history = send_chat(user_message, history)
        session['response'] = response
        session['history'] = history

        print(history)

    for item in history:
        for part in item['parts']:
            serialized_part = {
                "text": part,  
                "role": item['role']   
            }
            updated_history.append(serialized_part)

    
    with open('chat_history.json', 'w') as file:
        json.dump(updated_history, file, indent=4)

    
    return render_template('chat.html', messages=updated_history)

if __name__ == '__main__':
    app.run(debug=True)

   