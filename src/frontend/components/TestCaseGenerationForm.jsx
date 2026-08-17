import React, { useState } from 'react';
import axios from 'axios';

const TestCaseGenerationForm = () => {
  const [apiSpecId, setApiSpecId] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [testCaseIds, setTestCaseIds] = useState([]);

  const handleSubmit = async (event) => {
    event.preventDefault();

    // Sanitize input to prevent injection vulnerabilities
    const sanitizedApiSpecId = apiSpecId.replace(/[^a-zA-Z0-9_.-]/g, ''); 

    setLoading(true);
    setError('');
    setTestCaseIds([]);

    try {
      const response = await axios.post('/test-cases/generate', {
        api_spec_id: sanitizedApiSpecId,
      });

      if (response.status === 201) {
        setTestCaseIds(response.data.test_case_ids);
      } else {
        throw new Error(`Unexpected response status: ${response.status}`);
      }
    } catch (err) {
      if (err.response && err.response.status === 400) {
        setError('Invalid API Specification ID.');
      } else if (err.message.includes("Failed to connect")) {
          setError("Could not connect to the server. Please check your connection and try again.");
      }else {
        setError(`Test case generation failed: ${err.message}`);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h2>Generate API Test Cases</h2>
      <form onSubmit={handleSubmit}>
        <div>
          <label htmlFor="apiSpecId">API Specification ID:</label>
          <input
            type="text"
            id="apiSpecId"
            value={apiSpecId}
            onChange={(e) => setApiSpecId(e.target.value)}
            required
          />
        </div>
        <button type="submit" disabled={loading}>
          {loading ? 'Generating...' : 'Generate Test Cases'}
        </button>
      </form>

      {error && <p style={{ color: 'red' }}>Error: {error}</p>}

      {testCaseIds.length > 0 && (
        <div>
          <h3>Generated Test Case IDs:</h3>
          <ul>
            {testCaseIds.map((id) => (
              <li key={id}>{id}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

export default TestCaseGenerationForm;