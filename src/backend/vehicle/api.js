const express = require('express');
const router = express.Router();

// Mock vehicle data (replace with database or external API call in production)
const vehicles = [
    { id: 'v1', price: 50, company: 'Hertz', vehicle_type: 'sedan' },
    { id: 'v2', price: 75, company: 'Avis', vehicle_type: 'SUV' },
    { id: 'v3', price: 60, company: 'Enterprise', vehicle_type: 'sedan' },
    { id: 'v4', price: 90, company: 'Hertz', vehicle_type: 'SUV' },
];

// Function to implement retry logic
async function fetchDataWithRetry(fetchFunction, maxRetries = 3) {
    let retries = 0;
    while (retries < maxRetries) {
        try {
            return await fetchFunction();
        } catch (error) {
            retries++;
            console.error(`Attempt ${retries} failed: ${error.message}`);
            if (retries === maxRetries) {
                throw error; // Re-throw after max retries
            }
            // Add a delay between retries (e.g., 1 second)
            await new Promise(resolve => setTimeout(resolve, 1000));
        }
    }
}


router.get('/vehicles', async (req, res) => {
    const { location, pickup_date, dropoff_date, vehicle_type } = req.query;

    // Validate search criteria (basic validation)
    if (!location || !pickup_date || !dropoff_date || !vehicle_type) {
        return res.status(400).json({ error: 'Invalid search criteria' });
    }

    // Simulate API call with retry logic
    try {
        const filteredVehicles = await fetchDataWithRetry(() => {
            return new Promise((resolve) => {
                const results = vehicles.filter(vehicle =>
                    vehicle.vehicle_type === vehicle_type 
                );
                resolve(results);
            });
        });

        if (filteredVehicles.length === 0) {
            return res.status(200).json([]); // Return empty array if no vehicles found
        }

        res.status(200).json(filteredVehicles);

    } catch (error) {
        console.error("API Error:", error);
        res.status(500).json({ error: 'Internal server error' });
    }
});

module.exports = router;