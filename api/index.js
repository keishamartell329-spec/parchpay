const express = require('express');
const bcrypt = require('bcryptjs');
const crypto = require('crypto');

const app = express();
app.use(express.json());

// ------------------------------------------------------------
// 1. In‑memory data store (replace with a real DB in production)
// ------------------------------------------------------------
const users = [];
const records = [];

// Helper: generate API key (random token)
function generateApiKey() {
  return crypto.randomBytes(32).toString('hex');
}

// Helper: find user by API key
function findUserByApiKey(apiKey) {
  return users.find(u => u.apiKey === apiKey);
}

// Helper: find user by username
function findUserByUsername(username) {
  return users.find(u => u.username === username);
}

// Helper: get next record for a user
function getNextRecordForUser(userId, requestedAmount) {
  // Find first unused record (status not 'success' or 'failed') 
  // Optionally filter by requested_amount if provided
  let candidate = records.find(r => 
    r.userId === userId && 
    r.status !== 'success' && 
    r.status !== 'failed' &&
    (!requestedAmount || r.requested_amount === Number(requestedAmount))
  );
  if (!candidate) {
    // If no exact amount match, fallback to any unused record
    candidate = records.find(r => 
      r.userId === userId && 
      r.status !== 'success' && 
      r.status !== 'failed'
    );
  }
  return candidate || null;
}

// Seed some demo records (optional – remove in production)
function seedDemoData() {
  if (users.length === 0) {
    // Create a demo user
    const hashed = bcrypt.hashSync('password123', 10);
    const user = {
      id: 1,
      username: 'demo',
      passwordHash: hashed,
      apiKey: 'demo-api-key-123',
      balance: 100.00
    };
    users.push(user);

    // Create 10 demo records for the demo user
    for (let i = 1; i <= 10; i++) {
      records.push({
        id: i,
        userId: user.id,
        identifier: `411111111111111${String(i).padStart(2, '0')}`, // dummy card
        field_a: String(i % 12 + 1).padStart(2, '0'), // month
        field_b: '26', // year
        field_c: String(Math.floor(Math.random() * 900 + 100)), // CVV
        school: `Demo School ${i}`,
        requested_amount: 1.00 + (i % 5) * 0.50, // alternating amounts
        status: 'pending', // pending, success, failed
        transaction_id: null,
        message: null,
        amount_paid: null,
        created_at: new Date().toISOString()
      });
    }
  }
}

// ------------------------------------------------------------
// 2. API Routes
// ------------------------------------------------------------

// ---------- AUTH ----------
// POST /api/extension/auth/register
app.post('/api/extension/auth/register', async (req, res) => {
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
    const user = {
      id: users.length + 1,
      username,
      passwordHash: hashed,
      apiKey,
      balance: 0.00  // start with zero; admin can top up
    };
    users.push(user);

    // Optionally, auto-enable account (is_active)
    const is_active = true; // or false if you require admin approval

    res.status(201).json({
      username: user.username,
      api_key: user.apiKey,
      user_id: user.id,
      balance: user.balance.toFixed(2),
      is_active,
      message: is_active ? 'Account created and active' : 'Account created, pending admin approval'
    });
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Registration failed' });
  }
});

