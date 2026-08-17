import React, { useState, useEffect } from 'react';

const PerformanceConfig = () => {
  const [thresholds, setThresholds] = useState([]);
  const [metrics, setMetrics] = useState({});
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // Load existing thresholds from local storage or API (if available)
    const storedThresholds = localStorage.getItem('performance_thresholds');
    if (storedThresholds) {
      setThresholds(JSON.parse(storedThresholds));
    }
  }, []);

  const handleInputChange = (e, index) => {
    const { name, value } = e.target;
    const updatedThresholds = [...thresholds];
    updatedThresholds[index][name] = value;
    setThresholds(updatedThresholds);
    localStorage.setItem('performance_thresholds', JSON.stringify(updatedThresholds)); //Persist locally
  };

  const handleAddThreshold = () => {
    setThresholds([...thresholds, { endpoint: '', p95_latency_ms: '' }]);
  };

  const handleDeleteThreshold = (index) => {
    const updatedThresholds = [...thresholds];
    updatedThresholds.splice(index, 1);
    setThresholds(updatedThresholds);
    localStorage.setItem('performance_thresholds', JSON.stringify(updatedThresholds)); //Persist locally
  };

  const fetchMetrics = async (endpoint) => {
    if (!endpoint) return;

    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`/api-monitoring/metrics?endpoint=${endpoint}`);
      if (!response.ok) {
        throw new Error(`Failed to fetch metrics for ${endpoint}: ${response.status}`);
      }

      const data = await response.json();
      setMetrics({ ...metrics, [endpoint]: data.p95_latency });
    } catch (err) {
      console.error('Error fetching metrics:', err);
      setError(`Failed to fetch metrics for ${endpoint}: ${err.message}`);

    } finally {
      setLoading(false);
    }
  };

  const handleCheckMetrics = async () => {
    for (const threshold of thresholds) {
      await fetchMetrics(threshold.endpoint);
    }
  };
  

  return (
    <div>
      <h2>Performance Threshold Configuration</h2>
      <button onClick={handleAddThreshold}>Add Endpoint</button>
      {thresholds.map((threshold, index) => (
        <div key={index} style={{ border: '1px solid #ccc', padding: '10px', marginBottom: '10px' }}>
          <label>
            Endpoint:
            <input
              type="text"
              name="endpoint"
              value={threshold.endpoint}
              onChange={(e) => handleInputChange(e, index)}
            />
          </label>
          <br />
          <label>
            P95 Latency (ms):
            <input
              type="number"
              name="p95_latency_ms"
              value={threshold.p95_latency_ms}
              onChange={(e) => handleInputChange(e, index)}
            />
          </label>
          <br />
          <button onClick={() => handleDeleteThreshold(index)}>Delete</button>
        </div>
      ))}

      <button onClick={handleCheckMetrics}>Check Metrics</button>

      {loading && <p>Loading metrics...</p>}
      {error && <p style={{ color: 'red' }}>{error}</p>}

      <ul>
        {Object.entries(metrics).map(([endpoint, p95_latency]) => (
          <li key={endpoint}>
            {endpoint}: {p95_latency} ms
          </li>
        ))}
      </ul>
    </div>
  );
};

export default PerformanceConfig;