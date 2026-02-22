import os
import stripe

stripe.api_key = os.environ.get("STRIPE_API_KEY", "sk_test_mock")

def process_support_payment(amount_cents: int, source: str) -> dict:
    """
    Process a fiat payment for track support.
    If STRIPE_API_KEY is not set or is a mock key, this simulates a successful payment.
    """
    if stripe.api_key == "sk_test_mock" or not stripe.api_key:
        print(f"Mocking Stripe payment of {amount_cents} cents.")
        # Return a mock successful charge object
        import uuid
        return {
            "id": f"ch_mock_{uuid.uuid4().hex[:16]}",
            "status": "succeeded",
            "amount": amount_cents
        }

    try:
        charge = stripe.Charge.create(
            amount=amount_cents,
            currency="usd",
            source=source,
            description="STELLOS Track Support"
        )
        return charge
    except stripe.error.StripeError as e:
        print(f"Stripe error: {e}")
        raise