// POST /api/extension/auth/login
app.post('/api/extension/auth/login', async (req, res) => {
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

    // Optionally check if user is active (is_active flag)
    // For demo, we treat all as active.

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

// ---------- RECORDS ----------
// GET /api/extension/records/next
app.get('/api/extension/records/next', async (req, res) => {
  try {
    const authHeader = req.headers.authorization;
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return res.status(401).json({ error: 'Missing or invalid Authorization header' });
    }
    const apiKey = authHeader.slice(7);
    const user = findUserByApiKey(apiKey);
    if (!user) {
      return res.status(401).json({ error: 'Invalid API key' });
    }

    const { requested_amount } = req.query;
    const requestedAmount = requested_amount ? Number(requested_amount) : undefined;

    const record = getNextRecordForUser(user.id, requestedAmount);
    if (!record) {
      return res.status(404).json({ error: 'No available records' });
    }

    // Return record
    res.json({
      id: record.id,
      identifier: record.identifier,
      field_a: record.field_a,
      field_b: record.field_b,
      field_c: record.field_c,
      school: record.school || '',
      requested_amount: record.requested_amount,
      balance: user.balance.toFixed(2),
      payment_result_wait_seconds: 5 // optional, extension uses default if not provided
    });
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Failed to fetch record' });
  }
});

// PUT /api/extension/records/:id/status
app.put('/api/extension/records/:id/status', async (req, res) => {
  try {
    const authHeader = req.headers.authorization;
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return res.status(401).json({ error: 'Missing or invalid Authorization header' });
    }
    const apiKey = authHeader.slice(7);
    const user = findUserByApiKey(apiKey);
    if (!user) {
      return res.status(401).json({ error: 'Invalid API key' });
    }

    const recordId = Number(req.params.id);
    const record = records.find(r => r.id === recordId && r.userId === user.id);
    if (!record) {
      return res.status(404).json({ error: 'Record not found or not owned by user' });
    }

    const { status, transaction_id, message, requested_amount, amount_paid, school } = req.body;

    // Validate status
    if (!['success', 'failed'].includes(status)) {
      return res.status(400).json({ error: 'Status must be "success" or "failed"' });
    }

    // Update record
    record.status = status;
    record.transaction_id = transaction_id || null;
    record.message = message || null;
    if (requested_amount !== undefined) record.requested_amount = Number(requested_amount);
    if (amount_paid !== undefined) record.amount_paid = Number(amount_paid);
    if (school) record.school = school;

    // If success, deduct amount_paid from user's balance
    if (status === 'success') {
      const paid = Number(amount_paid) || 0;
      if (paid > 0) {
        user.balance = Math.max(0, user.balance - paid);
      }
    }

    // Return updated balance
    res.json({
      balance: user.balance.toFixed(2),
      record_status: record.status,
      message: record.message
    });
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Failed to update record status' });
  }
});

// ---------- Optional: Admin endpoint to add records ----------
// POST /api/extension/admin/records (for testing)
app.post('/api/extension/admin/records', async (req, res) => {
  // For simplicity, no auth; in production, protect with an admin token.
  try {
    const { userId, identifier, field_a, field_b, field_c, school, requested_amount } = req.body;
    if (!userId || !identifier || !field_a || !field_b || !field_c) {
      return res.status(400).json({ error: 'Missing required fields' });
    }
    const user = users.find(u => u.id === Number(userId));
    if (!user) {
      return res.status(404).json({ error: 'User not found' });
    }
    const newRecord = {
      id: records.length + 1,
      userId: user.id,
      identifier,
      field_a,
      field_b,
      field_c,
      school: school || '',
      requested_amount: Number(requested_amount) || 0,
      status: 'pending',
      transaction_id: null,
      message: null,
      amount_paid: null,
      created_at: new Date().toISOString()
    };
    records.push(newRecord);
    res.status(201).json(newRecord);
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Failed to create record' });
  }
});

// ---------- Optional: endpoint to top up balance ----------
// POST /api/extension/admin/topup
app.post('/api/extension/admin/topup', async (req, res) => {
  try {
    const { username, amount } = req.body;
    if (!username || amount === undefined) {
      return res.status(400).json({ error: 'Username and amount required' });
    }
    const user = findUserByUsername(username);
    if (!user) {
      return res.status(404).json({ error: 'User not found' });
    }
    user.balance += Number(amount);
    res.json({ username: user.username, new_balance: user.balance.toFixed(2) });
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Top-up failed' });
  }
});

// ---------- Root (optional) ----------
app.get('/', (req, res) => {
  res.send('QueuePay API is running.');
});

// ------------------------------------------------------------
// 3. Start server (if run directly, not via Vercel)
// ------------------------------------------------------------
const PORT = process.env.PORT || 3000;

// Seed demo data
seedDemoData();

// Export for Vercel (serverless)
module.exports = app;

// If running as a standalone server
if (require.main === module) {
  app.listen(PORT, () => {
    console.log(`QueuePay server running on port ${PORT}`);
  });
}
