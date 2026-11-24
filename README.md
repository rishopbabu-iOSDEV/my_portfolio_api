# Future Portfolio API

A small REST API that serves a personal portfolio (profile, projects, skills, experience, education, awards) straight from a MySQL database. Built with **FastAPI** and **mysql-connector-python** as a teaching project for the API / Web Data course.

## What you will learn

- How a REST API sits between a database and a client (browser, app, script)
- Defining routes with FastAPI (`@app.get`)
- Validating query parameters (`Query(..., ge=1, le=50)`)
- Filtering and pagination with SQL (`WHERE`, `LIMIT`, `OFFSET`)
- Why we query **views** instead of raw tables
- Preventing SQL injection with **parameterized queries**
- Keeping secrets out of code with `.env` files
- Using the auto-generated interactive docs (Swagger UI)

## Project structure

```
my_portfolio_api/
├── api/
│   ├── main.py        # FastAPI app: routes, helpers, Swagger documentation
│   └── db.py          # MySQL connection + query helper
├── .env.example       # Template for your database settings (safe to commit)
├── .env               # YOUR real settings (you create it; git ignores it)
├── .gitignore         # Files git must never track
├── requirements.txt   # Pinned Python dependencies
└── README.md
```

## Prerequisites

- Python 3.10 or newer (the code uses `str | None` type syntax)
- MySQL 8+ running locally (or reachable over the network)
- A database named `future_portfolio_db` containing the seven API views listed below (created in the course's database module)

## Setup

**1. Create and activate a virtual environment**

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
```

**2. Install dependencies**

```bash
pip install -r requirements.txt
```

**3. Configure the database connection**

Copy the template and fill in your own values:

```bash
cp .env.example .env
```

```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=your_mysql_user
DB_PASSWORD=your_mysql_password
DB_NAME=future_portfolio_db
```

> Never commit `.env`. It is already listed in `.gitignore` (see [Git and ignored files](#git-and-ignored-files)).

**4. Run the server**

`main.py` imports `db` directly, so start the server from inside the `api/` folder:

```bash
cd api
uvicorn main:app --reload
```

The API is now at <http://127.0.0.1:8000>.

## Try it

| What | URL |
|------|-----|
| Interactive docs (Swagger UI) | <http://127.0.0.1:8000/docs> |
| Alternative docs (ReDoc) | <http://127.0.0.1:8000/redoc> |
| Hello world | <http://127.0.0.1:8000/api/hello> |

Or from the terminal:

```bash
curl http://127.0.0.1:8000/api/hello
curl http://127.0.0.1:8000/api/profile
curl "http://127.0.0.1:8000/api/projects?skill=Python&limit=5"
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/hello` | Health check, returns `{"message": "Hello, World!"}` |
| GET | `/api/profile` | The portfolio owner's profile |
| GET | `/api/projects` | Paginated list of projects with their skills |
| GET | `/api/summary` | Professional summary |
| GET | `/api/experience` | Work history (filter by `company`, paginated) |
| GET | `/api/skills` | Skills with project counts (filter by `evidenced`, `category`) |
| GET | `/api/education` | Education history (paginated) |
| GET | `/api/resume` | Whole resume as one JSON document |

### List endpoints share the same paging options

`/api/projects`, `/api/experience`, `/api/skills` and `/api/education` all accept `page` (default 1) and `limit` (default 10, max 50) and return the total match count in the `X-Total-Count` header.

| Endpoint | Extra filters |
|----------|---------------|
| `/api/projects` | `skill`, `company` |
| `/api/experience` | `company` |
| `/api/skills` | `evidenced` (true/false), `category` (`Company`, `Industry` or `Community`) |
| `/api/education` | none |

### `GET /api/projects`

| Query parameter | Type | Default | Notes |
|-----------------|------|---------|-------|
| `skill` | string | none | Only projects that use this skill |
| `company` | string | none | Exact company name match |
| `page` | int | 1 | Must be 1 or more |
| `limit` | int | 10 | Between 1 and 50 |

The response header `X-Total-Count` holds the total number of matching rows, so a client can work out how many pages exist.

## How it works

```
Client ──HTTP──▶ FastAPI route ──SQL──▶ MySQL view ──▶ rows ──JSON──▶ Client
```

1. **`db.py`** reads credentials from `.env` and opens a MySQL connection (`connect`). `fetch_all` runs a query and returns rows as dictionaries.
2. **`main.py`** defines the routes. Each route opens a connection, queries a view, and returns the result; FastAPI turns Python dicts and lists into JSON.
3. **Views** (`v_api_*`) are saved SELECT statements in the database. They give the API a stable shape, so the API code doesn't need to know how the underlying tables are joined.
4. **`list_from_view`** is a shared helper that adds filtering, counting and pagination to any view.

### How the code is documented

Every function and keyword in `main.py` and `db.py` is explained in plain language using three questions: **What** does it do, **Why** is it there, **How** does it work. Read the files top to bottom like a lesson.

The same text feeds **Swagger** (`/docs`): each route has a summary, description, documented responses, and every query parameter has help text and examples. Change the code's documentation and the API docs update by themselves.

### Views the code expects

`v_api_profile`, `v_api_summary`, `v_api_experience`, `v_api_projects`, `v_api_skills`, `v_api_education`, `v_api_awards`

### Security note for students

Look at `list_from_view` in `main.py`. The column and view names are fixed text written in the code, while every value from the user goes through `%s` placeholders in `params`. This is a **parameterized query**, and it is what stops SQL injection. Never build SQL by pasting user input into a string with f-strings.

## Git and ignored files

The `.gitignore` keeps junk and secrets out of the repository:

| Ignored | Why |
|---------|-----|
| `.env`, `.env.*`, keys | Passwords and secrets must never reach GitHub (`.env.example` is the one exception: it is a safe template) |
| `__pycache__/`, `*.pyc`, tool caches | Python regenerates these automatically; they differ on every computer |
| `.venv/`, `venv/` | Each person creates their own virtual environment |
| `build/`, `dist/`, `*.egg-info/` | Build output |
| `.coverage`, `htmlcov/`, `.pytest_cache/` | Test artefacts |
| `*.log`, `*.tmp`, `*.bak`, `*.swp` | Temporary files |
| `.vscode/`, `.idea/` | Personal editor settings |
| `.DS_Store`, `Thumbs.db` | Operating-system clutter |
| `node_modules/` | In case a front end is added later |

If a file was committed *before* being ignored, ignoring it is not enough. Stop tracking it with:

```bash
git rm -r --cached api/__pycache__
```

## Exercises

1. Add `GET /api/awards` (the view `v_api_awards` already exists; copy the pattern of `list_education`).
2. Add a `category` filter to `/api/projects` using the `Category` type.
3. Return a proper `404` when a filter matches nothing (`HTTPException` is already imported).
4. Add a `404` response to the Swagger docs of `/api/profile` using `responses={404: {...}}`.
5. Add a `search` query parameter that matches text in the project name (use `LIKE %s`).
6. Write a small Python script with `requests` that calls your API and prints each project name.

## Troubleshooting

| Problem | Likely fix |
|---------|-----------|
| `ModuleNotFoundError: No module named 'db'` | You started uvicorn from the project root. `cd api` first. |
| `Access denied for user` | Check `DB_USER` / `DB_PASSWORD` in `.env`. |
| `Can't connect to MySQL server` | Make sure MySQL is running and `DB_HOST` / `DB_PORT` are right. |
| `Table 'v_api_...' doesn't exist` | Run the course SQL scripts that create the views in `future_portfolio_db`. |
| Changes not showing up | Start uvicorn with `--reload`. |

## Tech stack

- [FastAPI](https://fastapi.tiangolo.com/) - web framework
- [Uvicorn](https://www.uvicorn.org/) - ASGI server
- [mysql-connector-python](https://dev.mysql.com/doc/connector-python/en/) - database driver
- [python-dotenv](https://github.com/theskumar/python-dotenv) - loads `.env`
