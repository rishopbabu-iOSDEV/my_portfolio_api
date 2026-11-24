"""
main.py - the "front desk" of the Future Portfolio API.

WHAT: Defines the web addresses (called routes or endpoints) that people can
      visit, like /api/profile or /api/projects, and what each one answers with.
WHY:  A database cannot be opened by a website or phone app directly. This file
      is the safe middleman: it receives a request, asks the database, and
      replies in JSON (a simple text format every programming language reads).
HOW:  Each route is a normal Python function with a "decorator" line above it
      (@app.get(...)) that says "run this function when someone visits this
      address". The function asks db.py for data and returns it.

The nice text in the interactive documentation page (http://127.0.0.1:8000/docs,
called Swagger) is generated FROM this file. So documenting the code here also
documents the API for everyone, and the two can never disagree.
"""

# ---------------------------------------------------------------------------
# IMPORTS  (an import = "borrow a ready-made tool someone else already built")
# ---------------------------------------------------------------------------

# WHAT: Python's built-in JSON tool.
# WHY:  MySQL sometimes gives us a list as plain TEXT like '["Python","SQL"]'.
# HOW:  json.loads(text) turns that text into a real Python list (see parse_skills).
import json

# WHAT: `date` gives today's date. `datetime` is date+time.
# WHY:  build_resume() stamps the document with today's date. `datetime` is
#       imported but not used yet (harmless; you may remove it).
# HOW:  date.today() returns today's date.
from datetime import date, datetime

# WHAT: `Literal` lets us say "the value must be exactly one of these words".
# WHY:  so people cannot ask for a category that does not exist.
# HOW:  see the `Category` line below.
from typing import Literal

# WHAT: four tools from FastAPI, the web framework that powers this API.
#   FastAPI       - the application itself (the "building" our routes live in).
#   HTTPException - a way to send an error such as "404 Not Found"
#                   (not used yet; it is needed for the README exercises).
#   Query         - describes an option typed in the address after a "?", such
#                   as ?limit=5, and checks that it is allowed.
#   Response      - the reply we are about to send; lets us attach extra
#                   information (headers) to it.
# WHY:  writing a web server from scratch would take thousands of lines.
# HOW:  each one is used below where it is introduced.
from fastapi import FastAPI, HTTPException, Query, Response

# WHAT: our own two helpers from db.py.
# WHY:  main.py should never deal with passwords or database plumbing.
# HOW:  connect() opens the database; fetch_all(conn, sql, values) runs a question.
from db import connect, fetch_all

# ---------------------------------------------------------------------------
# SWAGGER SECTIONS
# ---------------------------------------------------------------------------

# WHAT: a list of section names (tags) with a one-line explanation each.
# WHY:  the /docs page groups routes into sections; this gives each a friendly
#       description instead of only a name.
# HOW:  FastAPI(..., openapi_tags=tags_metadata) below hands this list over.
#       A route joins a section by writing tags=["Name"].
tags_metadata = [
    {"name": "Profile",    "description": "Who the portfolio belongs to."},
    {"name": "Summary",    "description": "The short professional summary."},
    {"name": "Projects",   "description": "Projects and the skills used, with filtering and paging."},
    {"name": "Experience", "description": "Work history, newest first."},
    {"name": "Skills",     "description": "Skills with the number of projects that prove them."},
    {"name": "Education",  "description": "Schools, degrees and dates."},
    {"name": "Resume",     "description": "Everything above combined in one JSON document."},
]

# WHAT: creates the application. `app` is the object the server runs.
# WHY:  every route must be attached to one application.
# HOW:  you start it with `uvicorn main:app` = "in file main.py, use the thing named app".
#   title        - big heading on the docs page.
#   version      - the API's version number; raise it when replies change shape.
#   description  - intro paragraph on the docs page (** ** makes bold).
#   openapi_tags - the section list defined above.
app = FastAPI(
    title="Future Portfolio API",
    version="1.0",
    description=(
        "Read-only REST API for a personal portfolio.\n\n"
        "Data comes from MySQL **views** (`v_api_*`). "
        "All endpoints use `GET` and return JSON.\n\n"
        "List endpoints accept `page` and `limit` and return the total number "
        "of matches in the `X-Total-Count` response header."
    ),
    openapi_tags=tags_metadata,
)

