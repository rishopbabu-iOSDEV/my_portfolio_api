import json
from datetime import date, datetime
from typing import Literal
from fastapi import FastAPI, HTTPException, Query, Response
from db import connect, fetch_all

app = FastAPI(
    title="Future Portfolio API",
    version="1.0",
    description="Ananya Rao - Future Portfolio API",
)

Category = Literal["Company", "Industry", "Community"]

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def list_from_view(response: Response, view: str, where: list[str], params: list,
                   order: str, page: int, limit: int):
    """One page of rows from a view, with X-Total-Count for the whole filter.
    view, where and order are fixed text from this file; params carries every value.
    """
    where_sql = f" WHERE {' AND '.join(where)}" if where else ""
    with connect() as conn:
        total = fetch_all(conn, f"SELECT COUNT(*) AS total FROM {view}{where_sql}", params)[0]["total"]
        rows = fetch_all(
            conn,
            f"SELECT * FROM {view}{where_sql} ORDER BY {order} LIMIT %s OFFSET %s",
            [*params, limit, (page - 1) * limit],
        )
    response.headers["X-Total-Count"] = str(total)
    return rows


def parse_skills(rows):
    """The skills column is JSON text (JSON_ARRAYAGG); turn it into a list."""
    for row in rows:
        row["skills"] = json.loads(row["skills"]) if row["skills"] else []
    return rows


def build_resume(conn):
    """The whole resume.json document (contract version 2), from the seven views.
    The same function as scripts/db_to_json.py (Module 5), served live.
    """
    projects = parse_skills(fetch_all(conn, "SELECT * FROM v_api_projects ORDER BY project_id"))
    return {
        "generated_at": date.today().isoformat(),
        "profile":    fetch_all(conn, "SELECT * FROM v_api_profile")[0],
        "summary":    fetch_all(conn, "SELECT * FROM v_api_summary")[0],
        "experience": fetch_all(conn, "SELECT * FROM v_api_experience ORDER BY start_date DESC"),
        "projects":   projects,
        "skills":     fetch_all(conn, "SELECT * FROM v_api_skills ORDER BY project_count DESC, skill"),
        "education":  fetch_all(conn, "SELECT * FROM v_api_education ORDER BY start_year DESC"),
        "awards":     fetch_all(conn, "SELECT * FROM v_api_awards ORDER BY year DESC, id"),
    }

# ---------------------------------------------------------------------------
# hello
# ---------------------------------------------------------------------------

@app.get("/api/hello")
def hello():
    return {"message": "Hello, World!"}

# ---------------------------------------------------------------------------
# get_profile
# ---------------------------------------------------------------------------

@app.get("/api/profile", tags=["Profile"])
def get_profile():
    with connect() as conn:
        return fetch_all(conn, "SELECT * FROM v_api_profile")[0]

# ---------------------------------------------------------------------------
# list_projects
# ---------------------------------------------------------------------------

@app.get("/api/projects", tags=["Projects"])
def list_projects(response: Response, 
                  skill: str | None = Query(None, min_length=1, max_length=100),
                  company: str | None = Query(None, min_length=1, max_length=100),
                  page: int = Query(1, ge=1),
                  limit: int = Query(10, ge=1, le=50)):
    """Project-role pairs with their skills; filter by skill, company or text in the name.
    """
    where, params = [], []
    if skill is not None:
        where.append("JSON_CONTAINS(skills, JSON_QUOTE(%s))")
        params.append(skill)
    if company is not None:
        where.append("company = %s")
        params.append(company)
    rows = list_from_view(response, "v_api_projects", where, params, "project_id, role", page, limit)
    return parse_skills(rows)