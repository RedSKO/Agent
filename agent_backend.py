import os
import requests
import csv
from io import StringIO
from flask import Flask, request, jsonify


app = Flask(__name__)

@app.route("/")
def home():
    return "Hello, Render!"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

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
    response = requests.get(file_url, headers=HEADERS_SLACK)
    if response.status_code != 200:
        return f"Failed to download file: {response.status_code}"

    csv_data = StringIO(response.text)
    csv_reader = csv.DictReader(csv_data)

    # Collect invoice data for ChatGPT processing
    invoice_list = []
    for row in csv_reader:
        invoice_list.append({
            "Invoice Number": row['Invoice Number'],
            "Supplier Name": row['Supplier Name'],
            "Invoice Amount": row['Invoice Amount'],
            "Due Date": row['Due Date'],
            "Payment Terms": row['Payment Terms']
        })

    return analyze_invoices_with_chatgpt(invoice_list)


def analyze_invoices_with_chatgpt(invoices):
    # Prepare the ChatGPT prompt
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

    response = requests.post(CHATGPT_API_URL, json=payload, headers=HEADERS_CHATGPT)
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        return f"Failed to connect to ChatGPT: {response.status_code}"


@app.route("/slack/events", methods=["POST"])
def slack_event():
    data = request.json
    event_data = data.get("event", {})

    if event_data.get("type") == "message" and "files" in event_data:
        file_url = event_data["files"][0]["url_private_download"]
        result = process_csv_file(file_url)
        return jsonify({"text": result})

    return jsonify({"status": "ignored"})


if __name__ == "__main__":
    app.run(debug=True)
