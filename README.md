# CODE Creator Board

A small website where CODE students can ask each other for help creating content:
editing, filming, design, copywriting or feedback.

## What you can do

- See all help requests
- Open one request
- Create a new request
- Edit a request
- Delete a request (you have to confirm first)

## Tech

- Python + Flask (backend and routes)
- Jinja (template language, comes with Flask)
- SQLite (database, one file called `board.db`)
- Handwritten CSS, no framework

## How to start it

You need Python 3.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Then open http://localhost:5001 in your browser.

(I use port 5001 because on a Mac port 5000 is used by AirPlay.)

## Database

The database file `board.db` is created automatically the first time the app starts.
If it is empty, three example requests are added.

To start again with fresh example data, stop the app, delete `board.db` and start it again.

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

`/requests/<id>` is the dynamic route: one function reads the id from the URL
and loads that request from the database. So `/requests/1` and `/requests/2` show different content.
If the id does not exist, you get a "Page not found" page.

## Responsive design

The CSS is mobile first and has two breakpoints:

- **640px**: navigation goes next to the logo, cards show in 2 columns
- **1000px**: cards show in 3 columns, bigger headings

## Safety

- All SQL uses `?` placeholders (no user text is put directly into SQL)
- Jinja escapes user text automatically, so HTML in a title is shown as text
- The form is checked on the server: empty fields, unknown skill/status and bad links are rejected

## Known limits

- No login. Anyone can edit or delete any request.
- No protection against fake form posts from other websites (CSRF).
- Not deployed, it only runs on your own computer.
- Replies, challenges and shared content are ideas for later.

Before real CODE members use it, it would need login, owner permissions, moderation,
privacy information, HTTPS, backups and approval from the organisers.
