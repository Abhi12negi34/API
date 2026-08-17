import React, { useState } from 'react';
import axios from 'axios';

const ApiImportForm = () => {
  const [specUrl, setSpecUrl] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();

    // Sanitize spec_url to prevent SSRF
    const sanitizedSpecUrl = specUrl.replace(/^https?:\/\//, ''); // Remove protocol for basic sanitation
    if (!sanitizedSpecUrl || !/^[a-z0-9.-]+$/.test(sanitizedSpecUrl)) {
      setErrorMessage('Invalid URL format.');
      return;
    }

    try {
      const response = await axios.post('/api-specs', { spec_url: sanitizedSpecUrl });

      if (response.status === 201) {
        setSuccessMessage(`API specification imported successfully with ID: ${response.data.id}`);
        setErrorMessage(''); // Clear any previous errors
        setSpecUrl(''); // Reset the input field
      } else {
        // Handle unexpected error responses
        setErrorMessage('An unexpected error occurred.');
      }

    } catch (error) {
      if (error.response && error.response.status === 400) {
        setErrorMessage('Invalid URL or specification format');
      } else {
        setErrorMessage(`Failed to import API specification: ${error.message}`);
      }
    }
  };

  return (
    <div>
      <h2>Import API Specification</h2>
      <form onSubmit={handleSubmit}>
        <label htmlFor="specUrl">
          API Specification URL:
          <input
            type="text"
            id="specUrl"
            value={specUrl}
            onChange={(e) => setSpecUrl(e.target.value)}
            placeholder="Enter OpenAPI specification URL (e.g., https://example.com/openapi.json)"
          />
        </label>
        <button type="submit">Import</button>
      </form>

      {errorMessage && <div className="error">{errorMessage}</div>}
      {successMessage && <div className="success">{successMessage}</div>}
    </div>
  );
};

export default ApiImportForm;