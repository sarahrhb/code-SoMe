# CODE Creator Board
# A small website where students can ask for help (editing, filming, design...).
# Data is saved in a SQLite database. Pages are HTML files in templates/
# with $placeholders that Python fills in.

import base64
import html
import mimetypes
import os
import secrets
import sqlite3
import string
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


# database !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

def get_db():
    # open a connection to the database
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # so I can use row["title"]
    return conn


def run_query(sql, params=()):
    # open the database, run one query save and close then return the rows
    conn = get_db()
    rows = conn.execute(sql, params).fetchall()
    conn.commit()
    conn.close()
    return rows


def init_db():
    # create the table and add some example requests if it is empty
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS help_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            display_name TEXT NOT NULL,
            skill TEXT NOT NULL,
            content_link TEXT,
            status TEXT NOT NULL
        )
    """)
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
        "display_name": form.get("display_name", "").strip(),
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
    if not data["display_name"]:
        errors.append("Please write a display name.")
    if data["skill"] not in SKILLS:
        errors.append("Please choose a skill from the list.")
    if data["status"] not in STATUSES:
        errors.append("Please choose a status from the list.")
    if data["content_link"] and not data["content_link"].startswith(("http://", "https://")):
        errors.append("The link must start with http:// or https://")
    return data, errors


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
    body = render("base.html", safe={"content": content}, page_title=page_title)
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
        "skill_options": make_options(SKILLS, data["skill"]),
        "status_options": make_options(STATUSES, data["status"]),
    }
    return page(title, "form.html", status, safe,
                heading=heading, action=action, button_text=button_text,
                cancel_url=cancel_url, title=data["title"],
                description=data["description"], display_name=data["display_name"],
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
        return page("Requests", "list.html", safe={"cards": empty})
    cards = []
    for row in rows:
        cards.append(render("card.html", id=row["id"], title=row["title"],
                            skill=row["skill"], status=row["status"],
                            status_class=status_class(row["status"]),
                            display_name=row["display_name"]))
    cards_html = '<ul class="cards">\n' + "\n".join(cards) + "\n</ul>"
    return page("Requests", "list.html", safe={"cards": cards_html})


def new_request():
    empty = {"title": "", "description": "", "display_name": "", "skill": "",
             "content_link": "", "status": "Open"}
    return render_form(empty)


def create_request(form):
    data, errors = check_form(form)
    if errors:
        return render_form(data, errors, status=400)
    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO help_requests (title, description, display_name, skill, content_link, status) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (data["title"], data["description"], data["display_name"], data["skill"],
         data["content_link"], data["status"]),
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
    return page(row["title"], "detail.html", safe={"link": link_html},
                id=row["id"], title=row["title"], skill=row["skill"],
                status=row["status"], status_class=status_class(row["status"]),
                display_name=row["display_name"], description=row["description"])


def edit_request(request_id):
    row = get_request(request_id)
    if row is None:
        return not_found()
    return render_form(row, request_id=request_id)


def update_request(request_id, form):
    if get_request(request_id) is None:
        return not_found()
    data, errors = check_form(form)
    if errors:
        return render_form(data, errors, request_id, status=400)
    run_query(
        "UPDATE help_requests SET title = ?, description = ?, display_name = ?, skill = ?, "
        "content_link = ?, status = ? WHERE id = ?",
        (data["title"], data["description"], data["display_name"], data["skill"],
         data["content_link"], data["status"], request_id),
    )
    return redirect(f"/requests/{request_id}")


def confirm_delete(request_id):
    # only shows a question, nothing is deleted here
    row = get_request(request_id)
    if row is None:
        return not_found()
    return page("Delete request", "delete.html", id=row["id"], title=row["title"])


def delete_request(request_id):
    if get_request(request_id) is None:
        return not_found()
    run_query("DELETE FROM help_requests WHERE id = ?", (request_id,))
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


def has_write_password(headers):
    # One shared password keeps this demo simple. It is not a user account system.
    expected_password = os.environ.get("BOARD_WRITE_PASSWORD", "")
    if not expected_password:
        return None  # editing is disabled until the owner sets a password

    authorization = headers.get("Authorization", "")
    try:
        scheme, encoded = authorization.split(" ", 1)
        if scheme.lower() != "basic":
            return False
        username, password = base64.b64decode(encoded, validate=True).decode("utf-8").split(":", 1)
    except (ValueError, UnicodeDecodeError):
        return False

    return username == "community" and secrets.compare_digest(password, expected_password)


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
        if method == "POST":
            if not same_site_form(self.headers):
                self.send_simple(403, "This form must be submitted from the board website.")
                return
            password_ok = has_write_password(self.headers)
            if password_ok is None:
                self.send_simple(503, "Board editing is disabled until BOARD_WRITE_PASSWORD is set.")
                return
            if not password_ok:
                self.send_simple(
                    401,
                    "Enter the shared board password. The username is community.",
                    {"WWW-Authenticate": 'Basic realm="CODE Creator Board", charset="UTF-8"'},
                )
                return

        form = {}
        if method == "POST":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8", errors="replace")
            # parse_qs gives lists, like {"title": ["Hi"]}; we keep the first value
            form = {key: values[0] for key, values in parse_qs(body, keep_blank_values=True).items()}
        # HEAD is a GET without the page content
        status, headers, content = answer("GET" if method == "HEAD" else method, path, form)
        self.send_response(status)
        for name, value in headers.items():
            self.send_header(name, value)
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