# WHAT: a type meaning "exactly one of these three words".
# WHY:  if someone asks for ?category=Banana, FastAPI refuses with a clear error
#       (code 422) and the docs page shows a dropdown with only valid choices.
# HOW:  used as the type of the `category` option in list_skills().
Category = Literal["Company", "Industry", "Community"]

# ---------------------------------------------------------------------------
# REUSABLE DOCUMENTATION SNIPPETS
# ---------------------------------------------------------------------------

# WHAT: documentation for the reply header "X-Total-Count".
# WHY:  a header is invisible in the response body, so we describe it or nobody
#       would know it exists.
# HOW:  plugged into LIST_RESPONSES below.
TOTAL_COUNT_HEADER = {
    "X-Total-Count": {
        "description": "Total rows matching the filters, across all pages.",
        "schema": {"type": "integer"},
    }
}

# WHAT: the possible replies shared by every "list" route (200 ok, 422 bad
#       input, 500 server problem).
# WHY:  write it once and reuse it, so all routes are documented the same way
#       and a fix is made in one place.
# HOW:  routes pass it as responses=LIST_RESPONSES.
LIST_RESPONSES = {
    200: {"description": "A page of rows.", "headers": TOTAL_COUNT_HEADER},
    422: {"description": "Validation error, e.g. page < 1 or limit > 50."},
    500: {"description": "Database unreachable or view missing."},
}

# ---------------------------------------------------------------------------
# HELPER FUNCTIONS
# These are normal functions used by the routes. They have no @app line, so
# nobody can visit them from a browser.
# ---------------------------------------------------------------------------

def list_from_view(response: Response, view: str, where: list[str], params: list,
                   order: str, page: int, limit: int):
    """Fetch ONE PAGE of rows from a view, and report how many rows exist in total.

    WHAT: like opening page 2 of a catalogue (10 items per page) after applying
          any filters, and also telling the caller the total item count.
    WHY:  four routes need exactly this. Writing it once avoids repeated code
          and mistakes. Paging stops us from sending thousands of rows at once.
    HOW:  1) glue the filters into a WHERE clause,
          2) ask the database "how many rows match in total?",
          3) ask for just this page's rows,
          4) put the total in the reply header X-Total-Count.

    Arguments:
        response - the reply we are building (so we can add the header).
        view     - which saved query (view) to read, e.g. "v_api_projects".
        where    - filter conditions, e.g. ["company = %s"]; empty = no filter.
        params   - the values that fill the %s blanks, in the same order.
        order    - how to sort, e.g. "start_date DESC" (newest first).
        page     - which page (1 = first).
        limit    - how many rows per page.

    SAFETY: view, where and order are pasted into the SQL text, which is only
    safe because they are written by us in this file, never typed by a visitor.
    Everything a visitor types travels in `params` (the %s blanks).
    """
    # Build the filter text. ' AND '.join(where) glues conditions with AND, so
    # ["a = %s", "b = %s"] becomes "a = %s AND b = %s".
    # `X if condition else Y` = pick X when the condition is true, otherwise Y.
    # With no filters we use "" because a lonely word WHERE is a SQL error.
    # The f before the quotes (f-string) lets us drop {variables} into the text.
    where_sql = f" WHERE {' AND '.join(where)}" if where else ""

    # `with connect() as conn:` opens the database and CLOSES it automatically
    # at the end of the block, even if an error happens. No leaks.
    with connect() as conn:
        # Question 1: how many rows match in total? COUNT(*) counts rows.
        # `[0]["total"]` = take the first (only) row and read its "total" value.
        total = fetch_all(conn, f"SELECT COUNT(*) AS total FROM {view}{where_sql}", params)[0]["total"]

        # Question 2: the rows for this page only.
        #   ORDER BY  - sort the rows (a fixed order keeps pages from overlapping).
        #   LIMIT n   - give at most n rows.
        #   OFFSET m  - skip the first m rows.
        # Skipping (page - 1) * limit rows is the page maths: page 1 skips 0,
        # page 2 skips 10 (if limit is 10), page 3 skips 20, and so on.
        # `[*params, limit, offset]` = the filter values, then the two paging values.
        rows = fetch_all(
            conn,
            f"SELECT * FROM {view}{where_sql} ORDER BY {order} LIMIT %s OFFSET %s",
            [*params, limit, (page - 1) * limit],
        )

    # Attach the total to the reply as a header. Headers must be text, so str().
    # WHY a header: the body stays a clean list, and clients can still learn
    # how many pages exist.
    response.headers["X-Total-Count"] = str(total)
    return rows


