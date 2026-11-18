import  html
import json
import mimetypes
import os
import sqlite3
import  string
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse  import parse_qs, unquote,    urlsplit

DATABASE =   "board.db"
PORT = int(os.environ.get("PORT", "5001"))
HOST =  os.environ.get("HOST", "0.0.0.0")

# folders next to this file
ROOT  = os.path.dirname(os.path.abspath(__file__))
HTML = os.path.join(ROOT, "templates")
FILES = os.path.join(ROOT,   "static")

SKILLS  = ["Editing", "Filming", "Design", "Copywriting",   "Feedback", "Other"]
STATUSES = ["Open",    "In progress", "Done"]



# database hereeee my girl



# dear database, it is me again
# open the database
def db():
    c = sqlite3.connect(DATABASE)
    c.row_factory =    sqlite3.Row  # so I can use row["title"]
    return c



# asking sqlite nicely because yelling did not work
# run sql and return the rows
def  query(sql, params=()):
    c = db()
    rows =    c.execute(sql, params).fetchall()
    c.commit()
    c.close()
    return rows



# make the table if it is missing
def    setup():
    c = db()
    c.execute("""
        CREATE TABLE IF NOT EXISTS help_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            display_name TEXT NOT NULL,
            skill TEXT NOT NULL,
            content_link TEXT,
            status TEXT NOT NULL)""")

    c.commit()
    c.close()
# get one request by its id
def find(rid):
    rows = query("SELECT * FROM help_requests WHERE id = ?", (rid,))
    if rows:
        return rows[0]
    return   None



# vibe check, but with required fields
# check the form fields
def check(form):
    data = {
        "title": form.get("title", "").strip(),
        "description": form.get("description", "").strip(),
        "display_name": form.get("display_name",    "").strip(),
        "skill":  form.get("skill", ""),
        "content_link": form.get("content_link", "").strip(),
        "status": form.get("status", "Open"),}
    errors   = []
    if  not data["title"]:
        errors.append("Please write a title.")
    if len(data["title"]) >   100:
        errors.append("The title can be at most 100 characters.")
    if not data["description"]:
        errors.append("Please write a description.")
    if   not data["display_name"]:
        errors.append("Please write a display name.")
    if data["skill"] not in SKILLS:
        errors.append("Please choose a skill from the list.")
    if data["status"]    not in STATUSES:
        errors.append("Please choose a status from the list.")
    if    data["content_link"] and   not data["content_link"].startswith(("http://", "https://")):
        errors.append("The link must start with http:// or https://")
    return data, errors


# end of database my girrlll




# html is getting dressed
# put values into an html file
def fill(name, safe=None, **values):
    with open(os.path.join(HTML, name), encoding="utf-8")    as file:
        template = string.Template(file.read())
    filled   = {key: html.escape(str(value)) for key, value in values.items()}
    filled.update(safe   or {})
    return template.substitute(filled)


# wrap the page and set its response code
def page(page_title, name, code=200, safe=None, **values):
    content = fill(name, safe,   **values)
    body  = fill("base.html",    safe={"content":   content}, page_title=page_title)
    return code, {"Content-Type": "text/html; charset=utf-8"}, body.encode("utf-8")


# nothing to see here, keep walking
# send the browser to another url
def redirect(url):
    return 302, {"Location": url}, b""   # telling the browser to go to another page




# show an error page
def oops(title,    message, status):
    return page(title, "error.html", status, title=title,   message=message)





# it was here a second ago i swear
# the 404 page
def missing():
    return oops("Page not found",
                      "This page or request does not exist (maybe it was deleted).", 404)




# turn a status into a css class
def   status_css(status):  # "Open" -> "Done" etc etc
    return "status-"    + status.lower().replace(" ", "-")





# so many choices. still no option to go home
# make the dropdown choices
def options(choices, chosen):
    options = []

    for choice in   choices:
        sel  = " selected" if choice ==    chosen else ""
        value   = html.escape(choice)
        options.append(f'<option value="{value}"{sel}>{value}</option>')
    return "\n".join(options)





