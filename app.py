# CODE Creator Board
# A small website where students can ask for help (editing, filming, design...).
# Data is saved in a SQLite database. Pages are HTML files in templates/
# with $placeholders that Python fills in.

import base64
import hashlib
import hmac
import html
import mimetypes
import os
import re
import secrets
import sqlite3
import string
import time
import threading
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlsplit

PORT = 5001

# folders next to this file
HERE = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(HERE, "board.db")
TEMPLATES = os.path.join(HERE, "templates")
STATIC = os.path.join(HERE, "static")

SKILLS = ["Editing", "Filming", "Design", "Copywriting", "Feedback", "Other"]
STATUSES = ["Open", "In progress", "Done"]
SESSION_SECRET = os.environ.get("SESSION_SECRET", "") or secrets.token_urlsafe(48)
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "0") == "1"
SESSION_SECONDS = 7 * 24 * 60 * 60
PASSWORD_ITERATIONS = 310_000
request_context = threading.local()


# database !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

def get_db():
    # open a connection to the database
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # so I can use row["title"]
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def run_query(sql, params=()):
    # open the database, run one query save and close then return the rows
    conn = get_db()
    rows = conn.execute(sql, params).fetchall()
    conn.commit()
    conn.close()
    return rows


def init_db():
    # create accounts and add an owner column to existing requests if needed
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL COLLATE NOCASE UNIQUE,
            email TEXT UNIQUE COLLATE NOCASE,
            salt TEXT NOT NULL,
            password_hash TEXT NOT NULL
        )
    """)
    user_columns = {row["name"] for row in conn.execute("PRAGMA table_info(users)")}
    if "email" not in user_columns:
        conn.execute("ALTER TABLE users ADD COLUMN email TEXT")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS users_email_unique ON users(email COLLATE NOCASE)")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS help_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            display_name TEXT NOT NULL,
            skill TEXT NOT NULL,
            content_link TEXT,
            status TEXT NOT NULL,
            owner_id INTEGER REFERENCES users(id)
        )
    """)
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(help_requests)")}
    if "owner_id" not in columns:
        conn.execute("ALTER TABLE help_requests ADD COLUMN owner_id INTEGER REFERENCES users(id)")
    count = conn.execute("SELECT COUNT(*) FROM help_requests").fetchone()[0]
    if count == 0:
        examples = [
            ("Help edit a 30-second founder reel",
             "I filmed a short reel and I can't get myaself to edit it! I'm cringing from myself. "
             "Looking for someone to help me edit it. Peer exchange: I can help with copywriting in return.",
             "Mila (demo)", "Editing", "https://example.com/my-reel", "Open"),
            ("Need someone to film a product demo",
             "Thursday afternoon at the CODE campus, about 1 hour. Phone camera is fine.",
             "Jonas (demo)", "Filming", "", "In progress"),
            ("Feedback on my new logo",
             "I made three logo ideas. Which one is the best? Short feedback is enough.",
             "Ava (demo)", "Feedback", "https://example.com/logos", "Done"),
        ]
        conn.executemany(
            "INSERT INTO help_requests (title, description, display_name, skill, content_link, status) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            examples,
        )
    conn.commit()
    conn.close()


def get_request(request_id):
    # return one request, or None if this id does not exist
    rows = run_query("SELECT * FROM help_requests WHERE id = ?", (request_id,))
    if rows:
        return rows[0]
    return None


def check_form(form):
    # read the form and return (data, errors)
    data = {
        "title": form.get("title", "").strip(),
        "description": form.get("description", "").strip(),
        "skill": form.get("skill", ""),
        "content_link": form.get("content_link", "").strip(),
        "status": form.get("status", "Open"),
    }
    errors = []
    if not data["title"]:
        errors.append("Please write a title.")
    if len(data["title"]) > 100:
        errors.append("The title can be at most 100 characters.")
    if not data["description"]:
        errors.append("Please write a description.")
    if data["skill"] not in SKILLS:
        errors.append("Please choose a skill from the list.")
    if data["status"] not in STATUSES:
        errors.append("Please choose a status from the list.")
    if data["content_link"] and not data["content_link"].startswith(("http://", "https://")):
        errors.append("The link must start with http:// or https://")
    return data, errors


