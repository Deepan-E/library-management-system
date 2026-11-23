from datetime import date, timedelta

import mysql.connector

import db
from helpers import hash_password, verify_password

# Business rules from the brief, kept in named constants.
LOAN_DAYS = 14                 # days a book can be kept
MAX_BOOKS_PER_MEMBER = 3       # books one member may hold at the same time
FINE_PER_DAY = 2               # rupees for every day after the due date

def add_book(title, author, category, total_copies):
    """Insert a new book. Returns (True/False, message for the user)."""
    # Refuse a duplicate: same title and author already in the catalogue.
    existing = db.fetch_one(
        "SELECT book_id FROM books WHERE title = %s AND author = %s",
        (title, author),
    )
    if existing:
        return False, (
            f"This book already exists (ID {existing['book_id']}). "
            "Update its number of copies instead."
        )

    # A new book starts with every copy on the shelf.
    changed = db.execute(
        "INSERT INTO books (title, author, category, total_copies, available_copies) "
        "VALUES (%s, %s, %s, %s, %s)",
        (title, author, category, total_copies, total_copies),
    )
    if changed is None:
        return False, "The book could not be saved."
    return True, "Book added successfully."


def get_all_books():
    """Return every book, sorted by title."""
    return db.fetch_all(
        "SELECT book_id, title, author, category, total_copies, available_copies "
        "FROM books ORDER BY title"
    )


def search_books(text):
    """Return books whose title or author contains the given text."""
    pattern = "%" + text + "%"
    return db.fetch_all(
        "SELECT book_id, title, author, category, total_copies, available_copies "
        "FROM books WHERE title LIKE %s OR author LIKE %s ORDER BY title",
        (pattern, pattern),
    )


# Members
def add_member(full_name, phone):
    """Register a new member. Returns (True/False, message for the user)."""
    existing = db.fetch_one(
        "SELECT member_id FROM members WHERE phone = %s", (phone,)
    )
    if existing:
        return False, (
            f"This phone number is already registered "
            f"(member ID {existing['member_id']})."
        )

    # is_active is not given, so the database uses its DEFAULT of 1.
    changed = db.execute(
        "INSERT INTO members (full_name, phone) VALUES (%s, %s)",
        (full_name, phone),
    )
    if changed is None:
        return False, "The member could not be saved."
    return True, "Member registered successfully."


def get_all_members():
    """Return every member, sorted by name."""
    return db.fetch_all(
        "SELECT member_id, full_name, phone, is_active "
        "FROM members ORDER BY full_name"
    )


def get_member(member_id):
    """Return one member as a dictionary, or None if the ID does not exist."""
    return db.fetch_one(
        "SELECT member_id, full_name, phone, is_active "
        "FROM members WHERE member_id = %s",
        (member_id,),
    )


def search_members(text):
    """Return members whose name or phone contains the given text."""
    pattern = "%" + text + "%"
    return db.fetch_all(
        "SELECT member_id, full_name, phone, is_active "
        "FROM members WHERE full_name LIKE %s OR phone LIKE %s "
        "ORDER BY full_name",
        (pattern, pattern),
    )


def deactivate_member(member_id):
    """Set is_active to 0. The member is kept, so old issue records stay valid."""
    member = get_member(member_id)
    if member is None:
        return False, "No member exists with that ID."
    if member["is_active"] == 0:
        return False, "This member is already deactivated."

    changed = db.execute(
        "UPDATE members SET is_active = 0 WHERE member_id = %s", (member_id,)
    )
    if changed is None:
        return False, "The member could not be deactivated."
    return True, f"{member['full_name']} has been deactivated."


# ---------------------------------------------------------------------
# Users and login
# ---------------------------------------------------------------------
VALID_ROLES = ("ADMIN", "LIBRARIAN")


def count_users():
    """Return how many users exist, or None if the database could not be read."""
    row = db.fetch_one("SELECT COUNT(*) AS total FROM users")
    if row is None:
        return None
    return row["total"]


