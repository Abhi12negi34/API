import React, { useState, useEffect } from 'react';
import axios from 'axios';

const TestCaseList = () => {
  const [testCases, setTestCases] = useState([]);
  const [specId, setSpecId] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    // No initial data fetching. Test case generation is triggered by the user.
  }, []);

  const handleGenerateTestCases = async () => {
    if (!specId) {
      setError('Please enter a specification ID.');
      return;
    }

    // Sanitize specId to prevent injection vulnerabilities
    const sanitizedSpecId = specId.replace(/[^a-zA-Z0-9]/g, ''); 

    setLoading(true);
    setError('');

    try {
      const response = await axios.post('/test-cases/generate', { spec_id: sanitizedSpecId });

      if (response.status === 200 && response.data && response.data.test_case_ids) {
        setTestCases(response.data.test_case_ids);
      } else {
        setError('Failed to generate test cases.');
        console.error('Unexpected response:', response); // Log the full response for debugging
      }

    } catch (err) {
      if (err.response && err.response.status === 404) {
        setError('Specification not found.');
      } else {
        setError(`Error generating test cases: ${err.message}`);
        console.error('Test case generation error:', err); // Log the full error for debugging
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h2>Test Case List</h2>
      <div>
        <label htmlFor="specId">Specification ID:</label>
        <input
          type="text"
          id="specId"
          value={specId}
          onChange={(e) => setSpecId(e.target.value)}
        />
        <button onClick={handleGenerateTestCases} disabled={loading}>
          {loading ? 'Generating...' : 'Generate Test Cases'}
        </button>
      </div>

      {error && <div className="error">{error}</div>}

      <h3>Generated Test Case IDs:</h3>
      <ul>
        {testCases.map((id) => (
          <li key={id}>{id}</li>
        ))}
      </ul>
    </div>
  );
};

export default TestCaseList;