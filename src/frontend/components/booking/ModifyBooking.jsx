import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useParams } from 'react-router-dom';

const ModifyBooking = () => {
    const { bookingId } = useParams();
    const [date, setDate] = useState('');
    const [time, setTime] = useState('');
    const [services, setServices] = useState([]);
    const [message, setMessage] = useState('');
    const [error, setError] = useState('');

    useEffect(() => {
        // Fetch booking details on component mount
        const fetchBooking = async () => {
            try {
                // In a real application, you would fetch the booking details
                // from your backend API based on the bookingId.
                // For this example, we'll just set some default values.
                setDate('2024-03-15');
                setTime('10:00');
                setServices(['Haircut', 'Massage']);
            } catch (err) {
                setError('Failed to fetch booking details.');
                console.error(err);
            }
        };

        fetchBooking();
    }, [bookingId]);

    const handleSubmit = async (e) => {
        e.preventDefault();

        try {
            const response = await axios.put(`/bookings/${bookingId}`, {
                date,
                time,
                services,
            });

            if (response.status === 200 && response.data.status === 'updated') {
                setMessage('Booking updated successfully!');
                // Reset form or redirect as needed
            } else {
                setError('Failed to update booking.');
            }
        } catch (err) {
            if (err.response && err.response.status === 404) {
                setError('Booking not found.');
            } else if (err.response && err.response.status === 400) {
                setError('Invalid request.');
            } else {
                setError('An unexpected error occurred.');
                console.error(err);
            }
        }
    };

    return (
        <div>
            <h2>Modify Booking</h2>
            {message && <p style={{ color: 'green' }}>{message}</p>}
            {error && <p style={{ color: 'red' }}>{error}</p>}

            <form onSubmit={handleSubmit}>
                <div>
                    <label htmlFor="date">Date:</label>
                    <input
                        type="date"
                        id="date"
                        value={date}
                        onChange={(e) => setDate(e.target.value)}
                    />
                </div>
                <div>
                    <label htmlFor="time">Time:</label>
                    <input
                        type="time"
                        id="time"
                        value={time}
                        onChange={(e) => setTime(e.target.value)}
                    />
                </div>
                <div>
                    <label htmlFor="services">Services:</label>
                    <select
                        multiple
                        id="services"
                        value={services}
                        onChange={(e) => {
                            const selectedOptions = Array.from(e.target.selectedOptions).map(
                                (option) => option.value
                            );
                            setServices(selectedOptions);
                        }}
                    >
                        <option value="Haircut">Haircut</option>
                        <option value="Massage">Massage</option>
                        <option value="Facial">Facial</option>
                        <option value="Manicure">Manicure</option>
                    </select>
                </div>
                <button type="submit">Update Booking</button>
            </form>
        </div>
    );
};

export default ModifyBooking;