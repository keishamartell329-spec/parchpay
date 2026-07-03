// api/data.js
// In-memory data store (replace with a real DB in production)

const users = [];
const records = [];

// ---------- User helpers ----------
function findUserByApiKey(apiKey) {
  return users.find(u => u.apiKey === apiKey);
}

function findUserByUsername(username) {
  return users.find(u => u.username === username);
}

function findUserById(id) {
  return users.find(u => u.id === id);
}

function createUser(username, passwordHash, apiKey, balance = 0) {
  const user = {
    id: users.length + 1,
    username,
    passwordHash,
    apiKey,
    balance,
    isActive: true, // admin can deactivate
  };
  users.push(user);
  return user;
}

// ---------- Record helpers ----------
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
    // Fallback to any unused record
    candidate = records.find(r =>
      r.userId === userId &&
      r.status !== 'success' &&
      r.status !== 'failed'
    );
  }
  return candidate || null;
}

function createRecord(userId, identifier, field_a, field_b, field_c, school, requested_amount) {
  const record = {
    id: records.length + 1,
    userId,
    identifier,
    field_a,
    field_b,
    field_c,
    school: school || '',
    requested_amount: Number(requested_amount) || 0,
    status: 'pending',   // pending, success, failed
    transaction_id: null,
    message: null,
    amount_paid: null,
    created_at: new Date().toISOString()
  };
  records.push(record);
  return record;
}

function updateRecordStatus(recordId, userId, data) {
  const record = records.find(r => r.id === recordId && r.userId === userId);
  if (!record) return null;
  record.status = data.status;
  record.transaction_id = data.transaction_id || null;
  record.message = data.message || null;
  if (data.requested_amount !== undefined) record.requested_amount = Number(data.requested_amount);
  if (data.amount_paid !== undefined) record.amount_paid = Number(data.amount_paid);
  if (data.school) record.school = data.school;
  return record;
}

function updateUserBalance(userId, amount) {
  const user = findUserById(userId);
  if (!user) return null;
  user.balance = Math.max(0, user.balance + amount);
  return user;
}

// ---------- Seed demo data (optional) ----------
function seedDemoData() {
  if (users.length === 0) {
    // Create a demo user
    const bcrypt = require('bcryptjs');
    const hashed = bcrypt.hashSync('password123', 10);
    const user = createUser('demo', hashed, 'demo-api-key-123', 100.00);
    // Create 10 demo records
    for (let i = 1; i <= 10; i++) {
      createRecord(
        user.id,
        `411111111111111${String(i).padStart(2, '0')}`,
        String(i % 12 + 1).padStart(2, '0'),
        '26',
        String(Math.floor(Math.random() * 900 + 100)),
        `Demo School ${i}`,
        1.00 + (i % 5) * 0.50
      );
    }
  }
}

module.exports = {
  users,
  records,
  findUserByApiKey,
  findUserByUsername,
  findUserById,
  createUser,
  getNextRecordForUser,
  createRecord,
  updateRecordStatus,
  updateUserBalance,
  seedDemoData
};
