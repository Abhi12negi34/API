const express = require('express');
const router = express.Router();
const { CircuitBreaker } = require('@cityofzion/circuit-breaker');

// Mock destination data (replace with database or external API call)
const destinations = [
  { id: '1', name: 'Paris', location: 'France' },
  { id: '2', name: 'Tokyo', location: 'Japan' },
  { id: '3', name: 'New York', location: 'USA' },
  { id: '4', name: 'London', location: 'UK' },
  { id: '5', name: 'Sydney', location: 'Australia' },
];

// Implement Circuit Breaker
const breaker = new CircuitBreaker({
  timeout: 5000, // 5 seconds
  resetTimeout: 10000, // 10 seconds
});


router.get('/destinations', (req, res) => {
  const { query, location } = req.query;

  if (!query || !location) {
    return res.status(400).json({ error: 'Invalid query parameters. Both "query" and "location" are required.' });
  }

  const filteredDestinations = destinations.filter(destination =>
    destination.name.toLowerCase().includes(query.toLowerCase()) &&
    destination.location.toLowerCase() === location.toLowerCase()
  );

  if (filteredDestinations.length === 0) {
    return res.status(200).json([]); // Return empty array if no results found
  }

  breaker.call(() => {
    return Promise.resolve(filteredDestinations);
  })
  .then(results => {
    res.status(200).json(results);
  })
  .catch(err => {
    console.error("API call failed:", err);
    res.status(500).json({ error: 'Failed to retrieve destinations. Please try again later.' });
  });
});

module.exports = router;