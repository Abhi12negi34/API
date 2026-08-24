import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import axios from 'axios';

const Profile = () => {
  const { userId } = useParams();
  const [profile, setProfile] = useState(null);
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchProfile = async () => {
      try {
        const response = await axios.get(`/users/${userId}/profile`);
        setProfile(response.data);
        setEmail(response.data.email);
      } catch (err) {
        if (err.response && err.response.status === 404) {
          setError('User not found');
        } else {
          setError('Failed to fetch profile');
        }
      } finally {
        setLoading(false);
      }
    };

    fetchProfile();
  }, [userId]);

  const handleUpdateProfile = async () => {
    if (!email) {
      setError('Email is required');
      return;
    }

    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setError('Invalid email format');
      return;
    }

    try {
      const response = await axios.put(`/users/${userId}/profile`, { email });
      setProfile(response.data);
      setError('');
    } catch (err) {
      if (err.response && err.response.status === 400) {
        setError(err.response.data.message || 'Validation failed');
      } else if (err.response && err.response.status === 404) {
        setError('User not found');
      }
      else {
        setError('Failed to update profile');
      }
    }
  };

  if (loading) {
    return <div>Loading...</div>;
  }

  if (error) {
    return <div>Error: {error}</div>;
  }

  if (!profile) {
    return <div>Profile not found.</div>;
  }

  return (
    <div>
      <h2>Profile</h2>
      <p><strong>ID:</strong> {profile.id}</p>
      <p><strong>Email:</strong> {profile.email}</p>

      <h3>Update Email</h3>
      <input
        type="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
      />
      <button onClick={handleUpdateProfile}>Update</button>
    </div>
  );
};

export default Profile;