import React, { useState, useEffect } from 'react';

function AccommodationDetails({ accommodationId }) {
  const [accommodation, setAccommodation] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchAccommodationDetails = async () => {
      try {
        const response = await fetch(`/accommodations/${accommodationId}`);

        if (!response.ok) {
          if (response.status === 404) {
            setError("Accommodation not found");
          } else {
            throw new Error(`HTTP error! Status: ${response.status}`);
          }
          return;
        }

        const data = await response.json();
        setAccommodation(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchAccommodationDetails();
  }, [accommodationId]);

  if (loading) {
    return <p>Loading...</p>;
  }

  if (error) {
    return <p>Error: {error}</p>;
  }

  if (!accommodation) {
    return <p>No accommodation found.</p>;
  }

  return (
    <div>
      <h2>{accommodation.name}</h2>
      <p>{accommodation.description}</p>
      <h3>Amenities:</h3>
      <ul>
        {accommodation.amenities && accommodation.amenities.length > 0 ? (
          accommodation.amenities.map((amenity) => (
            <li key={amenity}>{amenity}</li>
          ))
        ) : (
          <li>No amenities available.</li>
        )}
      </ul>
    </div>
  );
}

export default AccommodationDetails;