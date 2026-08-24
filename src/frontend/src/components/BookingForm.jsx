import React, { useState } from 'react';
import axios from 'axios';

const BookingForm = () => {
  const [dates, setDates] = useState('');
  const [userId, setUserId] = useState('');
  const [flightId, setFlightId] = useState('');
  const [vehicleId, setVehicleId] = useState('');
  const [destinationId, setDestinationId] = useState('');
  const [accommodationId, setAccommodationId] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();

    // Validation
    if (!dates || !userId || !flightId || !vehicleId || !destinationId || !accommodationId) {
      setErrorMessage('All fields are required.');
      return;
    }

    try {
      const response = await axios.post('/bookings', {
        dates,
        userId,
        flightId,
        vehicleId,
        destinationId,
        accommodationId,
      });

      if (response.status === 201) {
        setSuccessMessage(`Booking created successfully! Booking ID: ${response.data.bookingId}`);
        setErrorMessage('');
        // Clear the form
        setDates('');
        setUserId('');
        setFlightId('');
        setVehicleId('');
        setDestinationId('');
        setAccommodationId('');
      } else {
        setErrorMessage('Booking creation failed.');
      }
    } catch (error) {
      if (error.response && error.response.status === 400) {
        setErrorMessage('Validation failed: ' + error.response.data.message);
      } else if (error.response && error.response.status === 500) {
        setErrorMessage('Internal server error.');
      } else {
        setErrorMessage('An unexpected error occurred.');
      }
    }
  };

  return (
    <div>
      <h2>Create Booking</h2>
      {errorMessage && <div style={{ color: 'red' }}>{errorMessage}</div>}
      {successMessage && <div style={{ color: 'green' }}>{successMessage}</div>}

      <form onSubmit={handleSubmit}>
        <div>
          <label htmlFor="dates">Dates:</label>
          <input
            type="text"
            id="dates"
            value={dates}
            onChange={(e) => setDates(e.target.value)}
            required
          />
        </div>
        <div>
          <label htmlFor="userId">User ID:</label>
          <input
            type="text"
            id="userId"
            value={userId}
            onChange={(e) => setUserId(e.target.value)}
            required
          />
        </div>
        <div>
          <label htmlFor="flightId">Flight ID:</label>
          <input
            type="text"
            id="flightId"
            value={flightId}
            onChange={(e) => setFlightId(e.target.value)}
            required
          />
        </div>
        <div>
          <label htmlFor="vehicleId">Vehicle ID:</label>
          <input
            type="text"
            id="vehicleId"
            value={vehicleId}
            onChange={(e) => setVehicleId(e.target.value)}
            required
          />
        </div>
        <div>
          <label htmlFor="destinationId">Destination ID:</label>
          <input
            type="text"
            id="destinationId"
            value={destinationId}
            onChange={(e) => setDestinationId(e.target.value)}
            required
          />
        </div>
        <div>
          <label htmlFor="accommodationId">Accommodation ID:</label>
          <input
            type="text"
            id="accommodationId"
            value={accommodationId}
            onChange={(e) => setAccommodationId(e.target.value)}
            required
          />
        </div>

        <button type="submit">Create Booking</button>
      </form>
    </div>
  );
};

export default BookingForm;