import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import axios from 'axios';

const BookingDetails = () => {
  const { bookingId } = useParams();
  const [booking, setBooking] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchBookingDetails = async () => {
      try {
        // Assuming your backend API endpoint to fetch booking details by ID
        const response = await axios.get(`/bookings/${bookingId}`); 
        setBooking(response.data);
      } catch (err) {
        console.error("Error fetching booking details:", err);
        setError(err.message || "Failed to fetch booking details.");
      } finally {
        setLoading(false);
      }
    };

    fetchBookingDetails();
  }, [bookingId]);

  if (loading) {
    return <p>Loading booking details...</p>;
  }

  if (error) {
    return <p>Error: {error}</p>;
  }

  if (!booking) {
    return <p>Booking not found.</p>;
  }

  return (
    <div>
      <h2>Booking Details</h2>
      <p><strong>Booking ID:</strong> {booking.bookingId}</p>
      <p><strong>Status:</strong> {booking.status}</p>
      {/* Add more booking details as needed */}
    </div>
  );
};

export default BookingDetails;