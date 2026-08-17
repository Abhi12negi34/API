import React, { useState, useEffect } from 'react';
import './Dashboard.css'; // You might need to create this CSS file for styling

const Dashboard = () => {
  const [metrics, setMetrics] = useState({
    totalTests: 0,
    passedTests: 0,
    failedTests: 0,
    errorRate: 0,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    // Simulate fetching data from an API endpoint (replace with actual API call)
    const fetchData = async () => {
      try {
        // Assuming MOD-011 provides a function to fetch reports. Replace 'getReports' and path if needed.
        const reportData = await import('../../../MOD-011/src/frontend/api/reportApi').then(module => module.getReports());

        if (!reportData) {
          throw new Error('No data received from the API.');
        }

        // Process the report data to calculate metrics
        const totalTests = reportData.length;
        const passedTests = reportData.filter(report => report.status === 'passed').length;
        const failedTests = reportData.filter(report => report.status === 'failed').length;

        let errorRate = 0;
        if (totalTests > 0) {
          errorRate = (failedTests / totalTests) * 100;
        }

        setMetrics({
          totalTests,
          passedTests,
          failedTests,
          errorRate,
        });
      } catch (err) {
        setError(`Failed to fetch reports: ${err.message}`);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []); // Empty dependency array ensures this effect runs only once after the initial render

  if (loading) {
    return <div>Loading dashboard...</div>;
  }

  if (error) {
    return <div>Error: {error}</div>;
  }


  return (
    <div className="dashboard-container">
      <h1>Dashboard</h1>
      <div className="metric-card">
        <h2>Total Tests</h2>
        <p>{metrics.totalTests}</p>
      </div>
      <div className="metric-card">
        <h2>Passed Tests</h2>
        <p>{metrics.passedTests}</p>
      </div>
      <div className="metric-card">
        <h2>Failed Tests</h2>
        <p>{metrics.failedTests}</p>
      </div>
      <div className="metric-card">
        <h2>Error Rate</h2>
        <p>{metrics.errorRate.toFixed(2)}%</p>
      </div>

       {/* Add more complex visualizations or charts here if needed */}
    </div>
  );
};

export default Dashboard;