def create_user(username, password, role):
    """Create a login account. Returns (True/False, message for the user)."""
    if role not in VALID_ROLES:
        return False, "The role must be ADMIN or LIBRARIAN."

    existing = db.fetch_one(
        "SELECT user_id FROM users WHERE username = %s", (username,)
    )
    if existing:
        return False, "That username is already taken."

    # Only the salted hash is stored, never the real password.
    changed = db.execute(
        "INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s)",
        (username, hash_password(password), role),
    )
    if changed is None:
        return False, "The user could not be saved."
    return True, f"{role.title()} account '{username}' created."


def login(username, password):
    """Return the user's details (without the hash) if the login is correct,
    otherwise None. The caller cannot tell which part was wrong."""
    user = db.fetch_one(
        "SELECT user_id, username, password_hash, role FROM users "
        "WHERE username = %s",
        (username,),
    )
    if user is None or not verify_password(password, user["password_hash"]):
        return None
    return {
        "user_id": user["user_id"],
        "username": user["username"],
        "role": user["role"],
    }

# ---------------------------------------------------------------------
# Circulation: issuing books
# ---------------------------------------------------------------------
def issue_book(book_id, member_id):
    """Issue one copy of a book to a member.
    Returns (True/False, message for the user)."""

    # --- Rule checks: nothing is changed in this part ---
    member = get_member(member_id)
    if member is None:
        return False, "No member exists with that ID."
    if member["is_active"] == 0:
        return False, "This member is deactivated and cannot borrow books."

    book = db.fetch_one(
        "SELECT book_id, title, available_copies FROM books WHERE book_id = %s",
        (book_id,),
    )
    if book is None:
        return False, "No book exists with that ID."
    if book["available_copies"] <= 0:
        return False, f"No copy of '{book['title']}' is available right now."

    held = db.fetch_one(
        "SELECT COUNT(*) AS total FROM issues "
        "WHERE member_id = %s AND status = 'ISSUED'",
        (member_id,),
    )
    if held is None:
        return False, "Could not check how many books the member holds."
    if held["total"] >= MAX_BOOKS_PER_MEMBER:
        return False, (
            f"{member['full_name']} already holds {MAX_BOOKS_PER_MEMBER} books, "
            "which is the maximum."
        )

    same_book = db.fetch_one(
        "SELECT issue_id FROM issues "
        "WHERE member_id = %s AND book_id = %s AND status = 'ISSUED'",
        (member_id, book_id),
    )
    if same_book:
        return False, "This member already holds a copy of this book."

    # --- The transaction: both changes are saved together, or neither ---
    today = date.today()
    due = today + timedelta(days=LOAN_DAYS)

    conn = None
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        conn.start_transaction()

        # Step 1: record the loan.
        cursor.execute(
            "INSERT INTO issues (book_id, member_id, issue_date, due_date) "
            "VALUES (%s, %s, %s, %s)",
            (book_id, member_id, today, due),
        )

        # Step 2: take one copy off the shelf. The 'available_copies > 0'
        # condition is the final safety net.
        cursor.execute(
            "UPDATE books SET available_copies = available_copies - 1 "
            "WHERE book_id = %s AND available_copies > 0",
            (book_id,),
        )
        if cursor.rowcount == 0:
            conn.rollback()                     # undo the INSERT as well
            return False, f"No copy of '{book['title']}' is available right now."

        conn.commit()                           # save both changes
        return True, (
            f"Issued '{book['title']}' to {member['full_name']}. "
            f"Due date: {due}."
        )
    except mysql.connector.Error as err:
        if conn is not None:
            conn.rollback()                     # undo everything
        print(f"Database error: {err}")
        return False, "The book could not be issued. No changes were saved."
    finally:
        if conn is not None and conn.is_connected():
            conn.close()


