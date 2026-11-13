import html
import mimetypes
import os
import sqlite3
import string
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlsplit

DATABASE = "board.db"
PORT = 5001

# folders next to this file
HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATES = os.path.join(HERE, "templates")
STATIC = os.path.join(HERE, "static")

SKILLS = ["Editing", "Filming", "Design", "Copywriting", "Feedback", "Other"]
STATUSES = ["Open", "In progress", "Done"]


# database hereeee my girl

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # so I can use row["title"]
    return conn
def run_query(sql, params=()):
    conn = get_db()
    rows = conn.execute(sql, params).fetchall()
    conn.commit()
    conn.close()
    return rows
def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS help_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            display_name TEXT NOT NULL,
            skill TEXT NOT NULL,
            content_link TEXT,
            status TEXT NOT NULL)""")
    conn.commit()
    conn.close()
def get_request(request_id):
    rows = run_query("SELECT * FROM help_requests WHERE id = ?", (request_id,))
    if rows:
        return rows[0]
    return None
def check_form(form):
    data = {
        "title": form.get("title", "").strip(),
        "description": form.get("description", "").strip(),
        "display_name": form.get("display_name", "").strip(),
        "skill": form.get("skill", ""),
        "content_link": form.get("content_link", "").strip(),
        "status": form.get("status", "Open"),}
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


# end of database my girrlll


def render(name, safe=None, **values):
    with open(os.path.join(TEMPLATES, name), encoding="utf-8") as file:
        template = string.Template(file.read())
    filled = {key: html.escape(str(value)) for key, value in values.items()}
    filled.update(safe or {})
    return template.substitute(filled)


def page(page_title, name, http_status=200, safe=None, **values): 
    content = render(name, safe, **values)
    body = render("base.html", safe={"content": content}, page_title=page_title)
    return http_status, {"Content-Type": "text/html; charset=utf-8"}, body.encode("utf-8")


def redirect(url):
    return 302, {"Location": url}, b"" # telling the browser to go to another page


def error_page(title, message, status):
    return page(title, "error.html", status, title=title, message=message)


def not_found():
    return error_page("Page not found",
                      "This page or request does not exist (maybe it was deleted).", 404)


def status_class(status): # "Open" -> "Done" etc etc
    return "status-" + status.lower().replace(" ", "-")


def make_options(choices, chosen):
    options = []
    for choice in choices:
        selected = " selected" if choice == chosen else ""
        value = html.escape(choice)
        options.append(f'<option value="{value}"{selected}>{value}</option>')
    return "\n".join(options)


def render_form(data, errors=None, request_id=None, status=200):
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


# pages etc

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
#create request
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
#find request
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
#edit request
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
         data["content_link"], data["status"], request_id))
    return redirect(f"/requests/{request_id}")
def confirm_delete(request_id):# shows a question
    row = get_request(request_id)
    if row is None:
        return not_found()
    return page("Delete request", "delete.html", id=row["id"], title=row["title"])
def delete_request(request_id):
    if get_request(request_id) is None:
        return not_found()
    run_query("DELETE FROM help_requests WHERE id = ?", (request_id,))
    return redirect("/requests")


def static_file(filename):# send a file from static
    if filename not in os.listdir(STATIC):
        return not_found()
    with open(os.path.join(STATIC, filename), "rb") as file:
        body = file.read()
    content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    return 200, {"Content-Type": content_type}, body


# routing
def handle_request(method, path, form):
    # For /requests/<id>/... we read the id from the URL (a "dynamic route").
    parts = path.split("/") 
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
    return 405, {"Content-Type": "text/plain; charset=utf-8"}, b"Method Not Allowed"


def answer(method, path, form):
    try:
        return handle_request(method, path, form)
    except sqlite3.Error as error:
        print("Database error:", error)
        return error_page("Database problem",
                          "Something went wrong with the database. Please try again later.", 500)


# the web server things here
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.respond("GET")
    def do_HEAD(self):
        self.respond("HEAD")
    def do_POST(self):
        self.respond("POST")
    def respond(self, method):
        path = unquote(urlsplit(self.path).path) 
        form = {}
        if method == "POST":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8", errors="replace")
            form = {key: values[0] for key, values in parse_qs(body, keep_blank_values=True).items()}
        status, headers, content = answer("GET" if method == "HEAD" else method, path, form)
        self.send_response(status)
        for name, value in headers.items():
            self.send_header(name, value)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        if method != "HEAD":
            self.wfile.write(content)

if __name__ == "__main__":
    init_db()
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"Running on http://localhost:{PORT} (press Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
