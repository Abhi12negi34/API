const { v4: uuidv4 } = require('uuid');

class Notification {
    constructor(userId, message) {
        if (!userId || typeof userId !== 'string' || userId.trim() === '') {
            throw new Error('Invalid userId. Must be a non-empty string.');
        }

        if (!message || typeof message !== 'string' || message.trim() === '') {
            throw new Error('Invalid message. Must be a non-empty string.');
        }

        this.id = uuidv4();
        this.userId = userId;
        this.message = message;
        this.createdAt = new Date();
        this.status = 'pending'; // pending, sent, failed
        this.attempts = 0;
    }

    markAsSent() {
        this.status = 'sent';
    }

    markAsFailed() {
        this.status = 'failed';
    }

    incrementAttempts() {
        this.attempts++;
    }
}

module.exports = Notification;