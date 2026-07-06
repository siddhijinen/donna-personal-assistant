import os
import razorpay

def get_razorpay_client():
    key_id = os.getenv("RAZORPAY_KEY_ID")
    key_secret = os.getenv("RAZORPAY_KEY_SECRET")
    if not key_id or not key_secret or key_id.startswith("rzp_test_your"):
        return None
    return razorpay.Client(auth=(key_id, key_secret))

def create_payment_link(amount: float, description: str, customer_email: str = "customer@example.com") -> str:
    """Create a Razorpay payment link for the given amount (in INR natively but amount arg is standard currency)."""
    client = get_razorpay_client()
    if not client:
        return "Razorpay is not configured. Please set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET in .env"
    
    # Razorpay expects amount in paise (smallest currency unit, e.g., 100 paise = 1 INR)
    # We will assume the amount given is in INR for simplicity, so multiply by 100.
    amount_in_paise = int(amount * 100)
    
    try:
        payment_link = client.payment_link.create({
            "amount": amount_in_paise,
            "currency": "INR",
            "accept_partial": False,
            "description": description,
            "customer": {
                "name": "Customer",
                "email": customer_email,
                "contact": "+919999999999"
            },
            "notify": {
                "sms": False,
                "email": False
            },
            "reminder_enable": False,
        })
        return f"Payment link created successfully: {payment_link.get('short_url')}"
    except Exception as e:
        return f"Razorpay error: {str(e)}"
