import React, { useState, useEffect } from 'react';
import axios from 'axios';

const FlightDetails = ({ flightId }) => {
  const [flightDetails, setFlightDetails] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchFlightDetails = async () => {
      try {
        const response = await axios.get(`/flights/${flightId}`);
        setFlightDetails(response.data);
        setError(null);
      } catch (err) {
        if (err.response && err.response.status === 404) {
          setError("Flight not found");
        } else {
          setError("Failed to fetch flight details");
        }
        setFlightDetails(null);
      } finally {
        setLoading(false);
      }
    };

    fetchFlightDetails();
  }, [flightId]);

  if (loading) {
    return <div>Loading flight details...</div>;
  }

  if (error) {
    return <div>Error: {error}</div>;
  }

  if (!flightDetails) {
    return <div>No flight details available.</div>;
  }

  return (
    <div>
      <h2>Flight Details</h2>
      <p><strong>ID:</strong> {flightDetails.id}</p>
      <p><strong>Price:</strong> {flightDetails.price}</p>
      <p><strong>Aircraft:</strong> {flightDetails.aircraft}</p>
      <p><strong>Arrival Time:</strong> {flightDetails.arrival_time}</p>
      <p><strong>Departure Time:</strong> {flightDetails.departure_time}</p>
    </div>
  );
};

export default FlightDetails;