# ---------------------------------------------------------------------
# Circulation: returning books
# ---------------------------------------------------------------------
def return_book(issue_id):
    """Return a book using the ID of its issue record.
    Calculates the fine automatically. Returns (True/False, message)."""

    # --- Checks: nothing is changed in this part ---
    issue = db.fetch_one(
        "SELECT i.issue_id, i.book_id, i.due_date, i.status, b.title "
        "FROM issues i JOIN books b ON b.book_id = i.book_id "
        "WHERE i.issue_id = %s",
        (issue_id,),
    )
    if issue is None:
        return False, "No issue record exists with that ID."
    if issue["status"] == "RETURNED":
        return False, "This book has already been returned."

    # --- Fine: Rs FINE_PER_DAY for every day after the due date ---
    today = date.today()
    days_late = max(0, (today - issue["due_date"]).days)
    fine = days_late * FINE_PER_DAY

    # --- The transaction: both changes are saved together, or neither ---
    conn = None
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        conn.start_transaction()

        # Step 1: close the loan record.
        cursor.execute(
            "UPDATE issues SET return_date = %s, status = 'RETURNED', "
            "fine_amount = %s WHERE issue_id = %s AND status = 'ISSUED'",
            (today, fine, issue_id),
        )
        if cursor.rowcount != 1:
            conn.rollback()
            return False, "This book could not be returned. No changes were saved."

        # Step 2: put the copy back on the shelf.
        cursor.execute(
            "UPDATE books SET available_copies = available_copies + 1 "
            "WHERE book_id = %s",
            (issue["book_id"],),
        )

        conn.commit()                           # save both changes
        if fine > 0:
            return True, (
                f"'{issue['title']}' returned {days_late} day(s) late. "
                f"Fine: Rs {fine}."
            )
        return True, f"'{issue['title']}' returned on time. No fine."
    except mysql.connector.Error as err:
        if conn is not None:
            conn.rollback()                     # undo both changes
        print(f"Database error: {err}")
        return False, "The book could not be returned. No changes were saved."
    finally:
        if conn is not None and conn.is_connected():
            conn.close()



# Circulation: books held by a member

def get_member_loans(member_id):
    """Return the books a member currently holds (not yet returned).
    days_late is 0 for a book that is not overdue."""
    return db.fetch_all(
        "SELECT i.issue_id, b.title, b.author, i.issue_date, i.due_date, "
        "       GREATEST(0, DATEDIFF(CURDATE(), i.due_date)) AS days_late "
        "FROM issues i "
        "JOIN books b ON b.book_id = i.book_id "
        "WHERE i.member_id = %s AND i.status = 'ISSUED' "
        "ORDER BY i.due_date",
        (member_id,),
    )

def update_copies(book_id, new_total):
    """Change how many copies the library owns.
    available_copies is recalculated as: new total - copies currently issued.
    Returns (True/False, message for the user)."""
    book = db.fetch_one(
        "SELECT book_id, title FROM books WHERE book_id = %s", (book_id,)
    )
    if book is None:
        return False, "No book exists with that ID."

    out = db.fetch_one(
        "SELECT COUNT(*) AS total FROM issues "
        "WHERE book_id = %s AND status = 'ISSUED'",
        (book_id,),
    )
    if out is None:
        return False, "Could not check how many copies are issued."
    copies_out = out["total"]

    if new_total < copies_out:
        return False, (
            f"{copies_out} copy/copies of '{book['title']}' are currently "
            f"issued, so the total cannot be less than {copies_out}."
        )

    new_available = new_total - copies_out
    changed = db.execute(
        "UPDATE books SET total_copies = %s, available_copies = %s "
        "WHERE book_id = %s",
        (new_total, new_available, book_id),
    )
    if changed is None:
        return False, "The number of copies could not be updated."
    return True, (
        f"'{book['title']}' now has {new_total} copies "
        f"({new_available} available)."
    )