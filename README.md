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
│   ├── main.py        # FastAPI app: routes and helper functions
│   └── db.py          # MySQL connection + query helper
├── .env.example       # Template for your database settings
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

> Never commit `.env`. It is already listed in `.gitignore`.

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

### Views the code expects

`v_api_profile`, `v_api_summary`, `v_api_experience`, `v_api_projects`, `v_api_skills`, `v_api_education`, `v_api_awards`

### Security note for students

Look at `list_from_view` in `main.py`. The column and view names are fixed text written in the code, while every value from the user goes through `%s` placeholders in `params`. This is a **parameterized query**, and it is what stops SQL injection. Never build SQL by pasting user input into a string with f-strings.

## Exercises

1. Add a `GET /api/summary` endpoint that returns the row from `v_api_summary`.
2. Add `GET /api/education` and `GET /api/awards`.
3. Return a proper `404` when a filter matches nothing (`HTTPException` is already imported).
4. Add a `GET /api/resume` route that returns the whole resume (a `build_resume` helper already exists in `main.py`).
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
