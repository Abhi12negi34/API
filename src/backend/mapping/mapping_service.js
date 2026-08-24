const mappingService = {};

// Mock mapping service integration - replace with actual service call
const generateMapUrl = (latitude, longitude) => {
  // In a real implementation, this would call the mapping service API
  // and return a URL to display the location on a map.
  return `https://www.google.com/maps?q=${latitude},${longitude}`;
};

mappingService.getLocationMapUrl = (latitude, longitude) => {
  // Input validation to prevent injection attacks
  if (typeof latitude !== 'number' || typeof longitude !== 'number') {
    return {
      status: 400,
      error: 'invalid coordinates'
    };
  }

  if (isNaN(latitude) || isNaN(longitude)) {
      return {
          status: 400,
          error: 'invalid coordinates'
      }
  }

  if (latitude < -90 || latitude > 90 || longitude < -180 || longitude > 180) {
      return {
          status: 400,
          error: 'invalid coordinates'
      }
  }

  try {
    const mapUrl = generateMapUrl(latitude, longitude);
    return {
      status: 200,
      body: {
        map_url: mapUrl
      }
    };
  } catch (error) {
    console.error('Error generating map URL:', error);
    return {
      status: 500,
      error: 'Failed to generate map URL'
    };
  }
};

module.exports = mappingService;