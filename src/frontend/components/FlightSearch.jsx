import React, { useState, useEffect } from 'react';

const FlightSearch = () => {
  const [origin, setOrigin] = useState('');
  const [destination, setDestination] = useState('');
  const [departureDate, setDepartureDate] = useState('');
  const [returnDate, setReturnDate] = useState('');
  const [flights, setFlights] = useState([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!origin || !destination || !departureDate || !returnDate) {
      setError('Please fill in all fields.');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await fetch('/flights', {
        method: 'GET',
        params: {
          origin,
          destination,
          departure_date: departureDate,
          return_date: returnDate,
        },
      });

      if (!response.ok) {
        if (response.status === 400) {
          setError('Invalid search criteria');
        } else {
          setError(`Flight search failed with status: ${response.status}`);
        }
        setFlights([]); // Clear previous results on error
        setLoading(false);
        return;
      }

      const data = await response.json();
      setFlights(data);
    } catch (err) {
      if (err.name === 'TimeoutError') {
        setError('Flight API timeout. Please try again.');
      } else {
        setError('An unexpected error occurred.');
        console.error("Error fetching flights:", err);
      }
      setFlights([]);
      setLoading(false);
    }
  };

  useEffect(() => {
    if (flights.length === 0 && loading === false && error === '') {
      // Handle case where no flights are available.
    }
  }, [flights, loading, error]);

  return (
    <div>
      <h1>Flight Search</h1>
      <form onSubmit={handleSubmit}>
        <div>
          <label htmlFor="origin">Origin:</label>
          <input type="text" id="origin" value={origin} onChange={(e) => setOrigin(e.target.value)} />
        </div>
        <div>
          <label htmlFor="destination">Destination:</label>
          <input type="text" id="destination" value={destination} onChange={(e) => setDestination(e.target.value)} />
        </div>
        <div>
          <label htmlFor="departureDate">Departure Date:</label>
          <input type="date" id="departureDate" value={departureDate} onChange={(e) => setDepartureDate(e.target.value)} />
        </div>
        <div>
          <label htmlFor="returnDate">Return Date:</label>
          <input type="date" id="returnDate" value={returnDate} onChange={(e) => setReturnDate(e.target.value)} />
        </div>
        <button type="submit" disabled={loading}>
          {loading ? 'Searching...' : 'Search Flights'}
        </button>
      </form>

      {error && <p style={{ color: 'red' }}>{error}</p>}

      {loading && <p>Loading flights...</p>}

      <ul>
        {flights.map((flight) => (
          <li key={flight.id}>
            {flight.airline} - {flight.departure_time} to {flight.arrival_time} - ${flight.price}
          </li>
        ))}
      </ul>
    </div>
  );
};

export default FlightSearch;