import os
import requests
import csv
from io import StringIO
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
        return jsonify({"challenge": data["challenge"]})
    
    # Process Slack events
    event_data = data.get("event", {})
    if event_data.get("type") == "message" and not event_data.get("bot_id"):
        channel = event_data.get("channel")
        text = event_data.get("text", "")
        logging.debug(f"Incoming message: {text}")
        handle_message(text, channel)
    
    return jsonify({"status": "ok"})

def handle_message(text, channel):
    """
    Handles incoming Slack messages.
    """
    if text.lower() == "hello":
        send_slack_message(channel, "Hello! How can I assist you today?")
    elif text.lower().startswith("analyze csv"):
        file_url = extract_file_url(text)
        if file_url:
            process_csv_file(file_url, channel)
        else:
            send_slack_message(channel, "Please provide a valid CSV file URL.")
    else:
        send_slack_message(channel, f"Received your message: {text}")

def extract_file_url(text):
    """
    Extracts a file URL from the Slack message text.
    """
    parts = text.split()
    for part in parts:
        if part.startswith("http"):
            return part
    return None

def process_csv_file(file_url, channel):
    """
    Downloads and processes a CSV file, then sends the analysis to Slack.
    """
    logging.debug(f"Downloading CSV from: {file_url}")
    try:
        response = requests.get(file_url, headers=HEADERS_SLACK)
        response.raise_for_status()
    except requests.RequestException as e:
        error_message = f"Failed to download file: {e}"
        logging.error(error_message)
        send_slack_message(channel, error_message)
        return

    try:
        csv_data = StringIO(response.text)
        csv_reader = csv.DictReader(csv_data)
        invoice_list = [
            {
                "Invoice Number": row['Invoice Number'],
                "Supplier Name": row['Supplier Name'],
                "Invoice Amount": row['Invoice Amount'],
                "Due Date": row['Due Date'],
                "Payment Terms": row['Payment Terms']
            }
            for row in csv_reader
        ]
        logging.debug(f"Extracted invoices: {invoice_list}")
        result = analyze_invoices_with_chatgpt(invoice_list)
        send_slack_message(channel, result)
    except Exception as e:
        error_message = f"Error processing CSV file: {e}"
        logging.error(error_message)
        send_slack_message(channel, error_message)

def analyze_invoices_with_chatgpt(invoices):
    """
    Sends invoice data to ChatGPT for analysis and returns the response.
    """
    logging.debug("Sending data to ChatGPT for analysis.")
    user_message = (
        "I have a set of invoice data. Analyze and give me insights like payment priority, "
        "potential anomalies, or suggestions to optimize financial decisions.\n\n"
        f"Here is the data:\n{invoices}"
    )

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
