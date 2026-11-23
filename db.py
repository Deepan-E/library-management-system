import os
import mysql.connector
from dotenv import load_dotenv

# Read DB_HOST, DB_USER, DB_PASSWORD, DB_NAME from the .env file
load_dotenv()


def get_connection():
    """Open and return a new connection to the MySQL database."""
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
    )


def fetch_all(query, params=None):
    """Run a SELECT and return all rows as a list of dictionaries."""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, params or ())
        return cursor.fetchall()
    except mysql.connector.Error as err:
        print(f"Database error: {err}")
        return []
    finally:
        if conn is not None and conn.is_connected():
            conn.close()


def fetch_one(query, params=None):
    """Run a SELECT and return the first row as a dictionary (or None)."""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, params or ())
        return cursor.fetchone()
    except mysql.connector.Error as err:
        print(f"Database error: {err}")
        return None
    finally:
        if conn is not None and conn.is_connected():
            conn.close()


def execute(query, params=None):
    """Run an INSERT, UPDATE or DELETE and save it.
    Returns the number of rows changed, or None if something went wrong."""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params or ())
        conn.commit()
        return cursor.rowcount
    except mysql.connector.Error as err:
        if conn is not None:
            conn.rollback()
        print(f"Database error: {err}")
        return None
    finally:
        if conn is not None and conn.is_connected():
            conn.close()


# This part runs only when you type: python db.py
if __name__ == "__main__":
    print(fetch_one("SELECT COUNT(*) AS total FROM books"))