def parse_skills(rows):
    """Turn the `skills` text in each row into a real list.

    WHAT: '["Python","SQL"]' (text)  ->  ["Python", "SQL"] (a list).
    WHY:  the database packs the skills into one piece of text. If we sent it
          as-is, the client would receive a string inside the JSON instead of
          a proper list and would have to unpack it themselves.
    HOW:  loop over every row; run json.loads on its skills text.
    """
    # `for row in rows:` = repeat the indented lines once for each row.
    for row in rows:
        # A project with no skills has an empty value (None); json.loads(None)
        # would crash, so in that case we use an empty list [] instead.
        row["skills"] = json.loads(row["skills"]) if row["skills"] else []
    # Return the rows so callers can write parse_skills(fetch_all(...)) in one go.
    return rows


def build_resume(conn):
    """Assemble the WHOLE resume as one dictionary.

    WHAT: profile + summary + experience + projects + skills + education + awards
          together, plus today's date.
    WHY:  a client (for example a resume web page) can then make ONE request
          instead of seven.
    HOW:  run one query per section against its view and put each result
          under its own key. The same logic as the Module 5 script
          scripts/db_to_json.py, but live from the database.

    Argument:
        conn - an already-open database connection (the caller opens and closes it).
    """
    # Projects need the extra step of turning their skills text into a list.
    projects = parse_skills(fetch_all(conn, "SELECT * FROM v_api_projects ORDER BY project_id"))

    return {
        # date.today().isoformat() -> "2026-11-24". Tells readers how fresh the data is.
        "generated_at": date.today().isoformat(),

        # [0] = "take the first row". profile and summary have only one row each,
        # so we return that single row (a dictionary), not a list of one.
        "profile":    fetch_all(conn, "SELECT * FROM v_api_profile")[0],
        "summary":    fetch_all(conn, "SELECT * FROM v_api_summary")[0],

        # DESC = descending = newest first.
        "experience": fetch_all(conn, "SELECT * FROM v_api_experience ORDER BY start_date DESC"),
        "projects":   projects,

        # Most-used skills first; if tied, A-to-Z. A second sort column keeps
        # the order the same every time.
        "skills":     fetch_all(conn, "SELECT * FROM v_api_skills ORDER BY project_count DESC, skill"),
        "education":  fetch_all(conn, "SELECT * FROM v_api_education ORDER BY start_year DESC"),
        "awards":     fetch_all(conn, "SELECT * FROM v_api_awards ORDER BY year DESC, id"),
    }

# ---------------------------------------------------------------------------
# ROUTES (the web addresses people can visit)
#
# `@app.get("/path")` is a DECORATOR: a label on top of a function meaning
# "when someone sends a GET request to /path, run this function".
# GET is the HTTP word for "just read, change nothing" - what a browser does
# when you open a page. Every route here only reads, so all are GET.
# Whatever the function `return`s, FastAPI converts to JSON automatically.
#
# Swagger options used in the decorators:
#   summary     - short title shown in /docs.
#   description - longer explanation shown when you expand the route.
#   tags        - which /docs section the route belongs to.
#   responses   - the possible replies and what each means.
# ---------------------------------------------------------------------------

# ---- hello ----------------------------------------------------------------

@app.get(
    "/api/hello",
    summary="Health check",
    description="Returns a fixed greeting. Use it to confirm the server is running; it does not touch the database.",
    responses={200: {"description": "Server is up.",
                     "content": {"application/json": {"example": {"message": "Hello, World!"}}}}},
)
def hello():
    """Say hello.

    WHAT: replies {"message": "Hello, World!"}.
    WHY:  a quick test: if this works, the server is alive, even if the
          database is down.
    HOW:  it returns a dictionary; FastAPI turns it into JSON.
    """
    return {"message": "Hello, World!"}


# ---- get_profile ----------------------------------------------------------

@app.get(
    "/api/profile",
    tags=["Profile"],
    summary="Get the portfolio owner's profile",
    description="Returns the single row of the `v_api_profile` view: name, headline, contact details and similar top-level information.",
    responses={200: {"description": "The profile object (keys are the view's columns)."},
               500: {"description": "Database unreachable or view missing."}},
)
def get_profile():
    """Return the owner's profile.

    WHAT: one object with the person's name, headline, contact info, etc.
    WHY:  it is the "who is this?" card every portfolio page needs.
    HOW:  open the database, read the one row from the profile view, return it.
    """
    with connect() as conn:
        # [0] = first row. The view holds exactly one row, so we return it
        # directly (a dictionary) rather than a list containing one item.
        return fetch_all(conn, "SELECT * FROM v_api_profile")[0]


