# Chat Assistant Webhook Project

This project sets up a Flask application that interacts with OpenAI's GPT-4-turbo model to assist in conversations via a webhook. It processes user messages, manages conversation threads, and extracts details using the assistant.

Prerequisites
----------------
Ensure you have the following installed on your system:

- Python 3.7+
- pip3 (Python package installer)
- OpenAI API key
- ngrok (for exposing the local server to the internet, optional but recommended for testing)

Setup Instructions
-------------------
1. **Clone the Repository**

   ```sh
   git clone <repository_url>
   cd <repository_directory>
2. Create a Virtual Environment

It is recommended to use a virtual environment to manage dependencies.

python3 -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate

3. Install Dependencies

Install the required Python packages using pip3:

pip3 install -r requirements.txt

4. Environment Variables

Ensure you have a .env file in the root directory of the project with your OpenAI API key and Make.com webhook URL:

OPENAI_API_KEY=your_openai_api_key
MAKE_RESPONSE_WEBHOOK_URL=https://your_make_com_webhook_url

5. Run the Flask Application

Start the Flask server:
python3 serverapp.py

The application will run on http://127.0.0.1:5001 by default.

6. Expose the Local Server to the Internet (Optional)

If you want to test the webhook from an external service, you can use ngrok to expose your local server:
ngrok http 5001


Usage
------
1) Webhook Endpoint

The webhook endpoint is available at /webhook. You can send POST requests to this endpoint to interact with the assistant.

Example using curl:
curl -X POST http://127.0.0.1:5001/webhook \
     -H "Content-Type: application/json" \
     -d '{
           "message": "Hello, this is a test message",
           "role": "user",
           "thread_id": "unique_thread_id"
         }'

2) Handling Conversations

New Thread: When a new thread ID is detected, the assistant will greet the user and ask for their name, email, child's name, and child's age (in Hebrew).
Existing Thread: For existing threads, the assistant will continue the conversation based on the provided messages.

3) Timeout Handling

If there is no activity in a thread for a specified timeout period (default 5 minutes), the conversation will be summarized, and details such as name, email, child's name, and child's age will be extracted and printed.

Project Structure
------------------
serverapp.py: Main Flask application file.
requirements.txt: List of Python dependencies.
.env: Environment variables file.


