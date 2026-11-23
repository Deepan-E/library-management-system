import random
import time

import db
from helpers import print_table

# Size of the demonstration, as required by the brief.
DSA_LIST_SIZE = 100_000
DSA_SEARCHES = 200


# ---------------------------------------------------------------------
# Reports (each one is a single SQL query)
# ---------------------------------------------------------------------
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


# ---------------------------------------------------------------------
# DSA demonstration: three ways to search 100,000 titles
# ---------------------------------------------------------------------
def linear_search(items, target):
    """O(n): check every item one by one. Returns its position or -1."""
    for position, item in enumerate(items):
        if item == target:
            return position
    return -1


def binary_search(sorted_items, target):
    """O(log n): works only on SORTED data.
    Look at the middle item and throw away the half that cannot contain
    the target. Returns its position or -1."""
    low = 0
    high = len(sorted_items) - 1
    while low <= high:
        middle = (low + high) // 2
        if sorted_items[middle] == target:
            return middle
        elif sorted_items[middle] < target:
            low = middle + 1          # target can only be in the right half
        else:
            high = middle - 1         # target can only be in the left half
    return -1


def run_dsa_demo():
    """Build 100,000 titles, then time three ways of searching them."""
    print(f"\nDSA DEMONSTRATION: searching {DSA_LIST_SIZE:,} book titles")
    print(f"Each method searches for the same {DSA_SEARCHES} titles.\n")

    random.seed(42)                   # same data every run, so results compare
    titles = [f"Book Title {number:06d}" for number in range(DSA_LIST_SIZE)]
    random.shuffle(titles)            # unsorted, like a real catalogue
    targets = random.sample(titles, DSA_SEARCHES)

    # Setup cost 1: binary search needs the list sorted.
    start = time.perf_counter()
    sorted_titles = sorted(titles)
    sort_time = time.perf_counter() - start

    # Setup cost 2: a dictionary has to be built before it can be used.
    start = time.perf_counter()
    position_of = {title: position for position, title in enumerate(titles)}
    build_time = time.perf_counter() - start

    # Sanity check: all three methods must find the same title.
    check = targets[0]
    assert titles[linear_search(titles, check)] == check
    assert sorted_titles[binary_search(sorted_titles, check)] == check
    assert titles[position_of[check]] == check

    # Time the searches.
    start = time.perf_counter()
    for target in targets:
        linear_search(titles, target)
    linear_time = time.perf_counter() - start

    start = time.perf_counter()
    for target in targets:
        binary_search(sorted_titles, target)
    binary_time = time.perf_counter() - start

    start = time.perf_counter()
    for target in targets:
        position_of.get(target, -1)
    dict_time = time.perf_counter() - start

    def row(name, complexity, setup, total):
        return {
            "Method": name,
            "Complexity": complexity,
            "Setup (ms)": f"{setup * 1000:.2f}",
            f"{DSA_SEARCHES} searches (ms)": f"{total * 1000:.3f}",
            "Per search (us)": f"{total / DSA_SEARCHES * 1_000_000:.2f}",
            "Times faster than linear": f"{linear_time / total:,.0f}",
        }

    print_table([
        row("Linear search", "O(n)", 0, linear_time),
        row("Binary search", "O(log n)", sort_time, binary_time),
        row("Dictionary lookup", "O(1) average", build_time, dict_time),
    ])
    print("\nSetup = time to sort the list (binary search) or build the "
          "dictionary. us = microseconds.")


# This part runs only when you type: python reports.py
if __name__ == "__main__":
    print("\nOVERDUE BOOKS")
    print_table(overdue_books())

    print("\nMOST BORROWED BOOKS")
    print_table(most_borrowed_books())

    print("\nFINE SUMMARY")
    print_table(fine_summary())

    run_dsa_demo()