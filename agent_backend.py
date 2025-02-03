import os
import requests
import csv
from io import StringIO
from flask import Flask, request, jsonify
import threading
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)

SLACK_BOT_TOKEN = os.getenv('SLACK_BOT_TOKEN')
CHATGPT_API_URL = "https://api.openai.com/v1/chat/completions"
CHATGPT_API_KEY = os.getenv('CHATGPT_API_KEY')

HEADERS_SLACK = {'Authorization': f'Bearer {SLACK_BOT_TOKEN}'}
HEADERS_CHATGPT = {
    "Authorization": f"Bearer {CHATGPT_API_KEY}",
    "Content-Type": "application/json"
}


def process_csv_file(file_url, channel, ts):
    logging.debug(f"Downloading CSV from: {file_url}")
    try:
        response = requests.get(file_url, headers=HEADERS_SLACK)
        response.raise_for_status()
    except requests.RequestException as e:
        error_message = f"Failed to download file: {e}"
        logging.error(error_message)
        send_slack_message(channel, error_message, ts)
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
        send_slack_message(channel, result, ts)
    except Exception as e:
        error_message = f"Error processing CSV file: {e}"
        logging.error(error_message)
        send_slack_message(channel, error_message, ts)


def analyze_invoices_with_chatgpt(invoices):
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


@app.route("/slack/events", methods=["POST"])
def slack_event():
    data = request.json
    logging.debug(f"Received Slack event: {data}")
    event_data = data.get("event", {})

    if event_data.get("type") == "message" and "files" in event_data:
        file_url = event_data["files"][0]["url_private_download"]
        channel = event_data.get("channel")
        ts = event_data.get("ts")

        # Acknowledge receipt to Slack
        threading.Thread(target=process_csv_file, args=(file_url, channel, ts)).start()
        return jsonify({"status": "processing"})

    return jsonify({"status": "ignored"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
