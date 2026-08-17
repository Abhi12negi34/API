import React, { useState } from 'react';
import axios from 'axios';

const ChaosControlPanel = () => {
  const [endpoint, setEndpoint] = useState('');
  const [duration, setDuration] = useState(5);
  const [faultType, setFaultType] = useState('latency');
  const [statusMessage, setStatusMessage] = useState('');
  const [loading, setLoading] = useState(false);

  const handleInjectFault = async () => {
    if (!endpoint) {
      setStatusMessage('Please enter a valid endpoint.');
      return;
    }

    if (duration <= 0) {
      setStatusMessage("Duration must be greater than 0.");
      return;
    }

    setLoading(true);
    try {
      const response = await axios.post('/fault-injection/inject', {
        endpoint,
        duration,
        fault_type: faultType,
      });

      if (response.status === 200) {
        setStatusMessage('Fault injected successfully.');
      } else {
        setStatusMessage(`Error injecting fault: ${response.data.message}`);
      }
    } catch (error) {
      if (error.response && error.response.status === 400) {
        setStatusMessage(error.response.data.message);
      } else {
        setStatusMessage(`An unexpected error occurred: ${error.message}`);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h2>Chaos Control Panel</h2>
      <div>
        <label>
          Endpoint:
          <input type="text" value={endpoint} onChange={(e) => setEndpoint(e.target.value)} />
        </label>
      </div>
      <div>
        <label>
          Duration (seconds):
          <input type="number" value={duration} onChange={(e) => setDuration(parseInt(e.target.value))} />
        </label>
      </div>
      <div>
        <label>
          Fault Type:
          <select value={faultType} onChange={(e) => setFaultType(e.target.value)}>
            <option value="latency">Latency</option>
            <option value="error">Error</option>
            <option value="blackhole">Blackhole</option>
          </select>
        </label>
      </div>
      <button onClick={handleInjectFault} disabled={loading}>
        {loading ? 'Injecting...' : 'Inject Fault'}
      </button>
      <div>{statusMessage}</div>
    </div>
  );
};

export default ChaosControlPanel;