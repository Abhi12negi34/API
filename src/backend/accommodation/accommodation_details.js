const accommodations = require('../data/accommodations'); // Assuming accommodations data is in data/accommodations.js (MOD-003)

exports.getAccommodationDetails = (req, res) => {
  const accommodationId = parseInt(req.params.accommodationId);

  const accommodation = accommodations.find(acc => acc.id === accommodationId);

  if (!accommodation) {
    return res.status(404).json({ message: 'Accommodation not found' });
  }

  const response = {
    id: accommodation.id,
    name: accommodation.name,
    amenities: accommodation.amenities || [], // Handle accommodation with no amenities
    description: accommodation.description
  };

  res.status(200).json(response);
};