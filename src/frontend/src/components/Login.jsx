import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

const Login = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();

    // Basic validation
    if (!email || !password) {
      setError('Please fill in all fields.');
      return;
    }

    if (password.length < 8) {
      setError('Password must be at least 8 characters long.');
      return;
    }

    try {
      setLoading(true);
      const response = await axios.post('/auth/login', { email, password });

      if (response.status === 200) {
        const { token } = response.data;
        localStorage.setItem('token', token); // Store token in local storage
        navigate('/dashboard'); // Redirect to dashboard
        setError('');
      }
    } catch (err) {
      if (err.response && err.response.status === 401) {
        setError('Invalid credentials.');
        // Log failed login attempt
        console.error('Failed login attempt:', err.response.data, 'IP:', process.env.REACT_APP_CLIENT_IP);
      } else if (err.response && err.response.status === 400) {
        setError('Validation failed.');
      } else {
        setError('An error occurred. Please try again.');
        console.error('Login error:', err);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // Check if already logged in
    const token = localStorage.getItem('token');
    if (token) {
      navigate('/dashboard');
    }
  }, [navigate]);

  return (
    <div className="login-container">
      <h2>Login</h2>
      <form onSubmit={handleSubmit}>
        <div>
          <label htmlFor="email">Email:</label>
          <input
            type="email"
            id="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </div>
        <div>
          <label htmlFor="password">Password:</label>
          <input
            type="password"
            id="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>
        <button type="submit" disabled={loading}>
          {loading ? 'Logging in...' : 'Login'}
        </button>
        {error && <p className="error">{error}</p>}
      </form>
    </div>
  );
};

export default Login;