import os
import random
import time

from functools import wraps

from flask import (
    Flask, render_template, request,
    redirect, url_for, session, flash, abort
)

from flask_wtf.csrf import CSRFProtect
from dotenv import load_dotenv

import features
import db
import dashboard_data
import reports


load_dotenv()

app = Flask(__name__)

app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY")

if not app.config["SECRET_KEY"]:
    raise RuntimeError("FLASK_SECRET_KEY is missing from .env")

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

csrf = CSRFProtect(app)


# ==========================================
# ACCESS CONTROL
# ==========================================

def login_required(function):

    @wraps(function)
    def wrapper(*args, **kwargs):

        if "user_id" not in session:
            flash("Please log in first.", "error")
            return redirect(url_for("login"))

        if session.get("role") not in ("ADMIN", "LIBRARIAN"):
            abort(403)

        return function(*args, **kwargs)

    return wrapper


def admin_required(function):

    @wraps(function)
    @login_required
    def wrapper(*args, **kwargs):

        if session.get("role") != "ADMIN":
            abort(403)

        return function(*args, **kwargs)

    return wrapper


def show_result(result, endpoint):

    success, message = result

    flash(message, "success" if success else "error")

    return redirect(url_for(endpoint))


# ==========================================
# HOME AND AUTHENTICATION
# ==========================================

@app.route("/")
def home():

    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():

    if "user_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:

            flash("Enter your username and password.", "error")

        else:

            user = features.login(username, password)

            if user:

                session.clear()

                session["user_id"] = user["user_id"]
                session["username"] = user["username"]
                session["role"] = user["role"]

                return redirect(url_for("dashboard"))

            flash("Incorrect username or password.", "error")

    return render_template("login.html")


@app.post("/logout")
def logout():

    session.clear()

    flash("Logged out successfully.", "success")

    return redirect(url_for("login"))


# ==========================================
# DASHBOARD
# ==========================================

@app.route("/dashboard")
@login_required
def dashboard():

    stats = dashboard_data.get_dashboard_stats()

    if stats is None:
        flash("Unable to load dashboard statistics.", "error")
        stats = {}

    if session.get("role") != "ADMIN":
        stats.pop("total_fines", None)

    transactions = dashboard_data.get_recent_transactions()

    return render_template(
        "dashboard.html",
        stats=stats,
        transactions=transactions
    )


# ==========================================
# BOOKS MANAGEMENT
# ==========================================

@app.route("/books")
@login_required
def books():

    search = request.args.get("q", "").strip()[:120]

    all_books = features.get_all_books()

    book_list = (
        features.search_books(search)
        if search else all_books
    )

    summary = {
        "total_titles": len(all_books),
        "total_copies": sum(
            b["total_copies"] for b in all_books
        ),
        "available_copies": sum(
            b["available_copies"] for b in all_books
        )
    }

    return render_template(
        "books.html",
        books=book_list,
        search=search,
        summary=summary
    )


@app.route("/books/add", methods=["GET", "POST"])
@login_required
def add_book():

    if request.method == "POST":

        title = request.form.get("title", "").strip()
        author = request.form.get("author", "").strip()
        category = request.form.get("category", "").strip()

        copies = request.form.get(
            "total_copies", type=int
        )

        if not 1 <= len(title) <= 120:

            flash("Invalid book title.", "error")

        elif not 1 <= len(author) <= 80:

            flash("Invalid author name.", "error")

        elif not 1 <= len(category) <= 50:

            flash("Invalid category.", "error")

        elif copies is None or not 1 <= copies <= 1000:

            flash("Copies must be between 1 and 1000.", "error")

        else:

            success, message = features.add_book(
                title, author, category, copies
            )

            flash(message, "success" if success else "error")

            if success:
                return redirect(url_for("books"))

    return render_template("add_book.html")


@app.route("/books/edit/<int:book_id>", methods=["GET", "POST"])
@login_required
def edit_book(book_id):

    book = db.fetch_one(
        "SELECT * FROM books WHERE book_id = %s",
        (book_id,)
    )

    if book is None:

        flash("Book not found or could not be loaded.", "error")

        return redirect(url_for("books"))

    issued_copies = (
        book["total_copies"] - book["available_copies"]
    )

    if request.method == "POST":

        new_total = request.form.get(
            "total_copies", type=int
        )

        if new_total is None or not 0 <= new_total <= 1000:

            flash("Copies must be between 0 and 1000.", "error")

        else:

            success, message = features.update_copies(
                book_id, new_total
            )

            flash(message, "success" if success else "error")

            if success:
                return redirect(url_for("books"))

    return render_template(
        "edit_book.html",
        book=book,
        issued_copies=issued_copies
    )


# ==========================================
# MEMBERS MANAGEMENT
# ==========================================

