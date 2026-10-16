from app.core.config import settings
from app.agents.contracts import RefundState
from app.models.order import Order


ELIGIBLE_STATUSES = {"confirmed", "shipped", "delivered"}


def run_refund_agent(order: Order, user_message: str = "") -> RefundState:
    amount = float(order.final_amount)
    policy_ok = order.status in ELIGIBLE_STATUSES and amount <= settings.REFUND_AUTO_APPROVE_LIMIT

    if policy_ok:
        decision = "approved"
        admin_note = "Automatically approved within the refund policy limit."
    else:
        decision = "escalated"
        admin_note = "Escalated for admin review because the order is outside the automatic refund policy."

    return {
        "user_id": order.user_id or 0,
        "order_id": order.id,
        "user_message": user_message,
        "intent": "refund_request",
        "amount": amount,
        "policy_ok": policy_ok,
        "decision": decision,
        "admin_note": admin_note,
    }
