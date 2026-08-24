import React, { useState, useEffect } from 'react';
import axios from 'axios';
import BookingDetails from './BookingDetails';

const BookingList = () => {
  const [bookings, setBookings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [userId, setUserId] = useState(localStorage.getItem('userId')); // Assuming userId is stored in localStorage

  useEffect(() => {
    const fetchBookings = async () => {
      try {
        if (!userId) {
          setError('User ID not found. Please log in.');
          return;
        }

        const response = await axios.get(`/bookings?userId=${userId}`);
        setBookings(response.data);
        setLoading(false);
      } catch (err) {
        setError('Failed to fetch bookings.');
        console.error(err);
        setLoading(false);
      }
    };

    fetchBookings();
  }, [userId]);

  if (loading) {
    return <p>Loading bookings...</p>;
  }

  if (error) {
    return <p>Error: {error}</p>;
  }

  if (bookings.length === 0) {
    return <p>No bookings found.</p>;
  }

  return (
    <div>
      <h2>Your Bookings</h2>
      <ul>
        {bookings.map((booking) => (
          <li key={booking.bookingId}>
            <BookingDetails booking={booking} />
          </li>
        ))}
      </ul>
    </div>
  );
};

export default BookingList;