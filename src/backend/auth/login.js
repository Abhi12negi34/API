const jwt = require('jsonwebtoken');
const { v4: uuidv4 } = require('uuid');

// In-memory storage for failed login attempts (replace with a database in production)
const failedLoginAttempts = {};

const secretKey = process.env.JWT_SECRET || 'your-secret-key'; // Use environment variable for production
const jwtExpiry = '1h';
const maxLoginAttempts = 5;
const lockoutDuration = 10 * 60; // 10 minutes

async function login(req, res) {
    const { email, password } = req.body;

    // Input validation
    if (!email || !password) {
        return res.status(400).json({ error: 'Email and password are required' });
    }

    // Strong password policy (example - adjust as needed)
    if (password.length < 8 || !/[!@#$%^&*()_+=\-[\]{};':"\\|,.<>/?]/.test(password)) {
        return res.status(400).json({ error: 'Password must be at least 8 characters long and contain special characters.' });
    }

    // Check for rate limiting and account lockout
    const ipAddress = req.ip;
    const key = `${ipAddress}-${email}`;

    if (failedLoginAttempts[key] && failedLoginAttempts[key].attempts >= maxLoginAttempts && failedLoginAttempts[key].lockoutEnd > Date.now()) {
        return res.status(401).json({ error: 'Account locked due to too many failed login attempts.' });
    }

    // Simulate user authentication (replace with database lookup)
    const user = await authenticateUser(email, password);

    if (!user) {
        // Log failed login attempt
        console.log(`Failed login attempt for user: ${email}, IP: ${ipAddress}`);

        // Update failed login attempts
        failedLoginAttempts[key] = {
            attempts: (failedLoginAttempts[key]?.attempts || 0) + 1,
            lockoutEnd: Date.now() + lockoutDuration
        };

        return res.status(401).json({ error: 'Invalid credentials' });
    }

    // If authentication is successful:

    // Reset failed login attempts for this user/IP
    delete failedLoginAttempts[key];

    // Generate JWT
    const token = jwt.sign({ userId: user.id, email: user.email }, secretKey, { expiresIn: jwtExpiry });

    // Return JWT
    res.status(200).json({ token });
}

// Simulate user authentication (replace with database lookup)
async function authenticateUser(email, password) {
    // Replace with actual database query
    if (email === 'test@example.com' && password === 'P@sswOrd1') {
        return { id: '123', email: 'test@example.com' };
    }
    return null;
}

module.exports = { login };