@app.route("/members", methods=["GET", "POST"])
@login_required
def members():

    if request.method == "POST":

        name = request.form.get("full_name", "").strip()
        phone = request.form.get("phone", "").strip()

        if not 1 <= len(name) <= 60:

            flash("Enter a valid member name.", "error")

        elif (
            len(phone) != 10
            or not phone.isascii()
            or not phone.isdigit()
        ):

            flash("Enter a valid 10-digit phone number.", "error")

        else:

            return show_result(
                features.add_member(name, phone),
                "members"
            )

    search = request.args.get("q", "").strip()[:60]

    all_members = features.get_all_members()

    rows = (
        features.search_members(search)
        if search else all_members
    )

    return render_template(
        "members.html",
        rows=rows,
        q=search,
        total=len(all_members),
        active=sum(bool(m["is_active"]) for m in all_members)
    )


@app.post("/members/<int:member_id>/deactivate")
@admin_required
def deactivate_member(member_id):

    return show_result(
        features.deactivate_member(member_id),
        "members"
    )


# ==========================================
# CIRCULATION
# ==========================================

@app.route("/circulation", methods=["GET", "POST"])
@login_required
def circulation():

    if request.method == "POST":

        book_id = request.form.get("book_id", type=int)
        member_id = request.form.get("member_id", type=int)

        if not book_id or not member_id or min(book_id, member_id) < 1:

            flash("Select a valid book and member.", "error")

            return redirect(url_for("circulation"))

        return show_result(
            features.issue_book(book_id, member_id),
            "circulation"
        )

    selected = request.args.get("member_id", type=int)

    loans = db.fetch_all(
        """
        SELECT
            i.issue_id,
            i.member_id,
            b.title,
            m.full_name,
            i.issue_date,
            i.due_date,
            GREATEST(
                0, DATEDIFF(CURDATE(), i.due_date)
            ) AS days_late
        FROM issues i
        JOIN books b ON b.book_id = i.book_id
        JOIN members m ON m.member_id = i.member_id
        WHERE i.status = 'ISSUED'
        ORDER BY i.due_date
        """
    )

    rows = [
        row for row in loans
        if selected is None or row["member_id"] == selected
    ]

    return render_template(
        "circulation.html",
        books=features.get_all_books(),
        members=features.get_all_members(),
        rows=rows,
        selected=selected,
        total_loans=len(loans),
        overdue=sum(r["days_late"] > 0 for r in loans)
    )


@app.post("/circulation/<int:issue_id>/return")
@login_required
def return_book(issue_id):

    return show_result(
        features.return_book(issue_id),
        "circulation"
    )


# ==========================================
# REPORTS
# ==========================================

@app.route("/reports")
@login_required
def report_page():

    sections = [
        ("Overdue Books", reports.overdue_books()),
        ("Most Borrowed Books", reports.most_borrowed_books())
    ]

    if session.get("role") == "ADMIN":

        sections.append(
            ("Recorded Fine Summary", reports.fine_summary())
        )

    return render_template(
        "reports.html",
        sections=sections,
        heading="Library Reports"
    )


# ==========================================
# ADMINISTRATION
# ==========================================

@app.route("/administration", methods=["GET", "POST"])
@admin_required
def administration():

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        role = request.form.get("role", "")

        if not 3 <= len(username) <= 30:

            flash("Username must contain 3 to 30 characters.", "error")

        elif not 6 <= len(password) <= 256:

            flash("Password must contain 6 to 256 characters.", "error")

        elif role not in ("ADMIN", "LIBRARIAN"):

            flash("Invalid role.", "error")

        else:

            return show_result(
                features.create_user(username, password, role),
                "administration"
            )

    rows = db.fetch_all(
        """
        SELECT user_id, username, role
        FROM users
        ORDER BY username
        """
    )

    return render_template("admin.html", rows=rows)


# ==========================================
# DSA DEMONSTRATION
# ==========================================

@app.post("/dsa")
@admin_required
def dsa():

    rng = random.Random(42)

    titles = [
        f"Book Title {number:06d}"
        for number in range(100000)
    ]

    rng.shuffle(titles)

    targets = rng.sample(titles, 200)

    start = time.perf_counter()

    sorted_titles = sorted(titles)

    sort_time = time.perf_counter() - start

    start = time.perf_counter()

    lookup = {
        title: index
        for index, title in enumerate(titles)
    }

    build_time = time.perf_counter() - start

    start = time.perf_counter()

    for target in targets:
        reports.linear_search(titles, target)

    linear_time = time.perf_counter() - start

    start = time.perf_counter()

    for target in targets:
        reports.binary_search(sorted_titles, target)

    binary_time = time.perf_counter() - start

    start = time.perf_counter()

    for target in targets:
        lookup.get(target, -1)

    dictionary_time = time.perf_counter() - start

    def row(method, complexity, setup, duration):

        return {
            "method": method,
            "complexity": complexity,
            "setup_ms": round(setup * 1000, 3),
            "search_ms": round(duration * 1000, 3),
            "speedup": round(
                linear_time / max(duration, 0.000000001), 2
            )
        }

    results = [
        row("Linear Search", "O(n)", 0, linear_time),
        row("Binary Search", "O(log n)", sort_time, binary_time),
        row("Dictionary Lookup", "O(1) average", build_time, dictionary_time)
    ]

    return render_template(
        "reports.html",
        heading="DSA Performance Analysis",
        sections=[
            ("100,000 Book Titles — 200 Searches", results)
        ]
    )


if __name__ == "__main__":

    app.run(debug=False)