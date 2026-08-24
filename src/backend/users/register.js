const crypto = require('crypto');
const { Pool } = require('pg');
const { validateEmail } = require('./utils'); // Assuming utils.js handles email validation
const rateLimit = require('express-rate-limit');

// Replace with your actual database configuration
const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
});

const registrationRateLimit = rateLimit({
  windowMs: 60 * 60 * 1000, // 1 hour
  maxRequests: 5, // Limit to 5 registrations per hour
  message: 'Too many registration attempts. Please try again later.',
});

async function registerUser(email, password) {
  if (!validateEmail(email)) {
    return { status: 400, message: 'Invalid email format.' };
  }

  // Check for rate limiting - Apply this in your main app/router file.  Not directly here.

  try {
    const salt = crypto.randomBytes(16).toString('hex');
    const passwordHash = crypto.pbkdf2Sync(password, salt, 1000, 64, 'sha512').toString('hex');

    const query = 'INSERT INTO users (email, password_hash) VALUES ($1, $2) RETURNING id';
    const values = [email, passwordHash];

    const result = await pool.query(query, values);

    if (result.rows.length === 0) {
      // This should not happen, but handle it just in case
      return { status: 500, message: 'Failed to create user.' };
    }

    const userId = result.rows[0].id;

    return { status: 201, body: { id: userId } };

  } catch (error) {
    if (error.code === '23505') { // Unique violation (email already exists)
      return { status: 409, message: 'Email already exists.' };
    } else {
      console.error('Error registering user:', error);
      return { status: 500, message: 'Internal server error.' };
    }
  }
}

module.exports = { registerUser };