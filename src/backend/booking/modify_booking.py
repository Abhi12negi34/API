from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)

# Assume a database connection is established in MOD-006
# For this example, we'll use a dictionary as a mock database
bookings = {
    "123": {"date": "2024-03-15", "time": "10:00", "services": ["haircut", "shampoo"]},
    "456": {"date": "2024-03-16", "time": "14:00", "services": ["manicure", "pedicure"]},
}

def validate_date(date_str):
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except ValueError:
        return False

def validate_time(time_str):
    try:
        datetime.strptime(time_str, '%H:%M')
        return True
    except ValueError:
        return False

@app.route('/bookings/<bookingId>', methods=['PUT'])
def modify_booking(bookingId):
    """
    Modifies an existing booking.
    """
    try:
        data = request.get_json()
        date = data.get('date')
        time = data.get('time')
        services = data.get('services')

        if not all([date, time, services]):
            return jsonify({"error": "Missing required fields"}), 400

        if not validate_date(date):
            return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400
        
        if not validate_time(time):
            return jsonify({"error": "Invalid time format. Use HH:MM"}), 400

        if bookingId not in bookings:
            return jsonify({"error": "Booking not found"}), 404

        # In a real application, you would check for conflicts with other bookings
        # and handle associated flights/accommodations.  This is a placeholder.
        # For example, check if the new time/date is available.  
        # If the booking has flights/accommodations, check if changing the date/time
        # affects those arrangements and handle accordingly (e.g., update flights/accommodations,
        # or return an error if the change isn't possible).

        bookings[bookingId]["date"] = date
        bookings[bookingId]["time"] = time
        bookings[bookingId]["services"] = services
        
        return jsonify({"status": "updated", "bookingId": bookingId}), 200

    except Exception as e:
        print(e)
        return jsonify({"error": "Invalid request"}), 400

if __name__ == '__main__':
    app.run(debug=True)