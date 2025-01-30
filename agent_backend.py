import requests
from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)

SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/YOUR_WEBHOOK_URL"

invoices = [
    {"id": 1, "supplier": "Supplier A", "due_date": "2025-02-05", "amount": 1500, "discount": 5, "status": "unpaid"},
    {"id": 2, "supplier": "Supplier B", "due_date": "2025-02-01", "amount": 1200, "discount": 2, "status": "unpaid"},
    {"id": 3, "supplier": "Supplier C", "due_date": "2025-02-10", "amount": 2000, "discount": 10, "status": "unpaid"},
]

def parse_date(date_str):
    return datetime.strptime(date_str, "%Y-%m-%d")

def prioritize_payments():
    today = datetime.now()
    recommendations = []

    for invoice in sorted(invoices, key=lambda x: (parse_date(x["due_date"]), -x["discount"])):
        due_date = parse_date(invoice["due_date"])
        days_until_due = (due_date - today).days
        urgency = "High" if days_until_due <= 3 else "Medium" if days_until_due <= 7 else "Low"

        recommendation = (
            f"Invoice {invoice['id']} from {invoice['supplier']} (Amount: ${invoice['amount']}) "
            f"is due on {invoice['due_date']} ({days_until_due} days left). "
            f"Discount: {invoice['discount']}%. Urgency: {urgency}."
        )
        recommendations.append(recommendation)
    return recommendations

def send_to_slack(message):
    payload = {"text": message}
    response = requests.post(SLACK_WEBHOOK_URL, json=payload)
    if response.status_code != 200:
        print("Failed to send message to Slack:", response.text)

@app.route("/analyze", methods=["POST"])
def analyze():
    recommendations = prioritize_payments()
    for rec in recommendations:
        send_to_slack(rec)
    return jsonify({"message": "Recommendations sent to Slack."})

@app.route("/pay_invoice", methods=["POST"])
def pay_invoice():
    invoice_id = request.json.get("invoice_id")
    for invoice in invoices:
        if invoice["id"] == invoice_id and invoice["status"] == "unpaid":
            invoice["status"] = "paid"
            send_to_slack(f"Invoice {invoice_id} marked as paid.")
            return jsonify({"message": f"Invoice {invoice_id} marked as paid."})
    return jsonify({"error": "Invoice not found or already paid."}), 404

if __name__ == "__main__":
    app.run(debug=True)
