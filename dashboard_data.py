import db


def get_dashboard_stats():

    query = """
        SELECT
            (SELECT COUNT(*) FROM books)
                AS total_books,

            (SELECT COALESCE(SUM(available_copies), 0)
             FROM books)
                AS available_copies,

            (SELECT COUNT(*) FROM members
             WHERE is_active = 1)
                AS active_members,

            (SELECT COUNT(*) FROM issues
             WHERE status = 'ISSUED')
                AS issued_books,

            (SELECT COUNT(*) FROM issues
             WHERE status = 'ISSUED'
             AND due_date < CURDATE())
                AS overdue_books,

            (SELECT COALESCE(SUM(fine_amount), 0)
             FROM issues
             WHERE status = 'RETURNED')
                AS total_fines
    """

    return db.fetch_one(query)


def get_recent_transactions():

    query = """
        SELECT
            i.issue_id,
            b.title,
            m.full_name,
            i.issue_date,
            i.due_date,
            i.return_date,

            CASE
                WHEN i.status = 'RETURNED'
                    THEN 'RETURNED'

                WHEN i.due_date < CURDATE()
                    THEN 'OVERDUE'

                ELSE 'ISSUED'
            END AS display_status

        FROM issues i

        JOIN books b
            ON i.book_id = b.book_id

        JOIN members m
            ON i.member_id = m.member_id

        ORDER BY i.issue_id DESC

        LIMIT 5
    """

    return db.fetch_all(query)


if __name__ == "__main__":

    print("Dashboard statistics:")
    print(get_dashboard_stats())

    print("\nRecent transactions:")

    for transaction in get_recent_transactions():
        print(transaction)