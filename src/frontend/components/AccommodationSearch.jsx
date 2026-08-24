import React, { useState, useEffect } from 'react';

const AccommodationSearch = () => {
  const [location, setLocation] = useState('');
  const [priceRange, setPriceRange] = useState('');
  const [checkinDate, setCheckinDate] = useState('');
  const [checkoutDate, setCheckoutDate] = useState('');
  const [accommodations, setAccommodations] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [cache, setCache] = useState({});

  useEffect(() => {
    // Check if results are cached
    const cacheKey = `${location}-${priceRange}-${checkinDate}-${checkoutDate}`;
    if (cache[cacheKey]) {
      setAccommodations(cache[cacheKey]);
      return;
    }

    const fetchAccommodations = async () => {
      setLoading(true);
      setError(null);

      try {
        const response = await fetch('/accommodations', {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
          params: {
            location,
            price_range: priceRange,
            checkin_date: checkinDate,
            checkout_date: checkoutDate,
          },
        });

        if (!response.ok) {
          if (response.status === 400) {
            throw new Error('Invalid search criteria');
          } else {
            throw new Error('Failed to fetch accommodations');
          }
        }

        const data = await response.json();
        setAccommodations(data);

        // Cache the results
        setCache(prevCache => ({
          ...prevCache,
          [cacheKey]: data,
        }));

      } catch (err) {
        setError(err.message);
        setAccommodations([]); // Clear any previous results on error
      } finally {
        setLoading(false);
      }
    };

    if (location && priceRange && checkinDate && checkoutDate) {
      fetchAccommodations();
    }

  }, [location, priceRange, checkinDate, checkoutDate, cache]);

  const handleSearch = (e) => {
    e.preventDefault();
    // No need to trigger search here as useEffect handles it based on state
  };

  return (
    <div>
      <h2>Accommodation Search</h2>
      <form onSubmit={handleSearch}>
        <div>
          <label htmlFor="location">Location:</label>
          <input
            type="text"
            id="location"
            value={location}
            onChange={(e) => setLocation(e.target.value)}
          />
        </div>
        <div>
          <label htmlFor="priceRange">Price Range:</label>
          <input
            type="text"
            id="priceRange"
            value={priceRange}
            onChange={(e) => setPriceRange(e.target.value)}
          />
        </div>
        <div>
          <label htmlFor="checkinDate">Check-in Date:</label>
          <input
            type="date"
            id="checkinDate"
            value={checkinDate}
            onChange={(e) => setCheckinDate(e.target.value)}
          />
        </div>
        <div>
          <label htmlFor="checkoutDate">Check-out Date:</label>
          <input
            type="date"
            id="checkoutDate"
            value={checkoutDate}
            onChange={(e) => setCheckoutDate(e.target.value)}
          />
        </div>
        <button type="submit">Search</button>
      </form>

      {loading && <p>Loading...</p>}
      {error && <p>Error: {error}</p>}

      <ul>
        {accommodations.length === 0 && !error && !loading ? (
          <p>No accommodations available for the specified dates.</p>
        ) : (
          accommodations.map((accommodation) => (
            <li key={accommodation.id}>
              {accommodation.name} - ${accommodation.price} - {accommodation.location}
            </li>
          ))
        )}
      </ul>
    </div>
  );
};

export default AccommodationSearch;