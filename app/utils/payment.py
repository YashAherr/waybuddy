import os
import razorpay
import hmac
import hashlib

SEEKER_FEE_PAISE = 9900  # Rs.99


def is_payment_required():
    return os.environ.get('PAYMENT_REQUIRED', 'false').lower() == 'true'


def get_razorpay_client():
    key_id = os.environ.get('RAZORPAY_KEY_ID')
    key_secret = os.environ.get('RAZORPAY_KEY_SECRET')
    return razorpay.Client(auth=(key_id, key_secret))


def create_order(receipt_id):
    """
    Creates a Razorpay order for the seeker fee.
    receipt_id should be a string uniquely identifying this seeker (e.g. str(seeker.id)).
    Returns the Razorpay order dict (contains 'id', 'amount', 'currency', etc.)
    """
    client = get_razorpay_client()
    order = client.order.create({
        'amount': SEEKER_FEE_PAISE,
        'currency': 'INR',
        'receipt': receipt_id,
        'payment_capture': 1
    })
    return order


def verify_webhook_signature(request_body, signature):
    """
    Verifies the X-Razorpay-Signature header against the raw request body
    using the webhook secret (NOT the API key secret).
    request_body must be the raw bytes of the request, not parsed JSON.
    Returns True if valid, False otherwise.
    """
    webhook_secret = os.environ.get('RAZORPAY_WEBHOOK_SECRET')
    if not webhook_secret:
        return False

    expected_signature = hmac.new(
        webhook_secret.encode('utf-8'),
        request_body,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected_signature, signature)