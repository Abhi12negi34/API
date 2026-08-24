from flask import Flask, request, jsonify
import uuid
import psycopg2
from datetime import datetime

app = Flask(__name__)

# Database configuration (replace with your actual credentials)
DATABASE_URL = "postgresql://user:password@host:port/database"

def validate_booking_data(data):
    """Validates the booking data against the expected schema."""
    required_fields = ["dates", "userId", "flightId", "vehicleId", "destinationId", "accommodationId"]
    for field in required_fields:
        if field not in data:
            return False, f"Missing required field: {field}"
    
    # Add more specific validation as needed (e.g., check data types, valid IDs)
    return True, None

@app.route('/bookings', methods=['POST'])
def create_booking():
    """
    Creates a new booking based on the provided data.
    """
    try:
        data = request.get_json()

        # Validate the booking data
        is_valid, error_message = validate_booking_data(data)
        if not is_valid:
            return jsonify({"status": "error", "message": error_message}), 400

        # Generate a unique booking ID
        booking_id = str(uuid.uuid4())

        # Establish database connection
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        # Start a transaction to ensure atomicity
        conn.autocommit = False

        try:
            # Insert the booking record into the 'bookings' table
            insert_query = """
                INSERT INTO bookings (booking_id, dates, user_id, flight_id, vehicle_id, destination_id, accommodation_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s);
            """
            cur.execute(insert_query, (booking_id, data["dates"], data["userId"], data["flightId"], data["vehicleId"], data["destinationId"], data["accommodationId"]))
            
            # Commit the transaction
            conn.commit()

        except Exception as e:
            # Rollback the transaction in case of an error
            conn.rollback()
            print(f"Error creating booking: {e}")
            return jsonify({"status": "error", "message": "Internal server error"}), 500
        finally:
            # Close the cursor and connection
            cur.close()
            conn.close()

        return jsonify({"status": "success", "bookingId": booking_id}), 201

    except Exception as e:
        print(f"Unexpected error: {e}")
        return jsonify({"status": "error", "message": "Internal server error"}), 500

if __name__ == '__main__':
    app.run(debug=True)