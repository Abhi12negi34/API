/**
 * @module Trip Planning
 */

const uuid = require('uuid');

/**
 * Represents a trip plan.
 * @class TripPlan
 */
class TripPlan {
    /**
     * Creates a new trip plan.
     * @param {string} startDate - The start date of the trip.
     * @param {string} endDate - The end date of the trip.
     * @param {string[]} destinations - An array of destination strings.
     */
    constructor(startDate, endDate, destinations) {
        this.tripId = uuid.v4();
        this.startDate = startDate;
        this.endDate = endDate;
        this.destinations = destinations;
        this.validateInput();
    }

    /**
     * Validates the input data.
     * @throws {Error} If the input is invalid.
     */
    validateInput() {
        if (!this.startDate || !this.endDate || !this.destinations || this.destinations.length === 0) {
            throw new Error('Invalid input: Start date, end date, and destinations are required.');
        }

        // Add more validation as needed, e.g., date format validation
        if (this.startDate > this.endDate) {
            throw new Error('Invalid input: Start date must be before end date.');
        }

        if (this.destinations.length > 100) {
          throw new Error('Invalid input: Too many destinations. Maximum 100 allowed.');
        }
    }

    /**
     * Returns the trip plan as an object.
     * @returns {object} The trip plan object.
     */
    toObject() {
        return {
            tripId: this.tripId,
            startDate: this.startDate,
            endDate: this.endDate,
            destinations: this.destinations
        };
    }
}

module.exports = TripPlan;