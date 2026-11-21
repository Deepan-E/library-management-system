import db


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


if __name__ == "__main__":
    from helpers import print_table

    print(add_member("Test Member", "9000000001"))
    print(add_member("Another Name", "9000000001"))   # duplicate phone
    print_table(search_members("priya"))
    print_table(search_members("9876"))
    print(deactivate_member(7))                        # fill in the test ID, see below
    print(deactivate_member(7))                        # already deactivated
    print(deactivate_member(9999))                     # does not exist
    print_table(get_all_members())