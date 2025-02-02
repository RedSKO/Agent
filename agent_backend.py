import requests
from flask import Flask, request, jsonify
from datetime import datetime

import os

#app = Flask(__name__)
#app.route("/")
#def home():
#    return "Hello from AI Agent!"

#if __name__ == "__main__":
#    port = int(os.environ.get("PORT", 5000))  # Use dynamic Render port
#    app.run(host="0.0.0.0", port=port)

#app = Flask(__name__)

app = Flask(__name__)

# Load OpenAI key from environment variables
openai.api_key = os.getenv("OPENAI_API_KEY")

@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json()
    user_input = data.get("text", "Analyze invoices")

    # Query GPT model
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4", 
            messages=[
                {"role": "system", "content": "You are an expert AI assistant analyzing financial documents."},
                {"role": "user", "content": user_input}
            ]
        )
        ai_response = response["choices"][0]["message"]["content"]

        # Send response back to Slack
        response_message = {"text": f"AI Agent Response: {ai_response}"}
        slack_webhook_url = os.getenv("SLACK_WEBHOOK_URL")
        if slack_webhook_url:
            requests.post(slack_webhook_url, json=response_message)
        return jsonify({"status": "success", "response": ai_response}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