# ---- list_projects --------------------------------------------------------

@app.get(
    "/api/projects",
    tags=["Projects"],
    summary="List projects (filter + pagination)",
    description=(
        "Returns project/role pairs, each with a `skills` array.\n\n"
        "**Filtering:** `skill` and `company` can be combined (both must match).\n\n"
        "**Pagination:** use `page` and `limit`; the total is in the `X-Total-Count` header."
    ),
    responses=LIST_RESPONSES,
)
def list_projects(
        # `response` - FastAPI notices the type is Response and passes in the
        # reply we are building, so we can add a header. It is NOT something
        # the visitor types.
        response: Response,

        # The next four are OPTIONS the visitor may add after "?" in the
        # address, e.g. /api/projects?skill=Python&limit=5
        #
        # `str | None` = "text, or nothing at all". Query(None, ...) = the
        # option is optional and defaults to nothing.
        # min_length=1 rejects empty text; max_length=100 rejects giant text.
        # WHY: catching bad input early gives clear errors and protects the server.
        # description / examples = the help text shown in /docs.
        skill: str | None = Query(
            None, min_length=1, max_length=100,
            description="Only projects that use this skill (exact match).",
            examples=["Python"]),
        company: str | None = Query(
            None, min_length=1, max_length=100,
            description="Only projects done at this company (exact match).",
            examples=["Acme Corp"]),

        # page: default 1. ge=1 means "greater than or equal to 1". WHY: page 0
        # or -3 makes no sense and would break the skip calculation.
        page: int = Query(1, ge=1, description="1-based page number."),

        # limit: default 10. le=50 means "less than or equal to 50". WHY: stops
        # someone asking for a million rows and overloading the server.
        limit: int = Query(10, ge=1, le=50, description="Rows per page (1-50).")):
    """List projects, optionally filtered by skill and/or company.

    WHAT: a page of projects, each with a list of the skills it used.
    WHY:  so a client can show "all my Python projects" or "projects at Acme"
          without downloading everything.
    HOW:  1) collect a filter condition for each option the visitor supplied,
          2) let list_from_view fetch the page and total,
          3) convert the skills text into real lists, 4) return.
    """
    # Two matching lists: where[0] is a condition, params[0] is its value, etc.
    where, params = [], []

    # `is not None` = "the visitor actually supplied this option".
    if skill is not None:
        # JSON_CONTAINS(skills, value) = "does the skills list contain this value?".
        # JSON_QUOTE(%s) wraps our plain word in quotes so MySQL sees it as JSON text.
        # The word itself still goes in as a safe %s blank.
        where.append("JSON_CONTAINS(skills, JSON_QUOTE(%s))")
        params.append(skill)
    if company is not None:
        where.append("company = %s")
        params.append(company)

    # Sort by project then role so the order never changes between pages.
    rows = list_from_view(response, "v_api_projects", where, params, "project_id, role", page, limit)

    # Turn each row's skills text into a list before replying.
    return parse_skills(rows)


# ---- get_resume -----------------------------------------------------------

@app.get(
    "/api/resume",
    tags=["Resume"],
    summary="Get the complete resume document",
    description="Builds the whole resume (profile, summary, experience, projects, skills, education, awards) from the views on every request, so it is always current. The response can be large; prefer the specific endpoints when you need one section.",
    responses={200: {"description": "The full resume JSON document."},
               500: {"description": "Database unreachable or a view is missing."}},
)
def get_resume():
    """Return the complete resume in one go.

    WHAT: every section of the portfolio inside one JSON document.
    WHY:  convenient for a client that wants everything with a single request.
    HOW:  open the database and let build_resume() assemble the document.
    """
    with connect() as conn:
        return build_resume(conn)


# ---- get_summary ----------------------------------------------------------

