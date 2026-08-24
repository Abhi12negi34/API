import os
import json
from typing import Dict
from datetime import datetime

# Assuming MOD-011 handles booking details and provides a booking ID
from src.backend.booking import booking_module as MOD_011  

# Third-party payment gateway integration (replace with actual integration)
class PaymentGateway:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def process_payment(self, amount: float, token: str) -> Dict:
        """Simulates processing a payment with a payment gateway."""
        # In a real implementation, this would interact with the payment gateway API.
        # For this example, we simulate success or failure.
        import random
        if random.random() < 0.9:  # 90% success rate for simulation
            return {"status": "success", "transaction_id": "txn_" + str(int(datetime.now().timestamp()))}
        else:
            return {"status": "failure", "message": "Payment declined."}

def tokenize_payment_info(payment_info: Dict) -> str:
    """
    Tokenizes sensitive payment information.
    In a production environment, this would involve a secure tokenization service.
    """
    # This is a placeholder for actual tokenization.  NEVER store raw card details.
    # Replace with a call to a secure tokenization provider.
    token = "token_" + str(hash(json.dumps(payment_info))) # Simple hash for demonstration - NOT secure in production!
    return token

def process_booking_payment(booking_id: str, payment_info: Dict) -> Dict:
    """
    Processes a payment for a given booking.

    Args:
        booking_id: The ID of the booking.
        payment_info: A dictionary containing payment details (e.g., card number, expiry date, CVV).

    Returns:
        A dictionary containing the payment status and transaction details.
    """

    # 1. Validate Booking ID
    try:
        MOD_011.get_booking_details(booking_id) # Ensure the booking exists
    except ValueError as e:
        return {"status": "failure", "message": str(e)}

    # 2. Tokenize Payment Information
    token = tokenize_payment_info(payment_info)

    # 3. Retrieve Booking Amount (from MOD-011)
    booking_details = MOD_011.get_booking_details(booking_id)
    amount = booking_details['total_price']

    # 4. Process Payment via Gateway
    payment_gateway = PaymentGateway(api_key=os.environ.get("PAYMENT_GATEWAY_API_KEY", "dummy_api_key"))  # Use environment variable for API key
    payment_result = payment_gateway.process_payment(amount, token)

    # 5. Handle Payment Result
    if payment_result["status"] == "success":
        # 6. Update Booking Status (in MOD-011) - mark as paid
        try:
            MOD_011.update_booking_status(booking_id, "paid", payment_result["transaction_id"])
        except Exception as e:
            return {"status": "failure", "message": f"Failed to update booking status: {str(e)}"}

        return {"status": "success", "transaction_id": payment_result["transaction_id"], "message": "Payment processed successfully."}
    else:
        return {"status": "failure", "message": payment_result["message"]}
    
# Example Usage (for testing)
if __name__ == "__main__":
    # Simulate a booking ID
    booking_id = "booking_123"
    
    # Simulate payment information
    payment_info = {
        "card_number": "1234567890123456",
        "expiry_date": "12/24",
        "cvv": "123"
    }

    payment_result = process_booking_payment(booking_id, payment_info)
    print(payment_result)