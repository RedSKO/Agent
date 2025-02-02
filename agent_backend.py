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
    print("Received data:", data)  # Debugging line

    # Handle Slack challenge verification
    if "challenge" in data:
        print("Challenge received:", data["challenge"])  # Debugging line
        return jsonify({"challenge": data["challenge"]})

    # Handle file uploads in Slack
    if "event" in data and data["event"].get("type") == "file_shared":
        print("File shared event detected.")  # Debugging line
        file_info = data["event"].get("file")
        file_url = file_info.get("url_private_download")
        
        # Download the file content
        headers = {'Authorization': f"Bearer {slack_token}"}
        file_content = download_file(file_url)
        
        # Parse the Excel file
        invoice_data = parse_excel(file_content)
        print("Invoice data parsed:", invoice_data)  # Debugging line
        
        # Generate recommendations using OpenAI based on the invoice data
        recommendations = generate_openai_recommendations(invoice_data)
        print("Generated recommendations:", recommendations)  # Debugging line
        
        # Send the recommendations back to Slack
        try:
            response = client.chat_postMessage(
                channel=data["event"]["channel"],
                text=recommendations
            )
            return jsonify({"status": "success"}), 200
        except SlackApiError as e:
            print("Error posting message to Slack:", str(e))  # Debugging line
            return jsonify({"error": str(e)}), 400

    return jsonify({"status": "ignored"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
