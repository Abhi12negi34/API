import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

function Register() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();

    // Basic email validation
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setErrorMessage('Invalid email format.');
      return;
    }

    try {
      const response = await axios.post('/users/register', { email, password });

      if (response.status === 201) {
        // Registration successful, redirect to login or home page
        navigate('/login'); // Or your desired redirect path
      }
    } catch (error) {
      if (error.response && error.response.status === 409) {
        setErrorMessage('Email already exists.');
      } else if (error.response && error.response.status === 400) {
        setErrorMessage('Validation failed.'); // Or parse specific validation errors from the response if available
      } else {
        setErrorMessage('Registration failed. Please try again.');
        console.error(error); // Log the error for debugging
      }
    }
  };

  return (
    <div>
      <h2>Register</h2>
      <form onSubmit={handleSubmit}>
        <div>
          <label htmlFor="email">Email:</label>
          <input
            type="email"
            id="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </div>
        <div>
          <label htmlFor="password">Password:</label>
          <input
            type="password"
            id="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </div>
        <button type="submit">Register</button>
      </form>
      {errorMessage && <p style={{ color: 'red' }}>{errorMessage}</p>}
    </div>
  );
}

export default Register;