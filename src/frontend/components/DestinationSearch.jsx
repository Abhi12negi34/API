import React, { useState, useEffect } from 'react';

const DestinationSearch = () => {
  const [query, setQuery] = useState('');
  const [location, setLocation] = useState('');
  const [destinations, setDestinations] = useState([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const circuitBreaker = {
    state: 'closed',
    failureCount: 0,
    threshold: 3, // Allow 3 failures before opening the circuit
    openDuration: 5000, // Duration to keep the circuit open (in ms)
    lastFailureTime: null
  };

  const searchDestinations = async () => {
    if (!query && !location) {
      setDestinations([]);
      setError('');
      return;
    }

    if (circuitBreaker.state === 'open') {
      const now = Date.now();
      if (now - circuitBreaker.lastFailureTime < circuitBreaker.openDuration) {
        setError('Service unavailable. Please try again later.');
        return;
      } else {
        circuitBreaker.state = 'half-open';
      }
    }

    setLoading(true);
    setError('');

    try {
      const response = await fetch('/destinations?query=' + query + '&location=' + location);

      if (!response.ok) {
        if (response.status === 400) {
          setError('Invalid query parameters');
        } else {
          setError('Failed to fetch destinations');
          circuitBreaker.failureCount++;
          circuitBreaker.lastFailureTime = Date.now();
          if (circuitBreaker.failureCount >= circuitBreaker.threshold) {
            circuitBreaker.state = 'open';
          }
        }
        throw new Error('Network response was not ok');
      }

      const data = await response.json();
      setDestinations(data);
      circuitBreaker.failureCount = 0;
      circuitBreaker.state = 'closed';

    } catch (err) {
      setError('Failed to fetch destinations');
      circuitBreaker.failureCount++;
      circuitBreaker.lastFailureTime = Date.now();
      if (circuitBreaker.failureCount >= circuitBreaker.threshold) {
        circuitBreaker.state = 'open';
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    searchDestinations();
  }, [query, location]);

  const handleInputChange = (e) => {
    if (e.target.name === 'query') {
      setQuery(e.target.value);
    } else if (e.target.name === 'location') {
      setLocation(e.target.value);
    }
  };

  return (
    <div>
      <div>
        <label htmlFor="query">Query:</label>
        <input
          type="text"
          id="query"
          name="query"
          value={query}
          onChange={handleInputChange}
        />
      </div>
      <div>
        <label htmlFor="location">Location:</label>
        <input
          type="text"
          id="location"
          name="location"
          value={location}
          onChange={handleInputChange}
        />
      </div>

      {loading && <p>Loading...</p>}
      {error && <p style={{ color: 'red' }}>{error}</p>}

      <ul>
        {destinations.map((destination) => (
          <li key={destination.id}>
            {destination.name} - {destination.location}
          </li>
        ))}
      </ul>
    </div>
  );
};

export default DestinationSearch;