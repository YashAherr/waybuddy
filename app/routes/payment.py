from flask import Blueprint, request, jsonify
from datetime import datetime, timezone
from ..models import db, Seeker, Payment
from ..utils.payment import verify_webhook_signature

payment_bp = Blueprint('payment', __name__)


@payment_bp.route('/payment/webhook', methods=['POST'])
def razorpay_webhook():
    signature = request.headers.get('X-Razorpay-Signature', '')
    raw_body = request.get_data()

    if not verify_webhook_signature(raw_body, signature):
        return jsonify({'error': 'invalid signature'}), 400

    payload = request.get_json()
    event = payload.get('event')

    if event == 'payment.captured':
        payment_entity = payload['payload']['payment']['entity']
        razorpay_order_id = payment_entity.get('order_id')
        razorpay_payment_id = payment_entity.get('id')

        payment_row = Payment.query.filter_by(razorpay_order_id=razorpay_order_id).first()
        if payment_row:
            payment_row.status = 'paid'
            payment_row.razorpay_payment_id = razorpay_payment_id
            payment_row.razorpay_signature = signature
            payment_row.paid_at = datetime.now(timezone.utc)

            seeker = Seeker.query.get(payment_row.seeker_id)
            if seeker:
                seeker.is_paid = True

            db.session.commit()

    return jsonify({'status': 'ok'}), 200