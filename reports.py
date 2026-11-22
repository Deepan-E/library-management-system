import db


def overdue_books():
    """Report 1: every issued book that is past its due date.
    Joins three tables and uses DATEDIFF to count the days late."""
    return db.fetch_all(
        "SELECT i.issue_id, b.title, m.full_name AS member, m.phone, "
        "       i.due_date, DATEDIFF(CURDATE(), i.due_date) AS days_late "
        "FROM issues i "
        "JOIN books b   ON b.book_id   = i.book_id "
        "JOIN members m ON m.member_id = i.member_id "
        "WHERE i.status = 'ISSUED' AND i.due_date < CURDATE() "
        "ORDER BY days_late DESC"
    )


def most_borrowed_books():
    """Report 2: the five books issued most often.
    Uses JOIN, GROUP BY, COUNT, ORDER BY and LIMIT."""
    return db.fetch_all(
        "SELECT b.book_id, b.title, b.author, COUNT(i.issue_id) AS times_issued "
        "FROM books b "
        "JOIN issues i ON i.book_id = b.book_id "
        "GROUP BY b.book_id, b.title, b.author "
        "ORDER BY times_issued DESC, b.title "
        "LIMIT 5"
    )


def fine_summary():
    """Report 3: total fine per member, only members who owe something.
    Uses GROUP BY, SUM and HAVING."""
    return db.fetch_all(
        "SELECT m.member_id, m.full_name, m.phone, "
        "       SUM(i.fine_amount) AS total_fine "
        "FROM members m "
        "JOIN issues i ON i.member_id = m.member_id "
        "GROUP BY m.member_id, m.full_name, m.phone "
        "HAVING SUM(i.fine_amount) > 0 "
        "ORDER BY total_fine DESC"
    )


# This part runs only when you type: python reports.py
if __name__ == "__main__":
    from helpers import print_table

    print("\nOVERDUE BOOKS")
    print_table(overdue_books())

    print("\nMOST BORROWED BOOKS")
    print_table(most_borrowed_books())

    print("\nFINE SUMMARY")
    print_table(fine_summary())