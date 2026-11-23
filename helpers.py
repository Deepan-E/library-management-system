import getpass
import hashlib
import hmac
import os

# How many times the hash is repeated; more repeats make guessing slower.
HASH_ITERATIONS = 100_000



# Input checking
def get_int(prompt, min_value=None, max_value=None):
    while True:
        text = input(prompt).strip()
        try:
            value = int(text)
        except ValueError:
            print("Please enter a whole number (digits only).")
            continue

        if min_value is not None and value < min_value:
            print(f"The number must be at least {min_value}.")
            continue
        if max_value is not None and value > max_value:
            print(f"The number must be at most {max_value}.")
            continue
        return value


def get_text(prompt, min_length=1, max_length=100):
    while True:
        text = input(prompt).strip()
        if len(text) < min_length:
            print(f"Please enter at least {min_length} character(s).")
            continue
        if len(text) > max_length:
            print(f"Please enter at most {max_length} characters.")
            continue
        return text


def get_phone(prompt):
    while True:
        text = input(prompt).strip()
        if text.isdigit() and len(text) == 10:
            return text
        print("A phone number must be exactly 10 digits.")


def get_password(prompt, min_length=6):
    while True:
        text = getpass.getpass(prompt)
        if len(text) >= min_length:
            return text
        print(f"The password must be at least {min_length} characters.")



# Password hashing
def hash_password(password):
    salt = os.urandom(16)                       # new random salt every time
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, HASH_ITERATIONS
    )
    return salt.hex() + "$" + digest.hex()


def verify_password(password, stored_value):
    try:
        salt_hex, digest_hex = stored_value.split("$")
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
    except ValueError:
        return False                            # stored value is damaged

    actual = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, HASH_ITERATIONS
    )
    return hmac.compare_digest(actual, expected)



# Table printing
def _cell(value):
    """Show a missing value (None) as a dash."""
    return "-" if value is None else str(value)


def print_table(rows):
    """Print a list of dictionaries as a formatted table."""
    if not rows:
        print("No records found.")
        return

    headers = list(rows[0].keys())
    widths = {
        h: max(len(str(h)), max(len(_cell(r[h])) for r in rows))
        for h in headers
    }

    line = "+-" + "-+-".join("-" * widths[h] for h in headers) + "-+"
    print(line)
    print("| " + " | ".join(str(h).ljust(widths[h]) for h in headers) + " |")
    print(line)
    for r in rows:
        print("| " + " | ".join(_cell(r[h]).ljust(widths[h]) for h in headers) + " |")
    print(line)


if __name__ == "__main__":
    stored = hash_password("secret123")
    print("Stored value:", stored)
    print("Correct password:", verify_password("secret123", stored))
    print("Wrong password:", verify_password("wrong", stored))
    print("Hashing twice gives different text:", hash_password("secret123") != stored)

    print_table([
        {"id": 1, "title": "Clean Code", "copies": 2},
        {"id": 2, "title": "Sapiens", "copies": None},
    ])
    print_table([])