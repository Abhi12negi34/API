import React, { useState, useEffect } from 'react';
import axios from 'axios';

const TestRunDetails = ({ resultId }) => {
    const [results, setResults] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchTestResults = async () => {
            try {
                const response = await axios.get(`/tests/results/${resultId}`);
                setResults(response.data.results);
                setLoading(false);
            } catch (err) {
                console.error("Error fetching test results:", err);
                setError(err.message || "Failed to fetch test results");
                setLoading(false);
            }
        };

        if (resultId) {
            fetchTestResults();
        } else {
            setLoading(false);
        }
    }, [resultId]);

    if (loading) {
        return <p>Loading test results...</p>;
    }

    if (error) {
        return <p>Error: {error}</p>;
    }

    return (
        <div>
            <h2>Test Run Details - Result ID: {resultId}</h2>
            <table>
                <thead>
                    <tr>
                        <th>Test Case ID</th>
                        <th>Status</th>
                        <th>Response</th>
                    </tr>
                </thead>
                <tbody>
                    {results.map(result => (
                        <tr key={result.id}>
                            <td>{result.test_case_id}</td>
                            <td>{result.status}</td>
                            <td>{JSON.stringify(result.response)}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
};

export default TestRunDetails;