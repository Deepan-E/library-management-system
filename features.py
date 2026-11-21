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


if __name__ == "__main__":
    
    from helpers import print_table
    print(add_book("Test Book", "Test Author", "Testing", 2))
    print(add_book("Test Book", "Test Author", "Testing", 2))   # duplicate
    print_table(search_books("narayan"))
    print_table(search_books("' OR '1'='1"))                    # injection test
    print_table(get_all_books())