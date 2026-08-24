const { validateTripRequest } = require('../../../shared/validation');
const { v4: uuidv4 } = require('uuid');

/**
 * @openapi
 * /trips/plan:
 *   post:
 *     summary: Create a new trip plan
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             properties:
 *               startDate:
 *                 type: string
 *                 format: date
 *               endDate:
 *                 type: string
 *                 format: date
 *               destinations:
 *                 type: array
 *                 items:
 *                   type: string
 *     responses:
 *       200:
 *         description: Successful operation
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 tripId:
 *                   type: string
 *       400:
 *         description: Invalid input
 */
const planTrip = (req, res) => {
  const { startDate, endDate, destinations } = req.body;

  const validationResult = validateTripRequest(startDate, endDate, destinations);

  if (!validationResult.isValid) {
    return res.status(400).json({ error: validationResult.message });
  }
  
  if (!Array.isArray(destinations)) {
      return res.status(400).json({ error: 'Destinations must be an array.' });
  }

  // Handle a very large number of destinations - could lead to performance issues.
  if (destinations.length > 100) {
      return res.status(400).json({ error: 'Too many destinations. Maximum allowed is 100.' });
  }

  const tripId = uuidv4();

  // Here you would typically interact with MOD-002 to save the trip plan.
  // For example:
  // const result = saveTripPlanToDatabase(tripId, startDate, endDate, destinations);
  // if (!result.success) {
  //   return res.status(500).json({ error: 'Failed to save trip plan.' });
  // }
  
  res.status(200).json({ tripId });
};

module.exports = { planTrip };