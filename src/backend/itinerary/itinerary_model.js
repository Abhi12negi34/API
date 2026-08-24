/**
 * Represents an itinerary.
 */
class ItineraryModel {
  /**
   * Retrieves an itinerary for a given trip ID.
   *
   * @param {string} tripId - The ID of the trip.
   * @returns {Promise<Array<Object>>} A promise that resolves to an array of itinerary items.
   * @throws {Error} If the trip is not found.
   */
  async getItinerary(tripId) {
    // Mock data for demonstration purposes
    // In a real application, this data would be fetched from a database or external API
    const mockItineraries = {
      '123': [
        { time: '9:00 AM', activity: 'Breakfast at hotel' },
        { time: '10:00 AM', activity: 'Visit the museum' },
        { time: '12:00 PM', activity: 'Lunch at restaurant' },
        { time: '2:00 PM', activity: 'Explore the city' },
        { time: '6:00 PM', activity: 'Dinner' },
      ],
      '456': [
        { time: '8:00 AM', activity: 'Morning walk' },
        { time: '9:00 AM', activity: 'Yoga session' },
        { time: '11:00 AM', activity: 'Brunch' },
        { time: '1:00 PM', activity: 'Shopping' },
        { time: '7:00 PM', activity: 'Movie night' },
      ],
    };

    if (!mockItineraries[tripId]) {
      throw new Error('Trip not found');
    }

    return mockItineraries[tripId];
  }
}

module.exports = ItineraryModel;