def password_record(password, salt=None):
    salt = salt or secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), PASSWORD_ITERATIONS).hex()
    return salt, hashed


def signed_session(user_id, expires, csrf):
    payload = f"{user_id}:{expires}:{csrf}"
    signature = hmac.new(SESSION_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return base64.urlsafe_b64encode(f"{payload}:{signature}".encode()).decode().rstrip("=")


def read_session(cookie_header):
    cookie = SimpleCookie()
    try:
        cookie.load(cookie_header or "")
        value = cookie.get("board_session")
        if not value:
            return None
        decoded = base64.urlsafe_b64decode(value.value + "=" * (-len(value.value) % 4)).decode()
        user_id, expires, csrf, signature = decoded.split(":", 3)
        payload = f"{user_id}:{expires}:{csrf}"
        expected = hmac.new(SESSION_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
        if int(expires) < int(time.time()) or not hmac.compare_digest(signature, expected):
            return None
        rows = run_query("SELECT id, username FROM users WHERE id = ?", (int(user_id),))
        return {"id": int(user_id), "username": rows[0]["username"], "csrf": csrf} if rows else None
    except (ValueError, TypeError, UnicodeDecodeError):
        return None


def csrf_input():
    return f'<input type="hidden" name="csrf" value="{html.escape(request_context.csrf)}">'


def account_page(title, template, **values):
    return page(title, template, safe={"csrf_input": csrf_input()}, **values)


# here starts making pages!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!


def render(name, safe=None, **values):
    # fill the $placeholders in templates/<name>.
    # Every normal value is escaped, so text people type can't become HTML.
    # "safe" is for pieces of HTML we built ourselves (they are already escaped).
    with open(os.path.join(TEMPLATES, name), encoding="utf-8") as file:
        template = string.Template(file.read())
    filled = {key: html.escape(str(value)) for key, value in values.items()}
    filled.update(safe or {})
    return template.substitute(filled)


def page(page_title, name, http_status=200, safe=None, **values):
    # put a template inside base.html and return a full response
    content = render(name, safe, **values)
    user = getattr(request_context, "user", None)
    if user:
        controls = (f'<span>Signed in as {html.escape(user["username"])}</span> '
                    f'<form class="inline-form" method="post" action="/logout">{csrf_input()}'
                    '<button type="submit">Sign out</button></form>')
    else:
        controls = '<a href="/login">Sign in</a> <a href="/signup">Create account</a>'
    body = render("base.html", safe={"content": content, "account_controls": controls}, page_title=page_title)
    return http_status, {"Content-Type": "text/html; charset=utf-8"}, body.encode("utf-8")


def redirect(url):
    # tell the browser to go to another page
    return 302, {"Location": url}, b""


def error_page(title, message, status):
    return page(title, "error.html", status, title=title, message=message)


def not_found():
    return error_page("Page not found",
                      "This page or request does not exist (maybe it was deleted).", 404)


def status_class(status):
    # "In progress" -> "status-in-progress" (used by the CSS for colours)
    return "status-" + status.lower().replace(" ", "-")


def make_options(choices, chosen):
    # <option> tags for a <select>, with the chosen one selected
    options = []
    for choice in choices:
        selected = " selected" if choice == chosen else ""
        value = html.escape(choice)
        options.append(f'<option value="{value}"{selected}>{value}</option>')
    return "\n".join(options)


def render_form(data, errors=None, request_id=None, status=200):
    # show the form page; we are editing if we know which request it is
    editing = request_id is not None
    errors_html = ""
    if errors:
        items = "\n".join(f"<li>{html.escape(error)}</li>" for error in errors)
        errors_html = render("errors.html", safe={"items": items})
    if editing:
        title = "Edit request"
        heading = f"Edit request #{request_id}"
        action = f"/requests/{request_id}/edit"
        button_text = "Save changes"
        cancel_url = f"/requests/{request_id}"
    else:
        title = heading = "Ask for help"
        action = "/requests"
        button_text = "Post request"
        cancel_url = "/requests"
    safe = {
        "errors": errors_html,
        "csrf_input": csrf_input(),
        "skill_options": make_options(SKILLS, data["skill"]),
        "status_options": make_options(STATUSES, data["status"]),
    }
    return page(title, "form.html", status, safe,
                heading=heading, action=action, button_text=button_text,
                cancel_url=cancel_url, title=data["title"],
                description=data["description"], display_name=data.get("display_name", ""),
                content_link=data["content_link"] or "")


# the pages (one function per route)!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

def home():
    return redirect("/requests")


def about():
    return page("About", "about.html")


def list_requests():
    rows = run_query("SELECT * FROM help_requests ORDER BY id DESC")
    if not rows:
        empty = '<p class="empty">No requests yet. Be the first to ask for help!</p>'
        return page("Requests", "list.html", safe={"cards": empty},
                    account_message=("Signed in as " + request_context.user["username"]
                                     if request_context.user else "Everyone can read requests. Sign in to post your own."))
    cards = []
    for row in rows:
        cards.append(render("card.html", id=row["id"], title=row["title"],
                            skill=row["skill"], status=row["status"],
                            status_class=status_class(row["status"]),
                            display_name=row["display_name"]))
    cards_html = '<ul class="cards">\n' + "\n".join(cards) + "\n</ul>"
    return page("Requests", "list.html", safe={"cards": cards_html},
                account_message=("Signed in as " + request_context.user["username"]
                                 if request_context.user else "Everyone can read requests. Sign in to post your own."))


def new_request():
    if not request_context.user:
        return redirect("/login")
    empty = {"title": "", "description": "", "display_name": "", "skill": "",
             "content_link": "", "status": "Open"}
    return render_form(empty)


def create_request(form):
    if not request_context.user:
        return redirect("/login")
    data, errors = check_form(form)
    if errors:
        return render_form(data, errors, status=400)
    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO help_requests (title, description, display_name, skill, content_link, status, owner_id) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (data["title"], data["description"], request_context.user["username"], data["skill"],
         data["content_link"], data["status"], request_context.user["id"]),
    )
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return redirect(f"/requests/{new_id}")


def show_request(request_id):
    row = get_request(request_id)
    if row is None:
        return not_found()
    link_html = ""
    if row["content_link"]:
        link = html.escape(row["content_link"])
        link_html = f'<p>Content link: <a href="{link}" rel="noopener nofollow">{link}</a></p>'
    owner_actions = ""
    if request_context.user and row["owner_id"] == request_context.user["id"]:
        owner_actions = (f'<div class="actions"><a class="button" href="/requests/{row["id"]}/edit">Edit</a> '
                         f'<a class="button button-danger" href="/requests/{row["id"]}/delete">Delete</a></div>')
    return page(row["title"], "detail.html", safe={"link": link_html, "owner_actions": owner_actions},
                id=row["id"], title=row["title"], skill=row["skill"],
                status=row["status"], status_class=status_class(row["status"]),
                display_name=row["display_name"], description=row["description"])


def edit_request(request_id):
    row = get_request(request_id)
    if row is None:
        return not_found()
    if not request_context.user or row["owner_id"] != request_context.user["id"]:
        return error_page("Not your request", "You can only edit requests created by your account.", 403)
    return render_form(row, request_id=request_id)


def update_request(request_id, form):
    row = get_request(request_id)
    if row is None:
        return not_found()
    if not request_context.user or row["owner_id"] != request_context.user["id"]:
        return error_page("Not your request", "You can only edit requests created by your account.", 403)
    data, errors = check_form(form)
    if errors:
        return render_form(data, errors, request_id, status=400)
    run_query(
        "UPDATE help_requests SET title = ?, description = ?, skill = ?, "
        "content_link = ?, status = ? WHERE id = ? AND owner_id = ?",
        (data["title"], data["description"], data["skill"],
         data["content_link"], data["status"], request_id, request_context.user["id"]),
    )
    return redirect(f"/requests/{request_id}")


def confirm_delete(request_id):
    # only shows a question, nothing is deleted here
    row = get_request(request_id)
    if row is None:
        return not_found()
    if not request_context.user or row["owner_id"] != request_context.user["id"]:
        return error_page("Not your request", "You can only delete requests created by your account.", 403)
    return page("Delete request", "delete.html", safe={"csrf_input": csrf_input()}, id=row["id"], title=row["title"])


def delete_request(request_id):
    row = get_request(request_id)
    if row is None:
        return not_found()
    if not request_context.user or row["owner_id"] != request_context.user["id"]:
        return error_page("Not your request", "You can only delete requests created by your account.", 403)
    run_query("DELETE FROM help_requests WHERE id = ? AND owner_id = ?", (request_id, request_context.user["id"]))
    return redirect("/requests")


def login_page(message=""):
    return account_page("Sign in", "login.html", message=message)


def signup_page(message=""):
    return account_page("Create account", "signup.html", message=message)


def create_account(form):
    username = form.get("username", "").strip()
    email = form.get("email", "").strip().lower()
    password = form.get("password", "")
    if not re.fullmatch(r"[a-z0-9._%+-]+@code\.berlin", email):
        return signup_page("Use an email address ending in @code.berlin.")
    if not re.fullmatch(r"[A-Za-z0-9_]{3,30}", username):
        return signup_page("Choose a username with 3–30 letters, numbers, or underscores.")
    if len(password) < 12:
        return signup_page("Choose a password with at least 12 characters.")
    salt, hashed = password_record(password)
    conn = get_db()
    try:
        cursor = conn.execute("INSERT INTO users (username, email, salt, password_hash) VALUES (?, ?, ?, ?)",
                              (username, email, salt, hashed))
        conn.commit()
        request_context.user = {"id": cursor.lastrowid, "username": username}
        request_context.new_session = True
        return redirect("/requests")
    except sqlite3.IntegrityError:
        return signup_page("That username or email address is already in use.")
    finally:
        conn.close()


def sign_in(form):
    username = form.get("username", "").strip()
    password = form.get("password", "")
    rows = run_query("SELECT * FROM users WHERE username = ? COLLATE NOCASE", (username,))
    if not rows:
        return login_page("Username or password is incorrect.")
    user = rows[0]
    _, candidate = password_record(password, user["salt"])
    if not hmac.compare_digest(candidate, user["password_hash"]):
        return login_page("Username or password is incorrect.")
    request_context.user = {"id": user["id"], "username": user["username"]}
    request_context.new_session = True
    return redirect("/requests")


def static_file(filename):
    # send a file from static/ (only files that are really in that folder)
    if filename not in os.listdir(STATIC):
        return not_found()
    with open(os.path.join(STATIC, filename), "rb") as file:
        body = file.read()
    content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    return 200, {"Content-Type": content_type}, body


# routing: which function answers which URL!!!!!!!!!!!!!!!!!!!!!!!!!

def handle_request(method, path, form):
    # The same URL can have a GET and a POST version.
    # For /requests/<id>/... we read the id from the URL (a "dynamic route").
    parts = path.split("/")  # "/requests/5/edit" -> ["", "requests", "5", "edit"]
    request_id = None
    if len(parts) in (3, 4) and parts[1] == "requests" and parts[2].isdigit():
        request_id = int(parts[2])
        route = "/requests/<id>" + path[len("/requests/" + parts[2]):]
    elif len(parts) == 3 and parts[1] == "static":
        route = "/static/<file>"
    else:
        route = path

    if route == "/":
        if method == "GET":
            return home()
    elif route == "/about":
        if method == "GET":
            return about()
    elif route == "/login":
        if method == "GET":
            return login_page()
        if method == "POST":
            return sign_in(form)
    elif route == "/signup":
        if method == "GET":
            return signup_page()
        if method == "POST":
            return create_account(form)
    elif route == "/logout":
        if method == "POST":
            request_context.logout = True
            return redirect("/requests")
    elif route == "/requests":
        if method == "GET":
            return list_requests()
        if method == "POST":
            return create_request(form)
    elif route == "/requests/new":
        if method == "GET":
            return new_request()
    elif route == "/requests/<id>":
        if method == "GET":
            return show_request(request_id)
    elif route == "/requests/<id>/edit":
        if method == "GET":
            return edit_request(request_id)
        if method == "POST":
            return update_request(request_id, form)
    elif route == "/requests/<id>/delete":
        if method == "GET":
            return confirm_delete(request_id)
        if method == "POST":
            return delete_request(request_id)
    elif route == "/static/<file>":
        if method == "GET":
            return static_file(parts[2])
    else:
        return not_found()
    # the URL exists, but not with this method (for example POST /about)
    return 405, {"Content-Type": "text/plain; charset=utf-8"}, b"Method Not Allowed"


def answer(method, path, form):
    # like handle_request, but shows the database error page if SQLite fails
    try:
        return handle_request(method, path, form)
    except sqlite3.Error as error:
        print("Database error:", error)
        return error_page("Database problem",
                          "Something went wrong with the database. Please try again later.", 500)


def same_site_form(headers):
    # Browsers send Origin for forms. Referer is a fallback for older clients.
    host = headers.get("Host", "").lower()
    source = headers.get("Origin") or headers.get("Referer")
    if not host or not source:
        return False
    parsed = urlsplit(source)
    return parsed.scheme in ("http", "https") and parsed.netloc.lower() == host


# the web server!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

class Handler(BaseHTTPRequestHandler):
    # http.server needs a class; it calls do_GET / do_POST for each request

    def do_GET(self):
        self.respond("GET")

    def do_HEAD(self):
        self.respond("HEAD")

    def do_POST(self):
        self.respond("POST")

    def respond(self, method):
        path = unquote(urlsplit(self.path).path)  # drop "?..." and decode %20 etc.
        session = read_session(self.headers.get("Cookie", ""))
        csrf_cookie = SimpleCookie()
        try:
            csrf_cookie.load(self.headers.get("Cookie", ""))
        except Exception:
            pass
        anonymous_csrf = csrf_cookie.get("board_csrf")
        request_context.user = session
        request_context.csrf = session["csrf"] if session else (anonymous_csrf.value if anonymous_csrf else secrets.token_urlsafe(24))
        request_context.new_session = False
        request_context.logout = False
        request_context.set_csrf = not session and not anonymous_csrf
        if method == "POST":
            if not same_site_form(self.headers):
                self.send_simple(403, "This form must be submitted from the board website.")
                return

        form = {}
        if method == "POST":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8", errors="replace")
            # parse_qs gives lists, like {"title": ["Hi"]}; we keep the first value
            form = {key: values[0] for key, values in parse_qs(body, keep_blank_values=True).items()}
            csrf_value = session["csrf"] if session else (anonymous_csrf.value if anonymous_csrf else "")
            if not csrf_value or not secrets.compare_digest(form.get("csrf", ""), csrf_value):
                self.send_simple(403, "The form expired. Please reload the page and try again.")
                return
        # HEAD is a GET without the page content
        status, headers, content = answer("GET" if method == "HEAD" else method, path, form)
        self.send_response(status)
        for name, value in headers.items():
            self.send_header(name, value)
        if request_context.new_session:
            new_csrf = secrets.token_urlsafe(24)
            token = signed_session(request_context.user["id"], int(time.time()) + SESSION_SECONDS, new_csrf)
            self.send_header("Set-Cookie", f"board_session={token}; Path=/; HttpOnly; SameSite=Lax; Max-Age={SESSION_SECONDS}" + ("; Secure" if COOKIE_SECURE else ""))
            self.send_header("Set-Cookie", f"board_csrf={new_csrf}; Path=/; SameSite=Lax; Max-Age={SESSION_SECONDS}" + ("; Secure" if COOKIE_SECURE else ""))
        elif request_context.logout:
            self.send_header("Set-Cookie", "board_session=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0" + ("; Secure" if COOKIE_SECURE else ""))
            self.send_header("Set-Cookie", "board_csrf=; Path=/; SameSite=Lax; Max-Age=0" + ("; Secure" if COOKIE_SECURE else ""))
        elif request_context.set_csrf:
            self.send_header("Set-Cookie", f"board_csrf={request_context.csrf}; Path=/; SameSite=Lax" + ("; Secure" if COOKIE_SECURE else ""))
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        if method != "HEAD":
            self.wfile.write(content)

    def send_simple(self, status, message, extra_headers=None):
        content = (message + "\n").encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        for name, value in (extra_headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(content)


if __name__ == "__main__":
    init_db()
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"Running on http://localhost:{PORT} (press Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
