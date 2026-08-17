import { get } from 'axios';

const BASE_URL = process.env.REACT_APP_API_BASE_URL || '/api'; // Use environment variable or default

// Function to fetch report data
export const fetchReportData = async (reportId) => {
  try {
    const response = await get(`${BASE_URL}/reports/${reportId}`);
    return response.data;
  } catch (error) {
    // Handle API errors gracefully
    if (error.response) {
      // The request was made and the server responded with an error status
      console.error('API Error:', error.response.data);
      throw new Error(`Report fetch failed: ${error.response.data?.message || 'Unknown error'}`); // Include message from response if available
    } else if (error.request) {
      // The request was made but no response was received
      console.error('Network Error:', error.request);
      throw new Error('Report fetch failed: Network error');
    } else {
      // Something happened in setting up the request that triggered an error
      console.error('Error fetching report:', error);
      throw new Error('Report fetch failed: Unknown error');
    }
  }
};

// Function to get summary metrics (for dashboard) - handles large datasets by limiting results
export const getSummaryMetrics = async () => {
    try {
        const response = await get(`${BASE_URL}/reports/summary`);
        return response.data;
    } catch (error) {
        if (error.response) {
            console.error('API Error:', error.response.data);
            throw new Error(`Summary metrics fetch failed: ${error.response.data?.message || 'Unknown error'}`);
        } else if (error.request) {
            console.error('Network Error:', error.request);
            throw new Error('Summary metrics fetch failed: Network error');
        } else {
            console.error('Error fetching summary metrics:', error);
            throw new Error('Summary metrics fetch failed: Unknown error');
        }
    }
};

//Example function for related module interaction (MOD-011). Placeholder only, assuming MOD-011 provides something similar. Adapt as necessary.
export const getMod011Data = async () => {
  try{
    const response = await get(`${BASE_URL}/mod011/data`); //adjust URL for mod 011 api path
    return response.data;
  } catch (error){
      console.error("Error getting data from Mod-011:", error);
      throw new Error('Failed to retrieve MOD-011 data');
  }
}