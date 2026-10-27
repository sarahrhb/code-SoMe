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

- Python 3, standard library only (nothing to install with pip)
- `http.server` (the web server and routes)
- HTML templates in `templates/` with `$placeholders` that Python fills in (`string.Template`).
  Everything users type is escaped with `html.escape` before it goes into a page.
- SQLite (database, one file called `board.db`)
- Handwritten CSS, no framework

## How to start it

You need Python 3. There is nothing to install.

```bash
python3 app.py
```

Then open http://localhost:5001 in your browser.

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

- No login. Anyone can edit or delete any request.
- No protection against fake form posts from other websites (CSRF).
- Not deployed.
