// api/routes/records.js
const express = require('express');
const { 
  findUserByApiKey, 
  getNextRecordForUser, 
  updateRecordStatus,
  updateUserBalance,
  records,
  createRecord,
  findUserById,
  findUserByUsername
} = require('../data');

const router = express.Router();

// Helper to extract user from Bearer token
function getUserFromAuth(authHeader) {
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    throw new Error('Missing or invalid Authorization header');
  }
  const apiKey = authHeader.slice(7);
  const user = findUserByApiKey(apiKey);
  if (!user) throw new Error('Invalid API key');
  return user;
}

// GET /api/extension/records/next
router.get('/next', async (req, res) => {
  try {
    const user = getUserFromAuth(req.headers.authorization);
    const { requested_amount } = req.query;
    const requestedAmount = requested_amount ? Number(requested_amount) : undefined;

    const record = getNextRecordForUser(user.id, requestedAmount);
    if (!record) {
      return res.status(404).json({ error: 'No available records' });
    }

    res.json({
      id: record.id,
      identifier: record.identifier,
      field_a: record.field_a,
      field_b: record.field_b,
      field_c: record.field_c,
      school: record.school || '',
      requested_amount: record.requested_amount,
      balance: user.balance.toFixed(2),
      payment_result_wait_seconds: 5
    });
  } catch (err) {
    const status = err.message.includes('Authorization') ? 401 : 500;
    res.status(status).json({ error: err.message || 'Failed to fetch record' });
  }
});

// PUT /api/extension/records/:id/status
router.put('/:id/status', async (req, res) => {
  try {
    const user = getUserFromAuth(req.headers.authorization);
    const recordId = Number(req.params.id);
    const { status, transaction_id, message, requested_amount, amount_paid, school } = req.body;

    if (!['success', 'failed'].includes(status)) {
      return res.status(400).json({ error: 'Status must be "success" or "failed"' });
    }

    const updated = updateRecordStatus(recordId, user.id, {
      status,
      transaction_id,
      message,
      requested_amount,
      amount_paid,
      school
    });
    if (!updated) {
      return res.status(404).json({ error: 'Record not found or not owned by user' });
    }

    // If success, deduct amount_paid from balance
    if (status === 'success') {
      const paid = Number(amount_paid) || 0;
      if (paid > 0) {
        const newUser = updateUserBalance(user.id, -paid);
        if (newUser) user.balance = newUser.balance;
      }
    }

    res.json({
      balance: user.balance.toFixed(2),
      record_status: updated.status,
      message: updated.message
    });
  } catch (err) {
    const status = err.message.includes('Authorization') ? 401 : 500;
    res.status(status).json({ error: err.message || 'Failed to update record' });
  }
});

// ---------- Admin routes (for testing) ----------
// POST /api/extension/admin/records – add a record for a user
router.post('/admin/records', async (req, res) => {
  try {
    const { userId, identifier, field_a, field_b, field_c, school, requested_amount } = req.body;
    if (!userId || !identifier || !field_a || !field_b || !field_c) {
      return res.status(400).json({ error: 'Missing required fields' });
    }
    const user = findUserById(userId);
    if (!user) {
      return res.status(404).json({ error: 'User not found' });
    }
    const record = createRecord(userId, identifier, field_a, field_b, field_c, school, requested_amount);
    res.status(201).json(record);
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Failed to create record' });
  }
});

// POST /api/extension/admin/topup – add balance to user
router.post('/admin/topup', async (req, res) => {
  try {
    const { username, amount } = req.body;
    if (!username || amount === undefined) {
      return res.status(400).json({ error: 'Username and amount required' });
    }
    const user = findUserByUsername(username);
    if (!user) {
      return res.status(404).json({ error: 'User not found' });
    }
    const updated = updateUserBalance(user.id, Number(amount));
    res.json({ username: user.username, new_balance: updated.balance.toFixed(2) });
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Top-up failed' });
  }
});

module.exports = router;
