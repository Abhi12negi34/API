import React, { useState } from 'react';
import axios from 'axios';

const SubmitReview = ({ entityId, entityType }) => {
  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();

    // Basic input validation
    if (rating === 0 || !comment || !entityId || !entityType) {
      setError('Please fill out all fields and provide a valid rating.');
      return;
    }

    try {
      const response = await axios.post('/reviews', {
        rating,
        comment,
        entity_id: entityId,
        entity_type: entityType,
      });

      if (response.status === 201) {
        setSuccess(true);
        // Optionally clear the form after successful submission
        setRating(0);
        setComment('');
        setError('');
      }
    } catch (err) {
      if (err.response && err.response.status === 400) {
        setError('Invalid input. Please check your review details.');
      } else {
        setError('An error occurred while submitting the review.');
        console.error(err);
      }
    }
  };

  return (
    <div>
      <h2>Submit Your Review</h2>
      {success && <p style={{ color: 'green' }}>Review submitted successfully!</p>}
      {error && <p style={{ color: 'red' }}>{error}</p>}
      <form onSubmit={handleSubmit}>
        <div>
          <label htmlFor="rating">Rating (1-5):</label>
          <select
            id="rating"
            value={rating}
            onChange={(e) => setRating(parseInt(e.target.value))}
          >
            <option value={0}>Select Rating</option>
            <option value={1}>1</option>
            <option value={2}>2</option>
            <option value={3}>3</option>
            <option value={4}>4</option>
            <option value={5}>5</option>
          </select>
        </div>
        <div>
          <label htmlFor="comment">Comment:</label>
          <textarea
            id="comment"
            value={comment}
            onChange={(e) => setComment(e.target.value)}
          />
        </div>
        <button type="submit">Submit Review</button>
      </form>
    </div>
  );
};

export default SubmitReview;