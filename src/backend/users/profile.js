const express = require('express');
const router = express.Router();
const { authenticateToken } = require('../middleware/auth'); // Assuming authentication middleware is in middleware folder
const { validateEmail } = require('../utils/validation'); // Assuming validation utility is in utils folder

// Mock user data (replace with database interaction in a real application)
const users = [
  { id: '1', email: 'user1@example.com' },
  { id: '2', email: 'user2@example.com' },
];

// GET /users/{userId}/profile
router.get('/users/:userId/profile', authenticateToken, (req, res) => {
  const userId = req.params.userId;
  const user = users.find(u => u.id === userId);

  if (!user) {
    return res.status(404).json({ message: 'user not found' });
  }

  res.status(200).json({ id: user.id, email: user.email });
});

// PUT /users/{userId}/profile
router.put('/users/:userId/profile', authenticateToken, (req, res) => {
  const userId = req.params.userId;
  const { email } = req.body;

  if (!email) {
    return res.status(400).json({ message: 'Email is required' });
  }

  if (!validateEmail(email)) {
    return res.status(400).json({ message: 'Invalid email format' });
  }

  const userIndex = users.findIndex(u => u.id === userId);

  if (userIndex === -1) {
    return res.status(404).json({ message: 'user not found' });
  }

  users[userIndex] = { ...users[userIndex], email };

  res.status(200).json({ id: users[userIndex].id, email: users[userIndex].email });
});

module.exports = router;