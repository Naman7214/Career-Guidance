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




def to_markdown(text):
  text = text.replace('•', '  *')
  return Markdown(textwrap.indent(text, '> ', predicate=lambda _: True))

def send_chat(message):
    model = genai.GenerativeModel('gemini-pro')
    # Re-create the chat session with the existing history
    # Make sure to transform 'history' back into the required format if it's not already compatible
    chat_session = model.start_chat(history=[])
    response = chat_session.send_message(message)
    
    # Serialize the updated history into a JSON-compatible format
    updated_history = []
    for item in chat_session.history:
        # Assuming `item.parts` is accessible and contains the message text
        # And `item.role` directly provides the role without needing further access
        # Loop through `item.parts` if it's a list, otherwise adjust based on the actual structure
        for part in item.parts:
            serialized_part = {
                "text": part.text,  # Extract text from parts
                "role": item.role   # Use role directly from the item
            }
            updated_history.append(serialized_part)
    
    return updated_history




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

prompt1 = [
    """
    You are an Expert in career guidance and your task is to help students explore and identify potential career paths that align with their interests, skills, personality, and aspirations. To accomplish this, follow these steps:
    Note : you are being used as a chat bot so follow these steps one at a time and sequentially. That also means you will have to ask questions when required to understand the skill set of the student and answer only when you have all the information.
    ask only one question at a time.
    Note: You must ask minimum of 10 questions to the user before providing an career related assements.
    1. Gather Information: You must always start with student's name, current education and field and what skills does he/she have. Also don't create a response based on this data but also ask other questions Like what skills they have, what field do they want to specialize in like AI/Ml, Web Development and etc. Also since your end goal is to provide the career path also ask them what is the salary they expect. And with also the previous data tell them what new skills they should acquire or what job would suit them with current knowledge.
    2. Analyze Responses: carefully judge what they know and how well they know for this you can also ask other series of questions but in orderily manner.
    3. Provide Insights: based on the input when you think you have sufficient information or user does not have anything else to tell, provide them with neccessary information and feedback, like what field suits and them, what new things they can learn and etc.
    4. Educational Guidance : Guide them on how they can acquire those skills, or  how can they find those jobs and all of those things.
    5. Personalized Recommendations
    6. Encourage Exploration
    7. Address Concerns
    8. Promote Reflection
    9. Follow-up
    Also note that these are college students and handle with that in mind
    Your role is to guide, inform, and inspire the student in their career exploration journey, helping them make informed decisions about their future.

"""
]

@app.route('/')
def index():
   session.clear()  # Clear the session
   return redirect(url_for('chat'))

@app.route('/chat', methods=['GET', 'POST'])
def chat():
    if 'chat_history' not in session or not session['chat_history']:
        initial_prompt = prompt[0]
        session['chat_history'] = send_chat(initial_prompt)
    
    if request.method == 'POST':
        user_message = request.form['message']
        updated_history = send_chat(user_message)
        old_history = session.get('chat_history')
        old_history.extend(updated_history)
        session['chat_history'] = old_history
    
    # Save chat history to a JSON file
    with open('chat_history.json', 'w') as file:
        json.dump(session['chat_history'], file, indent=4)

    chat_history_for_display = session.get('chat_history', [])
    return render_template('chat.html', messages=chat_history_for_display)



if __name__ == '__main__':
    app.run(debug=True)