import os
import requests
from flask import Flask, request, jsonify
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)

# Environment variables
SLACK_BOT_TOKEN = os.getenv('SLACK_BOT_TOKEN')
CHATGPT_API_URL = "https://api.openai.com/v1/chat/completions"
CHATGPT_API_KEY = os.getenv('CHATGPT_API_KEY')

# Headers for Slack and ChatGPT APIs
HEADERS_SLACK = {'Authorization': f'Bearer {SLACK_BOT_TOKEN}'}
HEADERS_CHATGPT = {
    "Authorization": f"Bearer {CHATGPT_API_KEY}",
    "Content-Type": "application/json"
}

@app.route("/")
def home():
    return "Hello from the Slack bot server!"

@app.route("/slack/events", methods=["POST"])
def slack_events():
    data = request.json
    logging.debug(f"Received Slack event: {data}")
    
    # Handle Slack verification challenge
    if "challenge" in data:
        logging.debug("Received Slack challenge request.")
        return jsonify({"challenge": data["challenge"]})
    
    # Process Slack events
    event_data = data.get("event", {})
    if event_data.get("type") == "message" and not event_data.get("bot_id"):
        channel = event_data.get("channel")
        text = event_data.get("text", "")
        logging.debug(f"Incoming message: {text} in channel: {channel}")
        
        # Always send the message to OpenAI for processing
        response = analyze_with_chatgpt(text)
        logging.debug(f"Sending response to Slack: {response}")
        send_slack_message(channel, response)
    
    return jsonify({"status": "ok"})

def analyze_with_chatgpt(user_message):
    """
    Sends the user's message to ChatGPT and returns the response.
    """
    logging.debug("Sending user message to ChatGPT for processing.")
    payload = {
        "model": "gpt-3.5-turbo",
        "messages": [{"role": "user", "content": user_message}],
        "temperature": 0.7
    }

    try:
        response = requests.post(CHATGPT_API_URL, json=payload, headers=HEADERS_CHATGPT)
        response.raise_for_status()
        chat_response = response.json()["choices"][0]["message"]["content"]
        logging.debug(f"ChatGPT response: {chat_response}")
        return chat_response
    except requests.RequestException as e:
        error_message = f"Failed to connect to ChatGPT: {e}"
        logging.error(error_message)
        return error_message

def send_slack_message(channel, text, ts=None):
    """
    Sends a message to a Slack channel.
    """
    logging.debug(f"Sending message to Slack channel: {channel}")
    try:
        payload = {"channel": channel, "text": text}
        if ts:
            payload["thread_ts"] = ts
        response = requests.post(
            "https://slack.com/api/chat.postMessage",
            headers=HEADERS_SLACK,
            json=payload
        )
        logging.debug(f"Slack response: {response.json()}")
    except requests.RequestException as e:
        logging.error(f"Failed to send message to Slack: {e}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))  # Adjust to Render's detected port
    app.run(host="0.0.0.0", port=port)
