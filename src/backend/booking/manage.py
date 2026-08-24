from flask import Flask, request, jsonify
import os
import logging

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Assuming MOD-001 provides user authentication/authorization
# and MOD-011 provides booking data access
try:
    from mod_001 import authenticate_user  # Replace with actual import path
    from mod_011 import get_bookings_by_user_id  # Replace with actual import path
except ImportError as e:
    logging.error(f"Failed to import dependencies: {e}")
    # Handle the missing dependencies appropriately, e.g., raise an exception
    raise

@app.route("/bookings", methods=["GET"])
def get_user_bookings():
    """
    Retrieves a list of bookings for a given user.
    """
    try:
        user_id = request.args.get("userId")
        if not user_id:
            return jsonify({"error": "User ID is required"}), 400

        # Authenticate user (using MOD-001)
        if not authenticate_user(user_id): # Assume authenticate_user returns True if authenticated, False otherwise
            return jsonify({"error": "Unauthorized"}), 401
        
        # Retrieve bookings (using MOD-011)
        bookings = get_bookings_by_user_id(user_id)

        if not bookings:
            return jsonify({"message": "No bookings found for this user"}), 200

        # Filter out deleted bookings
        valid_bookings = [booking for booking in bookings if booking.get("status") != "deleted"]

        # Format the response
        response_body = []
        for booking in valid_bookings:
            response_body.append({
                "status": booking.get("status", "unknown"),
                "bookingId": booking.get("bookingId", "unknown")
            })
        
        return jsonify(response_body), 200
    
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        return jsonify({"error": "Internal server error"}), 500

if __name__ == "__main__":
    app.run(debug=True)