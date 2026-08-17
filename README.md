# Vulnerable Notes App

A deliberately vulnerable Flask lab application demonstrating common security vulnerabilities:
- **A05: Injection** - SQL Injection in Authentication
- **A01: Broken Access Control** - Insecure Direct Object Reference (IDOR) on note deletion
- **A05: Injection / XSS** - Stored Cross-Site Scripting (XSS) in note content rendering

## Running the Application

```bash
uv run python main.py
```

Access the web interface at `http://127.0.0.1:5000` (or `http://localhost:5000`).

## Seeded Accounts

The database initializes with the following demo credentials:
- `alice` / `alice123` (Role: user)
- `bob` / `bob123` (Role: user)
- `admin` / `adminpass` (Role: admin)

---

## Vulnerability Testing & Exploitation Guide

### Vulnerability 1: SQL Injection (Authentication Bypass)

- **Vulnerable Endpoint**: `POST /login`
- **Root Cause**: Raw string concatenation allows the SQL parser to interpret user input as logic operators.
- **Exploit Payload**:
  - **Username**: `admin' --`
  - **Password**: *(any value)*
- **Resulting Query**:
  ```sql
  SELECT * FROM users WHERE username = 'admin' --' AND password = '...'
  ```
  The `--` comments out the password clause entirely, authenticating you directly as the `admin` user without checking the password.

---

### Vulnerability 2: Insecure Direct Object Reference (IDOR / Broken Access Control)

- **Vulnerable Endpoint**: `GET /notes/delete?id=<note_id>`
- **Root Cause**: The endpoint checks authentication (is the user logged in?), but skips authorization (does this note belong to this user?).
- **Exploit Steps**:
  1. Log in as `alice` (`alice` / `alice123`, `user_id = 1`).
  2. Inspect the UI and note that Bob's note has `id = 2`.
  3. Navigate directly in your browser to:
     ```
     http://localhost:5000/notes/delete?id=2
     ```
  4. **Result**: Alice deletes Bob's private note despite not owning it.

---

### Vulnerability 3: Stored Cross-Site Scripting (XSS)

- **Vulnerable Endpoint**: `POST /notes/create` rendered via `{{ note.content | safe }}`
- **Root Cause**: Disabling Jinja's auto-escaping (`| safe`) causes raw browser-executable scripts stored in the database to execute in every visitor's browser session.
- **Exploit Payload**:
  1. Create a note with the following content:
     ```html
     <script>alert('Session Stolen: ' + document.cookie);</script>
     ```
  2. **Result**: Every time a user loads the home page, the JavaScript payload executes within their browser context.

