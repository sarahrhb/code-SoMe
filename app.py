# CODE Creator Board
# A small Flask app where creators can ask for help (editing, filming, design...).
# Data is saved in a SQLite database. Pages are made with Jinja templates.

import sqlite3
from flask import Flask, render_template, request, redirect, url_for, abort

app = Flask(__name__)

DATABASE = "board.db"

SKILLS = ["Editing", "Filming", "Design", "Copywriting", "Feedback", "Other"]
STATUSES = ["Open", "In progress", "Done"]


def get_db():
    # open a connection to the database
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # so I can use row["title"]
    return conn


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
             "I filmed a short reel about my startup but the cuts feel slow. "
             "Looking for someone to tighten it. Peer exchange: I can help with copywriting in return.",
             "Mila (demo)", "Editing", "https://example.com/my-reel", "Open"),
            ("Need someone to film a product demo",
             "Thursday afternoon at the CODE campus, about 1 hour. Phone camera is fine.",
             "Jonas (demo)", "Filming", "", "In progress"),
            ("Feedback on my new logo",
             "I made three logo ideas. Which one is the clearest? Short feedback is enough.",
             "Ava (demo)", "Feedback", "https://example.com/logos", "Done"),
        ]
        conn.executemany(
            "INSERT INTO help_requests (title, description, display_name, skill, content_link, status) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            examples,
        )
    conn.commit()
    conn.close()


def get_request_or_404(request_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM help_requests WHERE id = ?", (request_id,)).fetchone()
    conn.close()
    if row is None:
        abort(404)
    return row


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
    if data["title"] == "":
        errors.append("Please write a title.")
    if len(data["title"]) > 100:
        errors.append("The title can be at most 100 characters.")
    if data["description"] == "":
        errors.append("Please write a description.")
    if data["display_name"] == "":
        errors.append("Please write a display name.")
    if data["skill"] not in SKILLS:
        errors.append("Please choose a skill from the list.")
    if data["status"] not in STATUSES:
        errors.append("Please choose a status from the list.")
    link = data["content_link"]
    if link != "" and not (link.startswith("http://") or link.startswith("https://")):
        errors.append("The link must start with http:// or https://")
    return data, errors


@app.route("/")
def home():
    return redirect(url_for("list_requests"))


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/requests")
def list_requests():
    conn = get_db()
    rows = conn.execute("SELECT * FROM help_requests ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("list.html", requests=rows)


@app.route("/requests/new")
def new_request():
    empty = {"title": "", "description": "", "display_name": "", "skill": "",
             "content_link": "", "status": "Open"}
    return render_template("form.html", data=empty, errors=[], editing=False,
                           skills=SKILLS, statuses=STATUSES)


@app.route("/requests", methods=["POST"])
def create_request():
    data, errors = check_form(request.form)
    if errors:
        return render_template("form.html", data=data, errors=errors, editing=False,
                               skills=SKILLS, statuses=STATUSES), 400
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
    return redirect(url_for("show_request", request_id=new_id))


# dynamic route: the same function shows a different request for each id
@app.route("/requests/<int:request_id>")
def show_request(request_id):
    row = get_request_or_404(request_id)
    return render_template("detail.html", req=row)


@app.route("/requests/<int:request_id>/edit")
def edit_request(request_id):
    row = get_request_or_404(request_id)
    return render_template("form.html", data=row, errors=[], editing=True,
                           request_id=request_id, skills=SKILLS, statuses=STATUSES)


@app.route("/requests/<int:request_id>/edit", methods=["POST"])
def update_request(request_id):
    get_request_or_404(request_id)
    data, errors = check_form(request.form)
    if errors:
        return render_template("form.html", data=data, errors=errors, editing=True,
                               request_id=request_id, skills=SKILLS, statuses=STATUSES), 400
    conn = get_db()
    conn.execute(
        "UPDATE help_requests SET title = ?, description = ?, display_name = ?, skill = ?, "
        "content_link = ?, status = ? WHERE id = ?",
        (data["title"], data["description"], data["display_name"], data["skill"],
         data["content_link"], data["status"], request_id),
    )
    conn.commit()
    conn.close()
    return redirect(url_for("show_request", request_id=request_id))


@app.route("/requests/<int:request_id>/delete")
def confirm_delete(request_id):
    # only shows a question, nothing is deleted here
    row = get_request_or_404(request_id)
    return render_template("delete.html", req=row)


@app.route("/requests/<int:request_id>/delete", methods=["POST"])
def delete_request(request_id):
    get_request_or_404(request_id)
    conn = get_db()
    conn.execute("DELETE FROM help_requests WHERE id = ?", (request_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("list_requests"))


@app.errorhandler(404)
def not_found(error):
    return render_template("error.html", title="Page not found",
                           message="This page or request does not exist (maybe it was deleted)."), 404


@app.errorhandler(sqlite3.Error)
def database_error(error):
    print("Database error:", error)
    return render_template("error.html", title="Database problem",
                           message="Something went wrong with the database. Please try again later."), 500


init_db()

if __name__ == "__main__":
    # port 5001 because macOS uses port 5000 for AirPlay
    app.run(debug=True, port=5001)
