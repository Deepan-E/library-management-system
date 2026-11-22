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


# This part runs only when you type: python features.py
if __name__ == "__main__":
    from helpers import print_table

    print("1. Normal issue:         ", issue_book(2, 4))   # Wings of Fire -> Sneha
    print("2. Same book twice:      ", issue_book(2, 4))
    print("3. Deactivated member:   ", issue_book(3, 6))
    print("4. Unknown book:         ", issue_book(999, 4))
    print("5. Unknown member:       ", issue_book(2, 999))
    print("6. Second book:          ", issue_book(3, 4))
    print("7. Third book:           ", issue_book(5, 4))
    print("8. Fourth book (limit):  ", issue_book(6, 4))
    print("9. Last copy of a book:  ", issue_book(4, 5))   # Clean Code -> Karthik
    print("10. No copy left:        ", issue_book(4, 3))   # Clean Code -> Rahul

    print_table(db.fetch_all(
        "SELECT issue_id, book_id, member_id, issue_date, due_date, status "
        "FROM issues WHERE issue_id > 7"
    ))

    # Clean up the test records. Use this ONLY in this test, never once you
    # start entering real records: it deletes every issue with an ID above 7
    # (the 7 sample records) and recalculates the copies on the shelf.
    db.execute("DELETE FROM issues WHERE issue_id > 7")
    db.execute(
        "UPDATE books SET available_copies = total_copies - "
        "(SELECT COUNT(*) FROM issues "
        " WHERE issues.book_id = books.book_id AND issues.status = 'ISSUED')"
    )
    print("Test records removed.")