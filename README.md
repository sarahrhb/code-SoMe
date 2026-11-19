# CODE SoMe incubator

A small website where CODE students can ask each other for help with editing,
filming, design, copywriting, or feedback.

## Website

[Open the live board](https://some.code-alumni.de/requests)

Pushing to GitHub does not update the website automatically. Deploy the new
version to the server after pushing.

## Run locally

Python 3.9 or newer is required. There are no Python package dependencies.

```sh
HOST=127.0.0.1 PORT=5001 python3 app.py
```

Open http://127.0.0.1:5001/requests. The SQLite database is `board.db` in the
working directory. Run the app from its project directory.

`PORT` defaults to `5001`; `HOST` defaults to `0.0.0.0`. Behind a reverse proxy,
set `HOST=127.0.0.1` and use the port configured in the proxy.

## Use the board

Browse requests, post a request with your display name, and open a request to
edit it, change its status, or delete it. This simplified version does not have
accounts, applications, or notifications. Anyone can edit or delete a request.
Do not post private information.

## Server-side and client-side rendering

`GET /requests` renders request cards on the server using HTML templates.
The board stays usable without JavaScript.

`GET /api/requests` returns a JSON array with each request's id, title,
description, display name, skill, and status, newest first.
`static/board.js` fetches this route, builds cards with `createElement` and
`textContent`, and filters requests in the browser by search text, skill, and
status. Filters can be combined and cleared without reloading the page.
If loading fails, the server-rendered cards remain visible.

## Checks

```sh
python3 -m unittest discover -s tests -v
node --test tests/board.test.js
```

The JavaScript tests use a small DOM test double and require Node.js 18 or newer.

## Deployment

Use the same commit on `main` and on the server. Upload
`app.py`, `static/`, and `templates/` together. Keep `board.db` on the server and
back up the current app and database before switching versions. Restart the
service after replacing the source files.

The existing server uses `/opt/code-some` and the `codesome` systemd service.
Its working directory must be `/opt/code-some`; its Python entrypoint must be
`/opt/code-some/app.py`. Set `PORT` to the reverse proxy's upstream port.
Deploying this version retains the older account tables but does not use them.
