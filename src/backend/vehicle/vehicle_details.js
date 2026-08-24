const { getVehicleById } = require('../../../shared/data_access'); // Assuming MOD-005 provides data access

exports.getVehicleDetails = async (req, res) => {
  const vehicleId = parseInt(req.params.vehicleId);

  if (isNaN(vehicleId)) {
    return res.status(400).json({ error: 'Invalid vehicle ID' });
  }

  try {
    const vehicle = await getVehicleById(vehicleId);

    if (!vehicle) {
      return res.status(404).json({ error: 'Vehicle not found' });
    }

    // Construct the response object
    const vehicleDetails = {
      id: vehicle.id,
      model: vehicle.model,
      features: vehicle.features,
      rental_rate: vehicle.rental_rate,
    };

    res.status(200).json(vehicleDetails);

  } catch (error) {
    console.error('Error fetching vehicle details:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
};