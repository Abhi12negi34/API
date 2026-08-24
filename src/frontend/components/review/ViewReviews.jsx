import React, { useState, useEffect } from 'react';
import axios from 'axios';

const ViewReviews = ({ entityId, entityType }) => {
    const [reviews, setReviews] = useState([]);
    const [page, setPage] = useState(1);
    const [limit, setLimit] = useState(10);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchReviews = async () => {
            setLoading(true);
            try {
                const response = await axios.get(`/reviews/${entityId}/${entityType}`, {
                    params: {
                        page: page,
                        limit: limit
                    }
                });

                if (response.status === 200) {
                    setReviews(response.data);
                } else {
                    setError('Failed to fetch reviews.');
                }
            } catch (err) {
                if (err.response && err.response.status === 404) {
                    setError('Entity not found.');
                } else {
                    setError('An error occurred while fetching reviews.');
                }
            } finally {
                setLoading(false);
            }
        };

        fetchReviews();
    }, [entityId, entityType, page, limit]);

    if (loading) {
        return <div>Loading reviews...</div>;
    }

    if (error) {
        return <div>Error: {error}</div>;
    }

    if (reviews.length === 0) {
        return <div>No reviews found for this entity.</div>;
    }

    return (
        <div>
            <h2>Reviews for {entityType} ID: {entityId}</h2>
            <ul>
                {reviews.map(review => (
                    <li key={review.review_id}>
                        <strong>Rating:</strong> {review.rating}<br/>
                        <strong>Comment:</strong> {review.comment}
                    </li>
                ))}
            </ul>
            <div>
                <button onClick={() => setPage(page - 1)} disabled={page === 1}>
                    Previous Page
                </button>
                <span>Page {page}</span>
                <button onClick={() => setPage(page + 1)} disabled={reviews.length < limit}>
                    Next Page
                </button>
            </div>
        </div>
    );
};

export default ViewReviews;