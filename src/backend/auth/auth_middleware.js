const jwt = require('jsonwebtoken');
const { log } = require('../logger'); // Assuming a logger module exists

const secret = process.env.JWT_SECRET || 'your_secret_key'; // Use environment variable
const failedLoginAttempts = {};

function authenticateToken(req, res, next) {
  const authHeader = req.headers.authorization;

  if (!authHeader) {
    return res.status(401).json({ message: 'No token provided' });
  }

  const token = authHeader.split(' ')[1]; // Assuming "Bearer <token>" format

  jwt.verify(token, secret, (err, user) => {
    if (err) {
      log('JWT Verification Failed:', err.message, req.ip); // Log verification failures
      return res.status(401).json({ message: 'Invalid token' });
    }

    req.user = user;
    next();
  });
}

function rateLimitLogin(req, res, next) {
  const ipAddress = req.ip;
  const maxAttempts = 5;
  const lockoutDuration = 60 * 60; // 1 hour

  if (!failedLoginAttempts[ipAddress]) {
    failedLoginAttempts[ipAddress] = [];
  }

  if (failedLoginAttempts[ipAddress].length >= maxAttempts) {
    const lockoutTime = Math.floor(Date.now() / 1000) + lockoutDuration;
    log('Account locked out:', ipAddress, 'until:', new Date(lockoutTime * 1000));
    return res.status(429).json({ message: 'Too many login attempts. Account locked for 1 hour.' });
  }

  next();
}

function trackFailedLogin(email) {
    return (req, res, next) => {
      if (res.statusCode === 401) {
        log('Failed login attempt:', email, 'from IP:', req.ip);
        const ipAddress = req.ip;
        if (!failedLoginAttempts[ipAddress]) {
          failedLoginAttempts[ipAddress] = [];
        }
        failedLoginAttempts[ipAddress].push({email: email, timestamp: Date.now()});
      }
      next();
    }
}



module.exports = {
  authenticateToken,
  rateLimitLogin,
  trackFailedLogin
};