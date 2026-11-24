"""
db.py - the "database helper" file.

WHAT: A small toolbox with three tools: open a connection to the database,
      run a question (query) and get the answers, and fix values that the
      JSON format does not understand.
WHY:  We keep ALL database work in this one file so the other file (main.py)
      only has to think about web addresses. Think of a restaurant: the waiter
      (main.py) never cooks; he asks the kitchen (db.py).
HOW:  main.py calls connect() to open the door to the database, then calls
      fetch_all() to ask questions through that door.
"""

# ---------------------------------------------------------------------------
# IMPORTS  (an import = "borrow a ready-made tool someone else already built")
# ---------------------------------------------------------------------------

# WHAT: `os` lets Python talk to the computer it is running on.
# WHY:  we need it to read secret settings (like the database password) that are
#       kept OUTSIDE the code.
# HOW:  later we write os.getenv("NAME") which means "look up the setting called NAME".
import os

# WHAT: `date` and `datetime` are Python's types for calendar dates and date+time.
# WHY:  the database hands us dates in this form, and we must recognise them
#       so we can turn them into plain text.
# HOW:  used in to_json_value() with isinstance() to check "is this value a date?".
from datetime import date, datetime

# WHAT: `Decimal` is a number type that is exact (no rounding surprises), like money.
# WHY:  MySQL returns DECIMAL columns this way, but the JSON format cannot carry it.
# HOW:  to_json_value() checks for it and converts it to a normal number.
from decimal import Decimal

# WHAT: the official MySQL driver - the "phone line" between Python and MySQL.
# WHY:  Python cannot talk to MySQL on its own.
# HOW:  we call mysql.connector.connect(...) inside connect() below.
import mysql.connector

# WHAT: a tool that reads a file named `.env` and loads its lines as settings.
# WHY:  passwords must never be typed into code (anyone who sees the code would
#       see the password, and it would end up on GitHub).
# HOW:  we call load_dotenv() once, right below.
from dotenv import load_dotenv

# WHAT: read the `.env` file now.
# WHY:  the settings must be ready before any function below asks for them.
#       Doing it once at start-up is faster than reading the file every request.
# HOW:  after this line, os.getenv("DB_USER") can find what you wrote in `.env`.
#       If there is no `.env` file, nothing happens (no crash).
load_dotenv()


def connect():
    """Open a new connection (a "phone call") to the MySQL database.

    WHAT: gives back a ready-to-use connection object.
    WHY:  you cannot ask the database anything until a connection is open.
          We open a fresh one per request because connections can drop or go
          stale, and sharing one between many visitors can mix them up.
    HOW:  read the host, port, user, password and database name from the
          settings, hand them to the MySQL driver, return what it gives us.
    """
    # `return` = "give this result back to whoever called the function".
    return mysql.connector.connect(

        # host = WHERE the database lives (its address).
        # os.getenv("DB_HOST", "localhost"): look for a setting named DB_HOST;
        # if nobody set it, use "localhost", which means "this same computer".
        host=os.getenv("DB_HOST", "localhost"),

        # port = WHICH door of that computer to knock on. MySQL's usual door is 3306.
        # Settings always arrive as text ("3306"), but the driver wants a real
        # number, so int() converts the text into a number.
        port=int(os.getenv("DB_PORT", "3306")),

        # user / password = WHO you are. There is deliberately NO fallback value:
        # if they are missing we WANT an error, instead of quietly trying a
        # guessable login.
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),

        # database = WHICH database on that server to open.
        database=os.getenv("DB_NAME", "future_portfolio_db"),
    )


def fetch_all(conn, sql, params=()):
    """Ask the database one question (a SELECT) and return ALL the answer rows.

    WHAT: takes an open connection, a SQL question and the values to plug in;
          returns a list where every row is a dictionary like
          {"name": "Ananya", "city": "Chicago"}.
    WHY:  one helper means every query in the project is run the same safe way,
          and rows as dictionaries become JSON objects with no extra work.
    HOW:  create a cursor (the "pen" that writes the question and reads the
          answer), run the SQL, collect all rows, close the cursor.

    Arguments:
        conn   - the open connection from connect().
        sql    - the question in SQL. Where a value goes, write %s (a blank to fill).
        params - the values for those blanks, in order, e.g. ["Python"].

    SAFETY (very important): never paste user text into the SQL string yourself.
    Keep the blanks (%s) in the SQL and pass the values in `params`. The driver
    then treats the values purely as data, so a hacker typing SQL commands into
    a search box cannot make the database run them. This attack is called
    "SQL injection".
    """
    # `params=()` means "if the caller gives no values, use an empty list of values".
    # It is a tuple () and not a list [] because a list default is shared between
    # calls and can cause strange bugs; a tuple can never change.

    # `with ... as cursor:` = "use this, and close it automatically when done,
    # even if something goes wrong". Like a door that always locks behind you.
    # `dictionary=True` = give me each row labelled by column name, not as an
    # unlabelled list of numbers.
    with conn.cursor(dictionary=True) as cursor:
        # Send the question to MySQL; the %s blanks get filled from `params` safely.
        cursor.execute(sql, params)
        # Read every answer row at once and return the list.
        # (Fine for small tables; a huge table would need to be read in chunks.)
        return cursor.fetchall()


def to_json_value(value):
    """Convert a value JSON cannot store into one it can.

    WHAT: turns dates into text ("2026-11-24") and exact decimals into ordinary numbers.
    WHY:  JSON only knows text, numbers, true/false, lists and objects. It has no
          "date" type. Without this, saving database rows as JSON would crash.
    HOW:  you pass this function to json.dumps(data, default=to_json_value).
          json.dumps calls it only for values it does not understand.
    """
    # isinstance(value, X) = "is this value an X?".  A date -> write it as text.
    # .isoformat() makes the standard "YYYY-MM-DD" form that every language can read.
    if isinstance(value, (date, datetime)):
        return value.isoformat()

    # A Decimal -> an ordinary number (float).
    if isinstance(value, Decimal):
        return float(value)

    # `raise` = stop and show an error. For any other unknown type we prefer a loud
    # error to quietly saving wrong data. f"..." (an f-string) lets us insert the
    # type's name into the message; {type(value).__name__} is that name.
    raise TypeError(f"cannot convert {type(value).__name__} to JSON")
