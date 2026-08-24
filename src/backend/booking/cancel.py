from flask import Flask, request, jsonify
import logging
import datetime

# Assuming MOD-011 handles booking data access
from src.backend.booking.booking_data import get_booking, update_booking
# Assuming MOD-012 handles refund processing
from src.backend.payment.refund import process_refund

app = Flask(__name__)
logger = logging.getLogger(__name__)

def is_cancellable(booking):
    """
    Checks if a booking is cancellable based on the cancellation policy.
    This is a simplified example, adjust based on your actual policy.
    """
    now = datetime.datetime.now()
    cancellation_deadline = booking['check_in_date'] - datetime.timedelta(days=2)  # Example: 2 days before check-in
    return now <= cancellation_deadline

def calculate_refund_amount(booking):
    """
    Calculates the refund amount based on the cancellation policy.
    This is a placeholder, replace with your actual calculation logic.
    """
    # Example: Full refund if cancelled within the cancellation window
    if is_cancellable(booking):
        return booking['total_price']
    else:
        return 0  # No refund if outside the cancellation window


@app.route("/bookings/<string:bookingId>", methods=["DELETE"])
def cancel_booking(bookingId):
    """
    Cancels a booking with the given ID.
    """
    try:
        booking = get_booking(bookingId)
        if not booking:
            logger.warning(f"Booking with ID {bookingId} not found.")
            return jsonify({"error": "Booking not found"}), 404

        if booking['status'] == 'cancelled':
            logger.warning(f"Booking with ID {bookingId} is already cancelled.")
            return jsonify({"error": "Booking is already cancelled"}), 400
        
        if not is_cancellable(booking):
            logger.warning(f"Cancellation request for booking {bookingId} outside the cancellation window.")
            return jsonify({"error": "Cancellation is not allowed for this booking"}), 400

        # Process refund
        refund_amount = calculate_refund_amount(booking)
        try:
            if refund_amount > 0:
                process_refund(booking['payment_id'], refund_amount)
                logger.info(f"Refund of {refund_amount} processed for booking {bookingId}.")
            else:
                logger.info(f"No refund applicable for booking {bookingId}.")

        except Exception as e:
            logger.error(f"Refund processing failed for booking {bookingId}: {e}")
            # Potentially retry or alert an administrator.  We don't want to fail the whole cancel operation because of a refund failure, but log it.
            # Consider implementing a dead letter queue for failed refunds.

        # Update booking status
        update_booking(bookingId, {"status": "cancelled"})
        logger.info(f"Booking {bookingId} cancelled successfully.")
        return jsonify({"status": "cancelled"}), 200

    except Exception as e:
        logger.exception(f"An error occurred while cancelling booking {bookingId}: {e}")
        return jsonify({"error": "An unexpected error occurred"}), 500

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app.run(debug=True)