@app.get(
    "/api/summary",
    tags=["Summary"],
    summary="Get the professional summary",
    description="Returns the single row of the `v_api_summary` view.",
    responses={200: {"description": "The summary object."},
               500: {"description": "Database unreachable or view missing."}},
)
def get_summary():
    """Return the short professional summary.

    WHAT: the "elevator pitch" paragraph about the person.
    WHY:  pages often show it at the top, on its own.
    HOW:  read the one row from the summary view and return it.
    """
    with connect() as conn:
        return fetch_all(conn, "SELECT * FROM v_api_summary")[0]


# ---- list_experience ------------------------------------------------------

@app.get(
    "/api/experience",
    tags=["Experience"],
    summary="List work experience (newest first)",
    description="Returns experience rows ordered by `start_date` descending. Optionally filter by company. Supports pagination.",
    responses=LIST_RESPONSES,
)
def list_experience(
        response: Response,   # the reply we are building (to add the total-count header)

        # Optional filter typed as ?company=... (same rules as in list_projects).
        company: str | None = Query(
            None, min_length=1, max_length=100,
            description="Only roles at this company (exact match).",
            examples=["Acme Corp"]),

        # Paging options (same meaning as in list_projects).
        page: int = Query(1, ge=1, description="1-based page number."),
        limit: int = Query(10, ge=1, le=50, description="Rows per page (1-50).")):
    """List work experience, newest job first.

    WHAT: a page of job entries.
    WHY:  resumes list the latest job first, and long histories need paging.
    HOW:  add a company filter if given, then let list_from_view do the work.
    """
    where, params = [], []
    if company is not None:
        where.append("company = %s")
        params.append(company)
    # "start_date DESC" = latest start date first.
    return list_from_view(response, "v_api_experience", where, params, "start_date DESC", page, limit)


# ---- list_skills ----------------------------------------------------------

@app.get(
    "/api/skills",
    tags=["Skills"],
    summary="List skills with project counts",
    description=(
        "Each skill comes with `project_count`, the number of projects that use it.\n\n"
        "- `evidenced=true`  -> only skills used in at least one project.\n"
        "- `evidenced=false` -> only skills claimed but not yet shown in any project.\n"
        "- `category` -> restrict to one category."
    ),
    responses=LIST_RESPONSES,
)
def list_skills(
        response: Response,   # the reply we are building (to add the total-count header)

        # `bool | None` = true, false, or not given. FastAPI also understands
        # 1/0 and yes/no and converts them to real True/False.
        evidenced: bool | None = Query(
            None, description="true = used in a project (count > 0); false = not used in any (count = 0)."),

        # Typed as `Category` (defined near the top), so only the three allowed
        # words are accepted and /docs shows a dropdown.
        category: Category | None = Query(
            None, description="Skill category: Company, Industry or Community."),

        page: int = Query(1, ge=1, description="1-based page number."),
        limit: int = Query(10, ge=1, le=50, description="Rows per page (1-50).")):
    """List skills together with how many projects use each.

    WHAT: a page of skills. "Evidenced" = proven by at least one project.
    WHY:  lets a client separate skills you can PROVE from skills you only claim.
    HOW:  add a filter for each option supplied, then let list_from_view run it.
    """
    where, params = [], []
    if evidenced is not None:
        # We choose between two FIXED pieces of text based on true/false, so no
        # visitor-typed value enters the SQL and no %s blank is needed.
        where.append("project_count > 0" if evidenced else "project_count = 0")
    if category is not None:
        where.append("category = %s")
        params.append(category)
    # Most-used skills first; ties sorted A-to-Z so the order is stable.
    return list_from_view(response, "v_api_skills", where, params, "project_count DESC, skill", page, limit)


# ---- list_education -------------------------------------------------------

@app.get(
    "/api/education",
    tags=["Education"],
    summary="List education (newest first)",
    description="Returns education rows ordered by `start_year` descending. No filters; supports pagination.",
    responses=LIST_RESPONSES,
)
def list_education(
        response: Response,   # the reply we are building (to add the total-count header)
        page: int = Query(1, ge=1, description="1-based page number."),
        limit: int = Query(10, ge=1, le=50, description="Rows per page (1-50).")):
    """List education history, most recent first.

    WHAT: a page of schools / degrees.
    WHY:  resumes show the latest education first.
    HOW:  no filters, so we pass empty lists for conditions and values;
          list_from_view does the rest. `id` is a tie-breaker so rows with the
          same start year always appear in the same order.
    """
    return list_from_view(response, "v_api_education", [], [], "start_year DESC, id", page, limit)
