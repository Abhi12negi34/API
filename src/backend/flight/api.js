const express = require('express');
const router = express.Router();

// Mock flight data (replace with actual API integration)
const mockFlights = [
  { id: '1', price: 250, airline: 'United', arrival_time: '10:00', departure_time: '08:00' },
  { id: '2', price: 300, airline: 'Delta', arrival_time: '12:00', departure_time: '10:00' },
  { id: '3', price: 200, airline: 'American', arrival_time: '14:00', departure_time: '12:00' },
];

router.get('/flights', (req, res) => {
  const { origin, destination, departure_date, return_date } = req.query;

  // Validate search criteria
  if (!origin || !destination || !departure_date || !return_date) {
    return res.status(400).json({ error: 'Invalid search criteria' });
  }

  // Simulate flight search (replace with actual API call)
  const matchingFlights = mockFlights.filter(flight => {
    // In a real implementation, this would involve querying a flight database or API
    // based on origin, destination, and dates.  For this example, we just return
    // all flights.
    return true;
  });

  if (matchingFlights.length === 0) {
    return res.status(200).json([]); // Return an empty array if no flights are found
  }
  
  // Simulate API timeout handling (example using setTimeout)
  // In a real app, use a proper timeout mechanism with an actual API call
  setTimeout(() => {
    res.status(200).json(matchingFlights);
  }, 500); // Simulate a 500ms delay
});

module.exports = router;