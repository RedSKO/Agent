import os
import requests
import csv
from io import StringIO
from flask import Flask, request, jsonify

app = Flask(__name__)

# Environment Variables for Security
SLACK_BOT_TOKEN = os.getenv('SLACK_BOT_TOKEN')
CHATGPT_API_URL = "https://api.openai.com/v1/chat/completions"
CHATGPT_API_KEY = os.getenv('CHATGPT_API_KEY')

HEADERS_SLACK = {'Authorization': f'Bearer {SLACK_BOT_TOKEN}'}
HEADERS_CHATGPT = {
    "Authorization": f"Bearer {CHATGPT_API_KEY}",
    "Content-Type": "application/json"
}


def process_csv_file(file_url):
    """Downloads and processes CSV file, extracts invoice information."""
    try:
        response = requests.get(file_url, headers=HEADERS_SLACK)
        response.raise_for_status()
    except requests.RequestException as e:
        return f"Failed to download file: {e}"

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
        return analyze_invoices_with_chatgpt(invoice_list)
    except Exception as e:
        return f"Error processing CSV file: {e}"


def analyze_invoices_with_chatgpt(invoices):
    """Sends invoice data to ChatGPT and retrieves AI insights."""
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
        return response.json()["choices"][0]["message"]["content"]
    except requests.RequestException as e:
        return f"Failed to connect to ChatGPT: {e}"


@app.route("/slack/events", methods=["POST"])
def slack_event():
    data = request.json
    event_data = data.get("event", {})

    if event_data.get("type") == "message" and "files" in event_data:
        file_url = event_data["files"][0]["url_private_download"]
        
        # Acknowledge receipt immediately to avoid Slack timeout
        requests.post(
            "https://slack.com/api/chat.postMessage",
            headers=HEADERS_SLACK,
            json={
                "channel": event_data.get("channel"),
                "text": "Bip bop, recherche et rassemblement des informations…",
                "thread_ts": event_data.get("ts")
            }
        )
        
        result = process_csv_file(file_url)
        
        requests.post(
            "https://slack.com/api/chat.postMessage",
            headers=HEADERS_SLACK,
            json={
                "channel": event_data.get("channel"),
                "text": result,
                "thread_ts": event_data.get("ts")
            }
        )
        
        return jsonify({"status": "ok"})

    return jsonify({"status": "ignored"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
