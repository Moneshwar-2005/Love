import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sqlite3
from backend.app.security import verify_password

conn = sqlite3.connect('database/love.db')
cursor = conn.cursor()
query = "SELECT u.username, u.email, u.is_owner, c.password_hash, c.failed_login_attempts, c.locked_until FROM users u JOIN user_credentials c ON u.id = c.user_id WHERE u.username = 'work_persist_1795095542'"
row = cursor.execute(query).fetchone()
if row:
    print('Username:', row[0])
    print('Email:', row[1])
    print('is_owner:', bool(row[2]))
    print('Password Match (SecurePassword123!):', verify_password('SecurePassword123!', row[3]))
    print('Failed attempts:', row[4])
    print('Locked until:', row[5])
else:
    print('User not found')
conn.close()
