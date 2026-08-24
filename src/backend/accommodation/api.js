const express = require('express');
const router = express.Router();

// Mock accommodation data (replace with database or external API calls in a real application)
const accommodations = [
  { id: '1', name: 'Cozy Cabin', price: 100, location: 'Mountains' },
  { id: '2', name: 'Beachfront Villa', price: 250, location: 'Beach' },
  { id: '3', name: 'City Apartment', price: 150, location: 'City' },
  { id: '4', name: 'Rustic Lodge', price: 120, location: 'Mountains' },
  { id: '5', name: 'Seaside Cottage', price: 200, location: 'Beach' },
];

// In-memory cache to store search results
const cache = {};

router.get('/accommodations', (req, res) => {
  const { location, price_range, checkin_date, checkout_date } = req.query;

  // Validate search criteria (basic validation)
  if (!location || !price_range || !checkin_date || !checkout_date) {
    return res.status(400).json({ error: 'Invalid search criteria' });
  }

  // Cache key based on search parameters
  const cacheKey = `${location}-${price_range}-${checkin_date}-${checkout_date}`;

  // Check if results are cached
  if (cache[cacheKey]) {
    console.log('Serving from cache');
    return res.status(200).json(cache[cacheKey]);
  }

  // Filter accommodations based on criteria
  let filteredAccommodations = accommodations.filter(accommodation =>
    accommodation.location.toLowerCase() === location.toLowerCase()
  );

  // Apply price range filtering
  const [minPrice, maxPrice] = price_range.split('-').map(Number);
  if (isNaN(minPrice) || isNaN(maxPrice)) {
    return res.status(400).json({ error: 'Invalid price range' });
  }

  filteredAccommodations = filteredAccommodations.filter(accommodation =>
    accommodation.price >= minPrice && accommodation.price <= maxPrice
  );
  
  //Handle unavailable accommodations or dates
  if(filteredAccommodations.length === 0){
    return res.status(200).json([]);
  }

  // Cache the results
  cache[cacheKey] = filteredAccommodations;

  res.status(200).json(filteredAccommodations);
});

module.exports = router;