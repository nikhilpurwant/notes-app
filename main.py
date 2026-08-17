import sqlite3
from flask import Flask, g, redirect, render_template_string, request, session

app = Flask(__name__)
app.secret_key = "lab-secret-key"
DATABASE = "vulnerable_lab.db"


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(error):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    with app.app_context():
        db = get_db()
        db.executescript(
            """
            DROP TABLE IF EXISTS users;
            DROP TABLE IF EXISTS notes;

            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password TEXT,
                role TEXT
            );

            CREATE TABLE notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                title TEXT,
                content TEXT
            );

            INSERT INTO users (username, password, role) VALUES 
                ('alice', 'alice123', 'user'),
                ('bob', 'bob123', 'user'),
                ('admin', 'adminpass', 'admin');

            INSERT INTO notes (user_id, title, content) VALUES 
                (1, 'Alice Secret Note', 'Meeting notes with client.'),
                (2, 'Bob Private Key', 'ssh-rsa AAAAB3NzaC1yc2E...');
        """
        )
        db.commit()


BASE_TEMPLATE = """
<!doctype html>
<html>
<head><title>OWASP Vulnerability Lab</title></head>
<body style="font-family: sans-serif; max-width: 800px; margin: 40px auto; line-height: 1.6;">
    <h2>Flask Security Lab</h2>
    {% if session.get('username') %}
        <p>Logged in as: <strong>{{ session['username'] }}</strong> (User ID: {{ session['user_id'] }}) | <a href="/logout">Logout</a></p>
        <hr>
        <h3>Create Note</h3>
        <form method="POST" action="/notes/create">
            <input type="text" name="title" placeholder="Note Title" required><br><br>
            <textarea name="content" placeholder="Note Content" rows="3" cols="40" required></textarea><br><br>
            <button type="submit">Save Note</button>
        </form>

        <h3>All Notes</h3>
        <ul>
        {% for note in notes %}
            <li>
                <strong>{{ note.title }}</strong> (ID: {{ note.id }}, Owner ID: {{ note.user_id }})
                <!-- VULNERABILITY: Stored XSS rendered without escaping -->
                <p>Content: {{ note.content | safe }}</p>
                <a href="/notes/delete?id={{ note.id }}">Delete Note</a>
            </li>
        {% endfor %}
        </ul>
    {% else %}
        <h3>Login</h3>
        <form method="POST" action="/login">
            <input type="text" name="username" placeholder="Username" required><br><br>
            <input type="password" name="password" placeholder="Password" required><br><br>
            <button type="submit">Login</button>
        </form>
    {% endif %}
</body>
</html>
"""


@app.route("/")
def index():
    notes = []
    if "user_id" in session:
        db = get_db()
        notes = db.execute("SELECT * FROM notes").fetchall()
    return render_template_string(BASE_TEMPLATE, notes=notes)


# -------------------------------------------------------------
# 1. Injection (A05) - SQL Injection Authentication Bypass
# -------------------------------------------------------------
@app.route("/login", methods=["POST"])
def login():
    username = request.form.get("username")
    password = request.form.get("password")
    db = get_db()

    # VULNERABLE: Direct string formatting into SQL query
    query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
    user = db.execute(query).fetchone()

    if user:
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        return redirect("/")
    return "Invalid credentials", 401


# -------------------------------------------------------------
# 2. Broken Access Control (A01) - Insecure Direct Object Reference (IDOR)
# -------------------------------------------------------------
@app.route("/notes/delete")
def delete_note():
    if "user_id" not in session:
        return "Unauthorized", 401

    note_id = request.args.get("id")
    db = get_db()

    # VULNERABLE: Deletes record purely based on parameter ID without verifying session user ownership
    db.execute("DELETE FROM notes WHERE id = ?", (note_id,))
    db.commit()
    return redirect("/")


# -------------------------------------------------------------
# 3. Injection / XSS (A05) - Stored Cross-Site Scripting
# -------------------------------------------------------------
@app.route("/notes/create", methods=["POST"])
def create_note():
    if "user_id" not in session:
        return "Unauthorized", 401

    title = request.form.get("title")
    content = request.form.get("content")
    db = get_db()

    db.execute(
        "INSERT INTO notes (user_id, title, content) VALUES (?, ?, ?)",
        (session["user_id"], title, content),
    )
    db.commit()
    return redirect("/")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)