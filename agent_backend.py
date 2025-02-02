from flask import Flask, request, jsonify
import os
import openai

from flask import Flask, request, jsonify
import os
import openai

app = Flask(__name__)

openai.api_key = os.getenv("OPENAI_API_KEY")

@app.route("/slack/events", methods=["POST"])
def slack_events():
    data = request.get_json()

    # Handle Slack challenge verification
    if "challenge" in data:
        return jsonify({"challenge": data["challenge"]})

    # Process message events for invoice-related queries
    if "event" in data and data["event"].get("type") == "message":
        user_input = data["event"].get("text", "")
        
        if user_input:
            # Customize AI agent prompt to handle invoice-related queries
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an AI agent specializing in analyzing invoices and providing financial recommendations."},
                    {"role": "user", "content": user_input}
                ]
            )
            ai_response = response["choices"][0]["message"]["content"]

            # Format Slack response
            return jsonify({"text": ai_response})

    return jsonify({"status": "ignored"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
