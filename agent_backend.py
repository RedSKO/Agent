from flask import Flask, request, jsonify
import os
import openai
import hashlib
import hmac
import json

app = Flask(__name__)

openai.api_key = os.getenv("OPENAI_API_KEY")
slack_signing_secret = os.getenv("SLACK_SIGNING_SECRET")

# Function to verify Slack's requests using the signing secret
def verify_slack_request(req):
    # Get the signature and timestamp from Slack headers
    slack_signature = req.headers.get("X-Slack-Signature")
    slack_timestamp = req.headers.get("X-Slack-Request-Timestamp")

    # Time window for requests (5 minutes)
    if abs(time.time() - int(slack_timestamp)) > 60 * 5:
        return False

    # Create the basestring to hash
    sig_basestring = f"v0:{slack_timestamp}:{req.get_data().decode()}"
    secret = bytes(slack_signing_secret, "utf-8")
    calculated_signature = "v0=" + hmac.new(secret, sig_basestring.encode(), hashlib.sha256).hexdigest()

    return hmac.compare_digest(calculated_signature, slack_signature)

@app.route("/slack/events", methods=["POST"])
def slack_events():
    data = request.get_json()

    # Log the received data for debugging
    print("Received data:", data)

    # Handle Slack challenge verification (used during initial setup)
    if "challenge" in data:
        return jsonify({"challenge": data["challenge"]})

    # Process message events
    if "event" in data and data["event"].get("type") == "message":
        user_input = data["event"].get("text", "")
        
        if user_input:
            print(f"User input: {user_input}")
            
            # Customize AI agent prompt to handle invoice-related queries
            try:
                response = openai.ChatCompletion.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": "You are an AI agent specializing in analyzing invoices and providing financial recommendations."},
                        {"role": "user", "content": user_input}
                    ] timeout=10
                )
                ai_response = response["choices"][0]["message"]["content"]
                print("AI Response:", ai_response)
                
                # Format Slack response
                return jsonify({"text": ai_response})

            except Exception as e:
                print("Error with OpenAI API:", str(e))
                return jsonify({"text": "Sorry, I encountered an error while processing your request."})

    # If no event or message found
    return jsonify({"status": "ignored"}), 200



if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

import os
import requests
import csv
from io import StringIO
from flask import Flask, request, jsonify

app = Flask(__name__)

# Retrieve the Slack bot token from environment variables
SLACK_BOT_TOKEN = os.getenv('SLACK_BOT_TOKEN')

# Function to process the CSV file
def process_csv_file(file_url):
    headers = {
        'Authorization': f'Bearer {SLACK_BOT_TOKEN}'  # Using the environment variable
    }

    # Download the file
    response = requests.get(file_url, headers=headers)

    if response.status_code == 200:
        print("File downloaded successfully.")
        
        # Convert the response content to a CSV string
        csv_data = StringIO(response.text)
        
        # Parse CSV data
        csv_reader = csv.DictReader(csv_data)
        
        for row in csv_reader:
            print(f"Invoice Number: {row['Invoice Number']}, Supplier Name: {row['Supplier Name']}, Amount: {row['Invoice Amount']}")
        
        # Process the data and return your response here
        return "Invoices processed successfully!"
    else:
        print(f"Failed to download file. Status code: {response.status_code}")
        return "Failed to download the file."

# Slack Event handler
@app.route("/slack/events", methods=["POST"])
def slack_event():
    data = request.json
    event_data = data.get("event", {})

    if event_data.get("type") == "message" and "files" in event_data:
        file_url = event_data["files"][0]["url_private_download"]
        result = process_csv_file(file_url)
        
        # Send a response to Slack with the result
        return jsonify({"text": result})

    return jsonify({"status": "ignored"})

if __name__ == "__main__":
    app.run(debug=True)
