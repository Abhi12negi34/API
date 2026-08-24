const express = require('express');
const router = express.Router();

// Mock flight data (replace with database integration in a real application)
const flights = [
    { id: 1, price: 200, aircraft: 'Boeing 737', arrival_time: '10:00', departure_time: '08:00' },
    { id: 2, price: 350, aircraft: 'Airbus A320', arrival_time: '14:30', departure_time: '12:00' },
    { id: 3, price: 500, aircraft: 'Boeing 777', arrival_time: '18:00', departure_time: '15:30' },
];

// GET /flights/:flightId
router.get('/flights/:flightId', (req, res) => {
    const flightId = parseInt(req.params.flightId);
    const flight = flights.find(f => f.id === flightId);

    if (!flight) {
        return res.status(404).json({ error: 'Flight not found' });
    }

    // Check for seat availability (edge case)
    const hasSeats = flight.price > 0; // simplistic check

    if (!hasSeats) {
        return res.status(200).json({
            ...flight,
            message: 'No seats available on this flight.'
        });
    }

    res.status(200).json(flight);
});

module.exports = router;