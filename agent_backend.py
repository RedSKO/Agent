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
    if not verify_slack_request(request):
        return "Request verification failed", 400

    data = request.get_json()

    # Handle Slack challenge verification (initial setup)
    if "challenge" in data:
        return jsonify({"challenge": data["challenge"]})

    # Process message events for invoice-related queries
    if "event" in data and data["event"].get("type") == "message":
        user_input = data["event"].get("text", "")
        user_id = data["event"].get("user")

        # Ignore messages from the bot itself
        if user_id == data["event"].get("bot_id"):
            return jsonify({"status": "ignored"}), 200

        if user_input:
            # Customize AI agent prompt for invoice analysis
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an AI agent specializing in analyzing invoices and providing financial recommendations."},
                    {"role": "user", "content": user_input}
                ]
            )
            ai_response = response["choices"][0]["message"]["content"]

            # Format the Slack response with AI-generated recommendation
            return jsonify({"text": ai_response})

    return jsonify({"status": "ignored"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
