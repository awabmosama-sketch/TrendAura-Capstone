from app.models.order import Order


def run_fraud_pipeline(order: Order) -> dict:
    score = 0
    flags: list[str] = []
    if order.payment_method == "bank_transfer":
        score += 10
    if float(order.final_amount) >= 5000:
        score += 25
        flags.append("high_value_order")
    if order.payment_status == "pending_verification":
        score += 15
        flags.append("payment_verification_required")
    verdict = "Flagged" if score >= 50 else "Safe"
    return {"order_id": order.id, "fraud_score": score, "verdict": verdict, "flags": flags}
