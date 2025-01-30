from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)

# Dummy invoice data
invoices = [
    {"id": 1, "supplier": "Supplier A", "due_date": "2025-02-05", "amount": 1500, "discount": 5, "payment_terms": "Net 30", "status": "unpaid"},
    {"id": 2, "supplier": "Supplier B", "due_date": "2025-02-01", "amount": 1200, "discount": 2, "payment_terms": "Net 15", "status": "unpaid"},
    {"id": 3, "supplier": "Supplier C", "due_date": "2025-02-10", "amount": 2000, "discount": 10, "payment_terms": "Net 45", "status": "unpaid"},
    {"id": 4, "supplier": "Supplier D", "due_date": "2025-02-03", "amount": 3000, "discount": 0, "payment_terms": "Net 60", "status": "unpaid"},
]

def parse_date(date_str):
    return datetime.strptime(date_str, "%Y-%m-%d")

def prioritize_payments():
    # Logic to sort invoices by due date and discount
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

def detect_anomalies():
    # Simple rule-based anomaly detection: unusually high amounts
    threshold = 2500
    anomalies = [f"Invoice {inv['id']} from {inv['supplier']} has an unusually high amount of ${inv['amount']}."
                 for inv in invoices if inv["amount"] > threshold]
    return anomalies

@app.route("/analyze", methods=["POST"])
def analyze():
    # Handle analysis request
    recommendations = prioritize_payments()
    anomalies = detect_anomalies()
    return jsonify({
        "recommendations": recommendations,
        "anomalies": anomalies
    })

@app.route("/pay_invoice", methods=["POST"])
def pay_invoice():
    # Simulate marking an invoice as paid
    invoice_id = request.json.get("invoice_id")
    for invoice in invoices:
        if invoice["id"] == invoice_id and invoice["status"] == "unpaid":
            invoice["status"] = "paid"
            return jsonify({"message": f"Invoice {invoice_id} marked as paid."})
    return jsonify({"error": "Invoice not found or already paid."}), 404

if __name__ == "__main__":
    app.run(debug=True)
