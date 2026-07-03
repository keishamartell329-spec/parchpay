// api/routes/auth.js
const express = require('express');
const bcrypt = require('bcryptjs');
const crypto = require('crypto');
const { findUserByUsername, createUser, findUserByApiKey } = require('../data');

const router = express.Router();

function generateApiKey() {
  return crypto.randomBytes(32).toString('hex');
}

// POST /api/extension/auth/register
router.post('/register', async (req, res) => {
  try {
    const { username, password } = req.body;
    if (!username || !password) {
      return res.status(400).json({ error: 'Username and password required' });
    }
    if (password.length < 6) {
      return res.status(400).json({ error: 'Password must be at least 6 characters' });
    }
    if (findUserByUsername(username)) {
      return res.status(409).json({ error: 'Username already exists' });
    }

    const hashed = await bcrypt.hash(password, 10);
    const apiKey = generateApiKey();
    const user = createUser(username, hashed, apiKey, 0); // start with zero balance

    // Optionally, you could set isActive flag; we assume active
    res.status(201).json({
      username: user.username,
      api_key: user.apiKey,
      user_id: user.id,
      balance: user.balance.toFixed(2),
      is_active: true,
      message: 'Account created and active'
    });
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Registration failed' });
  }
});

// POST /api/extension/auth/login
router.post('/login', async (req, res) => {
  try {
    const { username, password } = req.body;
    if (!username || !password) {
      return res.status(400).json({ error: 'Username and password required' });
    }
    const user = findUserByUsername(username);
    if (!user) {
      return res.status(401).json({ error: 'Invalid credentials' });
    }
    const valid = await bcrypt.compare(password, user.passwordHash);
    if (!valid) {
      return res.status(401).json({ error: 'Invalid credentials' });
    }

    res.json({
      username: user.username,
      api_key: user.apiKey,
      user_id: user.id,
      balance: user.balance.toFixed(2)
    });
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Login failed' });
  }
});

module.exports = router;
