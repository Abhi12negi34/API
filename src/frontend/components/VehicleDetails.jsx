import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import axios from 'axios';

function VehicleDetails() {
  const { vehicleId } = useParams();
  const [vehicle, setVehicle] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchVehicleDetails = async () => {
      try {
        const response = await axios.get(`/vehicles/${vehicleId}`);
        setVehicle(response.data);
        setError(null);
      } catch (err) {
        if (err.response && err.response.status === 404) {
          setError("Vehicle not found");
        } else {
          setError("Failed to fetch vehicle details");
        }
        setVehicle(null);
      } finally {
        setLoading(false);
      }
    };

    fetchVehicleDetails();
  }, [vehicleId]);

  if (loading) {
    return <div>Loading...</div>;
  }

  if (error) {
    return <div>Error: {error}</div>;
  }

  if (!vehicle) {
    return <div>No vehicle details available.</div>;
  }

  return (
    <div>
      <h2>Vehicle Details</h2>
      <p><strong>ID:</strong> {vehicle.id}</p>
      <p><strong>Model:</strong> {vehicle.model}</p>
      <p><strong>Features:</strong></p>
      <ul>
        {vehicle.features.map((feature, index) => (
          <li key={index}>{feature}</li>
        ))}
      </ul>
      <p><strong>Rental Rate:</strong> ${vehicle.rental_rate}</p>
    </div>
  );
}

export default VehicleDetails;