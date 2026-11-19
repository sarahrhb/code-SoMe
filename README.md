# CODE SoMe incubator

A small website where CODE students can ask each other for help with editing,
filming, design, copywriting, or feedback.

## Website

[Open the live board](https://some.code-alumni.de/requests)


## Run locally

Python 3.9 or newer is required.

```sh
HOST=127.0.0.1 PORT=5001 python3 app.py
```

Open http://127.0.0.1:5001/requests. The SQLite database is `board.db` in the
working directory. Run the app from its project directory.

## Use the board

Find requests, post a request with your name and edit it, change its status, or delete it. 
Anyone can edit or delete a request.

## Server-side and client-side rendering

`GET /requests` renders request cards on the server using HTML templates.

`GET /api/requests` returns a JSON with each request's id, title,
description, display name, skill, and status, newest first.
`static/board.js` fetches this route, builds cards with `createElement` and
`textContent`, and filters requests in the browser by search text, skill, and
status.

## Checks

```sh
python3 -m unittest discover -s tests -v
node --test tests/board.test.js
```

## Deployment

Use the same commit on `main` and on the server. Upload
`app.py`, `static/`, and `templates/` together. Keep `board.db` on the server and
back up the current app and database before switching versions. Restart the
service after replacing the source files.

The existing server uses `/opt/code-some` and the `codesome` systemd service.
Its working directory must be `/opt/code-some`; its Python entrypoint must be
`/opt/code-some/app.py`. Set `PORT` to the reverse proxy's upstream port.
