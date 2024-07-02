import os
import time
from threading import Timer
from dotenv import load_dotenv
import openai
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

# Load environment variables
load_dotenv()

# Initialize OpenAI client
openai.api_key = os.getenv("OPENAI_API_KEY")
client = openai.OpenAI()

model = "gpt-4o"

# Hardcoded ID for the assistant
assis_id = "asst_xu7o0Y9WJPl6ssJ0av4KPXZL"

# Webhook URL for Make.com to send responses back
make_webhook_url = os.getenv("MAKE_RESPONSE_WEBHOOK_URL")
summary_webhook_url = os.getenv("SUMMARY_WEBHOOK_URL")

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS

# Timeout period (e.g., 5 minutes)
CONVERSATION_TIMEOUT = 10 * 60

# Dictionary to store phone number to thread ID mapping
phone_to_thread = {}

# Dictionary to store conversation details
conversation_details = {}

def generate_lead_caption(name, email, child_name, child_age, summary):
    lead_caption = f"Lead Name: {name}, Lead Email: {email}, Child's Name: {child_name}, Child's Age: {child_age}, Summary: {summary}"
    return lead_caption

# Function to send messages back to Make.com
def send_response_to_make(content, thread_id, phone, lastrun_id, message_id):
    payload = {
        "content": content,
        "thread_id": thread_id,
        "phone": phone,
        "lastrun_id": lastrun_id,
        "message_id": message_id,
    }
    print(f"Sending payload to Make.com: {payload}")
    try:
        response = requests.post(make_webhook_url, json=payload)
        print(f"Response status code: {response.status_code}")
        print(f"Response content: {response.content}")
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Failed to send payload to Make.com: {e}")


# Function to send the summary to the Make webhook
def send_summary_to_make(summary, name, phone, email, child_name, child_age):
    payload = {
        "summary": summary,
        "name": name,
        "phone": phone,
        "email": email,
        "child_name": child_name,
        "child_age": child_age,
    }
    print(f"Sending summary to Make.com: {payload}")
    try:
        response = requests.post(summary_webhook_url, json=payload)
        print(f"Summary Response status code: {response.status_code}")
        print(f"Summary Response content: {response.content}")
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Failed to send summary to Make.com: {e}")


# Function to extract details using the assistant
def extract_details(thread_id, detail_type):

    client.beta.threads.messages.create(
        thread_id=thread_id, role="user", content=f"Extract the {detail_type} from the conversation, without dot at the end, only the {detail_type}. if there is no {detail_type} in the conversation, write word no. without including the names of the files you referenced."
    )     

    run = client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=assis_id,
        instructions=f"Extract the {detail_type} from the conversation. in hebrew. if there is no {detail_type} in the conversation, write word no. without including the names of the files you referenced."
    )
    while run.status != "completed":
        time.sleep(1)
        run = client.beta.threads.runs.retrieve(
            thread_id=thread_id, run_id=run.id
        )
    messages = client.beta.threads.messages.list(
        thread_id=thread_id
    )
    detail = ""
    for message in messages:
        if message.run_id == run.id and message.role == "assistant":
            if isinstance(message.content, list):
                for content_block in message.content:
                    if hasattr(content_block, 'text') and hasattr(content_block.text, 'value'):
                        detail += content_block.text.value + " "
            else:
                detail += message.content.strip()
    return detail.strip()

# Function to summarize the conversation using the assistant
def summarize_conversation(thread_id):
    summary = ''            
    instructions = "Please summarize the conversation" 
    
    client.beta.threads.messages.create(
        thread_id=thread_id, role="user", content='תכתוב את סיכום השיחה עד כה בלי לציין את שמות הקבצים שמהם קראת את המידע'
    )            
    run = client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=assis_id,
        instructions=instructions
    )

    # Wait for the assistant's response
    while run.status != "completed":
        time.sleep(1)
        run = client.beta.threads.runs.retrieve(
            thread_id=thread_id, run_id=run.id
        )

    # Retrieve messages added by the assistant
    messages = client.beta.threads.messages.list(
        thread_id=thread_id
    )  

    # Process the messages
    assistant_messages_for_run = [
        message
        for message in messages
        if message.run_id == run.id and message.role == "assistant"
    ]

    for message in assistant_messages_for_run:
       # print(f"Message content: {message.content}")
        if isinstance(message.content, list):
            for content_block in message.content:
                if hasattr(content_block, 'text') and hasattr(content_block.text, 'value'):
                    summary = content_block.text.value
        else:
            summary = message.content.strip()

    return summary.strip()