# show the new or edit form
def form_page(data, errors=None,  rid=None, status=200):
    editing = rid is  not None
    errors_html =    ""
    if errors:
        items = "\n".join(f"<li>{html.escape(error)}</li>"  for error in errors)
        errors_html = fill("errors.html", safe={"items": items})
    if editing:
        title = "Edit request"
        heading = f"Edit request #{rid}"
        action = f"/requests/{rid}/edit"
        button_text = "Save changes"
        cancel_url   = f"/requests/{rid}"
    else:
        title =   heading = "Ask for help"
        action  = "/requests"
        button_text =    "Post request"
        cancel_url = "/requests"
    safe = {
        "errors": errors_html,
        "skill_options": options(SKILLS, data["skill"]),
        "status_options": options(STATUSES,   data["status"]),
    }
    return    page(title, "form.html", status, safe,
                heading=heading,    action=action, button_text=button_text,
                cancel_url=cancel_url, title=data["title"],
                description=data["description"], display_name=data["display_name"],
                content_link=data["content_link"] or "")


# pages etc

# start at the request board
def home():
    return    redirect("/requests")




# show the about page
def about():
    return page("About",   "about.html")
# get requests, newest first
def  all_rows():
    return query(
        "SELECT id, title, description, display_name, skill, status "
        "FROM help_requests ORDER BY id DESC")




# same requests, no outfit
# send the requests as json
def json_list():
    body   = json.dumps([dict(row)    for row in all_rows()], ensure_ascii=False)
    return 200, {"Content-Type": "application/json; charset=utf-8",
                 "Cache-Control": "no-store"}, body.encode("utf-8")



# the group chat has become a website
# make the cards on the server
def board():
    rows =    all_rows()
    if   not rows:
        empty = '<p class="empty">No requests yet. Be the first to ask for help!</p>'
        return    page("Requests", "list.html", safe={"cards": empty})
    cards = []

    for row in  rows:
        cards.append(fill("card.html", id=row["id"], title=row["title"],
                            skill=row["skill"], status=row["status"],
                            status_class=status_css(row["status"]),
                            display_name=row["display_name"],
                            card_class="done-card" if    row["status"] ==   "Done" else "",
                            description_preview=(row["description"][:177].rstrip()  + "..."
                                                 if len(row["description"]) > 180 else row["description"]),
                            author_initial=row["display_name"][:1].upper()))
    cards_html   = '<ul class="cards">\n' + "\n".join(cards) +    "\n</ul>"
    return page("Requests", "list.html", safe={"cards": cards_html})


# start with an empty form
def   new():
    empty = {"title": "", "description":   "", "display_name": "", "skill": "",
             "content_link": "",   "status": "Open"}
    return form_page(empty)
#create request
# another side quest has entered the chat
# save a new request
def   add(form):
    data, errors    = check(form)
    if errors:
        return form_page(data, errors, status=400)
    c  = db()
    cur = c.execute(
        "INSERT INTO help_requests (title, description, display_name, skill, content_link, status) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (data["title"], data["description"], data["display_name"], data["skill"],
         data["content_link"], data["status"]),
    )
    c.commit()
    nid  = cur.lastrowid
    c.close()
    return redirect(f"/requests/{nid}")

#find request


# show one request
def show(rid):
    row =    find(rid)
    if row is None:
        return missing()
    link_html =   ""
    if row["content_link"]:
        link = html.escape(row["content_link"])
        link_html = f'<p>Content link: <a href="{link}" rel="noopener nofollow">{link}</a></p>'
    return page(row["title"],   "detail.html", safe={"link": link_html},
                id=row["id"], title=row["title"],    skill=row["skill"],
                status=row["status"],    status_class=status_css(row["status"]),
                display_name=row["display_name"], description=row["description"])
#edit request



# load a request into the form
def    edit(rid):
    row = find(rid)
    if    row is None:
        return missing()
    return form_page(row, rid=rid)


