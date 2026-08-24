import React, { useState, useEffect } from 'react';

const VehicleSearch = () => {
  const [location, setLocation] = useState('');
  const [pickupDate, setPickupDate] = useState('');
  const [dropoffDate, setDropoffDate] = useState('');
  const [vehicleType, setVehicleType] = useState('');
  const [vehicles, setVehicles] = useState([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const searchVehicles = async () => {
    setLoading(true);
    setError('');

    try {
      const response = await fetch('/vehicles', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        params: {
          location,
          pickup_date: pickupDate,
          dropoff_date: dropoffDate,
          vehicle_type: vehicleType,
        },
      });

      if (!response.ok) {
        if (response.status === 400) {
          throw new Error('Invalid search criteria');
        } else {
          throw new Error(`API error: ${response.status}`);
        }
      }

      const data = await response.json();
      setVehicles(data);
    } catch (err) {
      setError(err.message);
      setVehicles([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // Implement retry logic for failed API calls
    let attempt = 0;
    const maxRetries = 3;

    const fetchData = async () => {
      try {
        await searchVehicles();
      } catch (error) {
        if (attempt < maxRetries) {
          attempt++;
          console.error(`Attempt ${attempt} failed: ${error.message}`);
          // Wait before retrying
          setTimeout(() => {
            fetchData();
          }, 2000);
        } else {
          setError(`Failed to fetch vehicles after ${maxRetries} attempts: ${error.message}`);
          setVehicles([]);
        }
      }
    };

    if (location && pickupDate && dropoffDate && vehicleType) {
      fetchData();
    }
  }, [location, pickupDate, dropoffDate, vehicleType]);

  const handleSubmit = (e) => {
    e.preventDefault();
    searchVehicles();
  };

  return (
    <div>
      <h1>Vehicle Search</h1>
      <form onSubmit={handleSubmit}>
        <div>
          <label htmlFor="location">Location:</label>
          <input
            type="text"
            id="location"
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            required
          />
        </div>
        <div>
          <label htmlFor="pickupDate">Pickup Date:</label>
          <input
            type="date"
            id="pickupDate"
            value={pickupDate}
            onChange={(e) => setPickupDate(e.target.value)}
            required
          />
        </div>
        <div>
          <label htmlFor="dropoffDate">Dropoff Date:</label>
          <input
            type="date"
            id="dropoffDate"
            value={dropoffDate}
            onChange={(e) => setDropoffDate(e.target.value)}
            required
          />
        </div>
        <div>
          <label htmlFor="vehicleType">Vehicle Type:</label>
          <select
            id="vehicleType"
            value={vehicleType}
            onChange={(e) => setVehicleType(e.target.value)}
            required
          >
            <option value="">Select a type</option>
            <option value="sedan">Sedan</option>
            <option value="suv">SUV</option>
            <option value="truck">Truck</option>
          </select>
        </div>
        <button type="submit" disabled={loading}>
          {loading ? 'Searching...' : 'Search'}
        </button>
      </form>

      {error && <p style={{ color: 'red' }}>Error: {error}</p>}

      <h2>Available Vehicles:</h2>
      {vehicles.length === 0 && !error && <p>No vehicles available for the specified criteria.</p>}
      <ul>
        {vehicles.map((vehicle) => (
          <li key={vehicle.id}>
            {vehicle.company} - {vehicle.vehicle_type} - ${vehicle.price}
          </li>
        ))}
      </ul>
    </div>
  );
};

export default VehicleSearch;