# Function to handle conversation timeout
def handle_conversation_timeout(thread_id, phone_num): 
    print(f"handle_conversation_timeout")
    print(f"phone: {phone_num}")
    name = extract_details(thread_id, "Name")
    email = extract_details(thread_id, "email")
    child_name = extract_details(thread_id, "child's name")
    child_age = extract_details(thread_id, "child's age")
    summary = summarize_conversation(thread_id)
    details = conversation_details.get(thread_id, {})
    #phone_num = details.get("phone_num", "")

    #lead_caption = generate_lead_caption(name, email, child_name, child_age, summary)

   # print(f"Lead Caption: {lead_caption}")
    print(f"Summary: {summary}")
    print(f"Name: {name}")
    print(f"Email: {email}")
    print(f"Child's Name: {child_name}")
    print(f"Child's Age: {child_age}")
    print(f"phone: {phone_num}")

    # Send the summary to the Make webhook
    send_summary_to_make(summary, name, phone_num, email, child_name, child_age)

    
    # Clean up the details for the ended conversation
    if conversation_details[thread_id]["timeout_timer"]:
        conversation_details[thread_id]["timeout_timer"].cancel()
    print(f"Conversation with thread ID {thread_id} has ended due to timeout.")

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        print("Headers:", request.headers)
        print("Request data:", request.data)
        data = request.json
        print(f"Received webhook data: {data}")
        if data and "message" in data and "role" in data and "thread_id" in data:
            # Process the user's message and send it to OpenAI
            print(f"Process the user's message and send it to OpenAI")
            user_message = data["message"]
            role = data["role"]
            phone_num = data["thread_id"]
            # Check if the phone number exists in the dictionary
            new_thread = False
            if phone_num in phone_to_thread:
                thread_id = phone_to_thread[phone_num]
            else:
                # Create a new thread and add to the dictionary
                chat_thread = client.beta.threads.create()
                thread_id = chat_thread.id
                phone_to_thread[phone_num] = thread_id
                new_thread = True
                conversation_details[thread_id] = {
                    "timeout_timer": None,
                    "phone_num": phone_num
                }   
                print(f"New thread created for phone number {phone_num}: {thread_id}")

            if role == "user":
                # Add the user's message to the existing thread
                client.beta.threads.messages.create(
                    thread_id=thread_id, role="user", content=user_message
                )
                # Create a run with additional instructions for new threads
                if new_thread:
                    instructions = "Please greet the customer and ask for their name and email address. please do it only in hebrew"
                else:
                    instructions = None

                run = client.beta.threads.runs.create(
                    thread_id=thread_id,
                    assistant_id=assis_id,
                    instructions=instructions
                )

                # Wait for the assistant's response
                while run.status != "completed":
                    time.sleep(1)
                    run = client.beta.threads.runs.retrieve(
                        thread_id=thread_id, run_id=run.id
                    )

                # Retrieve messages added by the assistant
                messages = client.beta.threads.messages.list(
                    thread_id=thread_id
                )  

                # Process and send assistant messages back to Make.com
                assistant_messages_for_run = [
                    message
                    for message in messages
                    if message.run_id == run.id and message.role == "assistant"
                ]

                for message in assistant_messages_for_run:
                    print(f"Message content: {message.content}")
                    # Ensure message content is correctly accessed
                    if isinstance(message.content, list):
                        for content_block in message.content:
                            # Adapt this based on actual content structure
                            if hasattr(content_block, 'text') and hasattr(content_block.text, 'value'):
                                assistant_message_content = content_block.text.value
                                # Send the assistant's message back to Make.com
                                send_response_to_make(
                                    assistant_message_content, thread_id, phone_num, 
                                    run.id, message.id
                                )
                    else:
                        print(f"Unexpected message content format: {message.content}")

                # Reset the timeout timer for the thread
                if conversation_details[thread_id]["timeout_timer"]:
                    conversation_details[thread_id]["timeout_timer"].cancel()

                timer = Timer(CONVERSATION_TIMEOUT, handle_conversation_timeout, [thread_id, phone_num])
                conversation_details[thread_id]["timeout_timer"] = timer
                timer.start()

            return jsonify({"status": "success"}), 200
        else:
            print("Invalid payload received.")
            return jsonify({"status": "error", "message": "Invalid payload"}), 400
    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({"status": "error", "message": "An internal error occurred"}), 500
    


if __name__ == '__main__':
    app.run(port=5001, debug=True)