# we all deserve an edit button
# save the edits
def save(rid, form):
    if find(rid) is None:
        return missing()
    data, errors = check(form)

    if errors:
        return form_page(data, errors,  rid, status=400)
    query(
        "UPDATE help_requests SET title = ?, description = ?, display_name = ?, skill = ?, "
        "content_link = ?, status = ? WHERE id = ?",
        (data["title"], data["description"], data["display_name"], data["skill"],
         data["content_link"], data["status"], rid))
    return redirect(f"/requests/{rid}")


# are you sure or just hungry
# ask before deleting
def    ask_delete(rid):# shows a question
    row =  find(rid)
    if row is None:
        return missing()
    return page("Delete request", "delete.html",   id=row["id"], title=row["title"])
# gone. unlike my browser tabs
# remove one request
def delete(rid):
    if    find(rid) is   None:
        return  missing()
    query("DELETE FROM help_requests WHERE id = ?", (rid,))
    return redirect("/requests")




# send css or javascript
def   file_data(filename):# send a file from static
    if filename    not in os.listdir(FILES):
        return missing()
    with open(os.path.join(FILES, filename), "rb") as file:
        body =  file.read()
    mime = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    return 200, {"Content-Type": mime},  body


# routing



# you go here, you go there, everybody gets a route
# pick the function for this url
def go(method, path, form):
    # rid is the request number in the url
    parts = path.split("/")
    rid = None
    if    len(parts) in   (3, 4)  and parts[1]    == "requests" and parts[2].isdigit():
        rid    = int(parts[2])
        route  = "/requests/<id>" + path[len("/requests/" + parts[2]):]
    elif len(parts) == 3   and parts[1]  == "static":
        route = "/static/<file>"
    else:
        route  = path

    if route == "/":
        if method ==  "GET":
            return    home()
    elif route == "/about":
        if method    == "GET":
            return about()
    elif route ==    "/api/requests":
        if   method == "GET":
            return json_list()
    elif route   == "/requests":
        if method == "GET":
            return board()
        if method  == "POST":
            return add(form)
    elif route  == "/requests/new":
        if method == "GET":
            return new()
    elif    route == "/requests/<id>":
        if method == "GET":
            return show(rid)
    elif route == "/requests/<id>/edit":
        if method    == "GET":
            return edit(rid)
        if method ==    "POST":
            return   save(rid, form)
    elif    route == "/requests/<id>/delete":
        if method == "GET":

            return ask_delete(rid)
        if method == "POST":
            return delete(rid)
    elif route == "/static/<file>":
        if method ==    "GET":
            return   file_data(parts[2])
    else:
        return   missing()
    return 405, {"Content-Type": "text/plain; charset=utf-8"}, b"Method Not Allowed"




# trying to hold this whole thing together
# handle the request and catch database errors
def  reply(method, path, form):
    try:
        return go(method,    path, form)
    except sqlite3.Error  as error:
        print("Database error:", error)
        if path ==  "/api/requests":
            return    (500, {"Content-Type": "application/json; charset=utf-8",
                          "Cache-Control": "no-store"},
                    b'{"error":"Could not load requests."}')
        return   oops("Database problem",
                          "Something went wrong with the database. Please try again later.", 500)


# the web server things here. yes this is the whole server
# read the browser request and send back the result
class Web(BaseHTTPRequestHandler):
    def    do_GET(self):
        self.send("GET")
    def do_HEAD(self):
        self.send("HEAD")
    def do_POST(self):
        self.send("POST")
    def send(self, method):
        path = unquote(urlsplit(self.path).path)
        form = {}
        if method == "POST":
            size =  int(self.headers.get("Content-Length",   0))
            body  = self.rfile.read(size).decode("utf-8", errors="replace")
            form    = {key: values[0] for key, values in parse_qs(body, keep_blank_values=True).items()}
        status,    headers, content = reply("GET" if method ==  "HEAD" else method, path, form)
        self.send_response(status)
        for name, value    in headers.items():
            self.send_header(name,    value)
        self.send_header("Content-Length",  str(len(content)))
        self.end_headers()
        if method != "HEAD":

            self.wfile.write(content)

# start the server when this file is run
if __name__ == "__main__":
    setup()
    server = ThreadingHTTPServer((HOST, PORT), Web)
    print(f"Running on http://{HOST}:{PORT} (press Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
