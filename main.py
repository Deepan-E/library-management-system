import getpass

import features
from helpers import get_int, get_text, get_phone, get_password, print_table

MAX_LOGIN_ATTEMPTS = 3



# First-run setup and login

def first_run_setup():
    """Runs only when no user exists yet: create the first ADMIN account."""
    print("\nNo users found. Let's create the first ADMIN account.")
    while True:
        username = get_text("Choose a username (3-30 characters): ", 3, 30)
        password = get_password("Choose a password (at least 6 characters): ")
        confirm = get_password("Type the password again: ")
        if password != confirm:
            print("The two passwords do not match. Try again.")
            continue

        success, message = features.create_user(username, password, "ADMIN")
        print(message)
        if success:
            return


def login_screen():
    """Give the user a few attempts to log in. Returns the user or None."""
    print("\n--- LOGIN ---")
    for _ in range(MAX_LOGIN_ATTEMPTS):
        username = input("Username: ").strip()
        # getpass hides the password while it is typed.
        password = getpass.getpass("Password: ")
        user = features.login(username, password)
        if user is not None:
            print(f"\nWelcome, {user['username']} ({user['role']}).")
            return user
        print("Incorrect username or password.")

    print("Too many failed attempts. The program will close.")
    return None



# Menus

def books_menu():
    while True:
        print("\n--- BOOKS ---")
        print("1. Add a book")
        print("2. View all books")
        print("3. Search by title or author")
        print("0. Back")
        choice = get_int("Choose an option: ", 0, 3)

        if choice == 1:
            title = get_text("Title: ", 1, 120)
            author = get_text("Author: ", 1, 80)
            category = get_text("Category: ", 1, 50)
            copies = get_int("Number of copies: ", 1, 1000)
            _, message = features.add_book(title, author, category, copies)
            print(message)
        elif choice == 2:
            print_table(features.get_all_books())
        elif choice == 3:
            text = get_text("Search text: ", 1, 50)
            print_table(features.search_books(text))
        else:
            return


def members_menu(user):
    is_admin = user["role"] == "ADMIN"
    while True:
        print("\n--- MEMBERS ---")
        print("1. Register a member")
        print("2. View all members")
        print("3. Search by name or phone")
        if is_admin:
            print("4. Deactivate a member")
        print("0. Back")
        choice = get_int("Choose an option: ", 0, 4)

        if choice == 1:
            name = get_text("Full name: ", 1, 60)
            phone = get_phone("Phone (10 digits): ")
            _, message = features.add_member(name, phone)
            print(message)
        elif choice == 2:
            print_table(features.get_all_members())
        elif choice == 3:
            text = get_text("Search text: ", 1, 60)
            print_table(features.search_members(text))
        elif choice == 4:
            # The menu hides this option, but we still check the role here.
            if not is_admin:
                print("Only an ADMIN can deactivate members.")
            else:
                member_id = get_int("Member ID to deactivate: ", 1)
                _, message = features.deactivate_member(member_id)
                print(message)
        else:
            return


def admin_menu():
    while True:
        print("\n--- ADMINISTRATION ---")
        print("1. Create a new user")
        print("0. Back")
        choice = get_int("Choose an option: ", 0, 1)

        if choice == 1:
            username = get_text("New username (3-30 characters): ", 3, 30)
            password = get_password("Password (at least 6 characters): ")
            print("Role: 1 = ADMIN, 2 = LIBRARIAN")
            role = "ADMIN" if get_int("Choose a role: ", 1, 2) == 1 else "LIBRARIAN"
            _, message = features.create_user(username, password, role)
            print(message)
        else:
            return


def main_menu(user):
    is_admin = user["role"] == "ADMIN"
    while True:
        print(f"\n=== MAIN MENU  ({user['username']}, {user['role']}) ===")
        print("1. Books")
        print("2. Members")
        if is_admin:
            print("3. Administration")
        print("0. Log out")
        choice = get_int("Choose an option: ", 0, 3)

        if choice == 1:
            books_menu()
        elif choice == 2:
            members_menu(user)
        elif choice == 3:
            if is_admin:
                admin_menu()
            else:
                print("Only an ADMIN can use this option.")
        else:
            print("You have been logged out.")
            return



# Program start

def main():
    print("=== LIBRARY MANAGEMENT SYSTEM ===")

    total = features.count_users()
    if total is None:
        print("Cannot reach the database. Check your .env settings "
              "and that MySQL is running.")
        return
    if total == 0:
        first_run_setup()

    user = login_screen()
    if user is not None:
        main_menu(user)
    print("Goodbye.")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nProgram closed.")