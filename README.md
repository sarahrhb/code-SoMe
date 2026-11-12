# CODE Creator Board

A website where CODE students can ask each other for help creating content:
editing, filming, design, copywriting or feedback.

## !! This is a part of the SoMe incubator project in CODE - Initiated by CAF i.V. !!

The website is meant to be a place for these requests. Slack is so crowded, and adding more channels there will make students hate it even more. A request stays on this board with a visible status, so people can follow whether it is open, being worked on, or done.

## What you can do

- See all help requests
- Search the list in the browser without reloading the page
- Open one request
- Create a new request
- Edit a request
- Delete a request
- Keep the request status visible for follow-through

## Tech

- Python 3, standard library (nothing to install with pip)
- `http.server` (the web server and routes)
- HTML templates in `templates/` with `$placeholders` that Python fills in (`string.Template`).
  Everything users type is escaped with `html.escape` before it goes into a page.
- SQLite (database, saved in `board.db` next to `app.py`)
- A small browser-side JavaScript file filters the requests already on the page
- Handwritten CSS

This project uses SQLite. The module objective is to store and change data in a database; it does not require an ORM.

## How to start it

You need Python 3.

```bash
export SESSION_SECRET='choose-a-long-random-secret'
python3 app.py
```

Then open http://localhost:5001 in your browser.
To create an account, use an `@code.berlin` email address. Each account has its own
username and password.

## How the protection works

- Each account password is saved as a one-way hash, not as readable text.
- Only email addresses ending in `@code.berlin` are accepted during signup. The email
  address is stored for this check and is not shown publicly.
- A signed-in account can edit or delete only requests it created.
- Forms include a small check to help stop other websites from submitting changes.
- A form must come from this same website.
- User text is escaped before it is shown, and database values are sent separately
  from SQL instructions.

Everyone can read requests. Anyone who enters an `@code.berlin` address can create an
account, then edit or delete only their own requests. The email address is checked for
its domain, but the app does not confirm that the person owns that mailbox. The same-site
check and form token are basic safeguards. For a public server, use HTTPS; the built-in
Python server by itself does not provide HTTPS.

## Current demo deployment

The prototype is running over HTTPS at <https://some.code-alumni.de>. Caddy handles
HTTPS and forwards website traffic to the Python app, which listens only inside the
server. The app runs as a system service and saves `board.db` beside `app.py` so the
data remains after a restart. The temporary address
<https://code-some.167.233.155.151.sslip.io> also continues to work.

On the server, a long random `SESSION_SECRET` and `COOKIE_SECURE=1` are stored in
`/etc/codesome/board.env`. These values are private and are not in this repository.

Existing requests from before accounts were added stay visible, but have no owner, so
they cannot be edited or deleted through the website. New requests belong to the
account that created them.

## Data model: HelpRequest

| Field | Meaning |
| --- | --- |
| id | number, made by the database |
| title | short title of the request |
| description | what you need, when, and if it is paid or a peer exchange |
| display_name | account username shown on the request (demo requests may have fictional names) |
| skill | Editing, Filming, Design, Copywriting, Feedback or Other |
| content_link | optional link, must start with http:// or https:// |
| status | Open, In progress or Done |
| owner_id | account that created the request; old requests have no owner |

## Routes

| Method | Route | What it does |
| --- | --- | --- |
| GET | / | goes to /requests |
| GET | /requests | list of all requests |
| GET | /requests/&lt;id&gt; | one request (dynamic route) |
| GET | /about | about page |
| GET/POST | /login | sign in |
| GET/POST | /signup | create an account using a CODE email address |
| POST | /logout | sign out |
| GET | /requests/new | form to create a request |
| POST | /requests | saves a new request |
| GET | /requests/&lt;id&gt;/edit | edit form with the current values |
| POST | /requests/&lt;id&gt;/edit | saves the changes (same id) |
| GET | /requests/&lt;id&gt;/delete | asks "are you sure?" |
| POST | /requests/&lt;id&gt;/delete | really deletes the request |


## Known limits

- Everyone can read the requests; accounts only control who may change each request.
- Old requests have no account owner and are read-only.
- The browser-side feature only filters the list; it does not create or save records.
- The temporary `sslip.io` address remains available as a fallback.
- The email domain is checked, but the app does not send a confirmation email to prove
  that a person owns that mailbox.
