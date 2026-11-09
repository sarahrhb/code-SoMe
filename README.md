# CODE Creator Board

A small website where CODE students can ask each other for help creating content:
editing, filming, design, copywriting or feedback.

The website is meant to be a focused place for these requests. Slack already has a lot
of activity, and adding more requests there can make them harder to find. A request
stays on this board with a visible status, so people can follow whether it is open,
being worked on, or done.

## What you can do

- See all help requests
- Search the list in the browser without reloading the page
- Open one request
- Create a new request
- Edit a request
- Delete a request (you have to confirm first)
- Keep the request status visible for follow-through

## Tech

- Python 3, standard library only (nothing to install with pip)
- `http.server` (the web server and routes)
- HTML templates in `templates/` with `$placeholders` that Python fills in (`string.Template`).
  Everything users type is escaped with `html.escape` before it goes into a page.
- SQLite (database, saved in `board.db` next to `app.py`)
- A small browser-side JavaScript file filters the requests already on the page
- Handwritten CSS, no framework; one shared password protects changes

There is no ORM. An ORM is a tool that lets code work with database rows as Python
objects. This project uses SQLite directly so the database steps stay visible and
simple. The module objective is to store and change data in a database; it does not
require an ORM specifically.

## How to start it

You need Python 3.

```bash
export BOARD_WRITE_PASSWORD='choose-a-private-password'
python3 app.py
```

Then open http://localhost:5001 in your browser.
When you post, edit, or delete a request, the browser asks for the shared password.
Use `community` as the username. If `BOARD_WRITE_PASSWORD` is not set, changes are
disabled. Do not put the password in this repository.

## How the protection works

- The shared password is checked before a form can change the database.
- A form must come from this same website. This is a simple check against another
  website secretly submitting a form for you.
- User text is escaped before it is shown, and database values are sent separately
  from SQL instructions.

This is a beginner-level protection, not a complete account system. Everyone who
can edit uses the same password, and everyone can read the requests. The same-site
check is a basic safeguard, not a replacement for a full CSRF token. For a public
server, use HTTPS; the built-in Python server by itself does not provide HTTPS.

## Keeping the data

The database file is `board.db` next to `app.py`. It is ignored by Git so personal
request data is not pushed with the code. Back up this file before moving the project
or updating a server. For a simple manual backup, stop the app and copy `board.db` to
a safe location. To restore it, stop the app and put the backup beside `app.py` with
the name `board.db`.

The project is not deployed yet. For a public deployment, keep the Python app behind
an HTTPS reverse proxy and use persistent server storage for `board.db`; do not expose
the built-in Python server directly to the internet.

## Data model: HelpRequest

| Field | Meaning |
| --- | --- |
| id | number, made by the database |
| title | short title of the request |
| description | what you need, when, and if it is paid or a peer exchange |
| display_name | your name (fictional in the demo) |
| skill | Editing, Filming, Design, Copywriting, Feedback or Other |
| content_link | optional link, must start with http:// or https:// |
| status | Open, In progress or Done |

## Routes

| Method | Route | What it does |
| --- | --- | --- |
| GET | / | goes to /requests |
| GET | /requests | list of all requests |
| GET | /requests/&lt;id&gt; | one request (dynamic route) |
| GET | /about | about page |
| GET | /requests/new | form to create a request |
| POST | /requests | saves a new request |
| GET | /requests/&lt;id&gt;/edit | edit form with the current values |
| POST | /requests/&lt;id&gt;/edit | saves the changes (same id) |
| GET | /requests/&lt;id&gt;/delete | asks "are you sure?" |
| POST | /requests/&lt;id&gt;/delete | really deletes the request |


## Known limits

- One shared password rather than separate user accounts or permissions.
- The browser-side feature only filters the list; it does not create or save records.
- The protection is intentionally small and still needs review before public use.
- Not deployed.
