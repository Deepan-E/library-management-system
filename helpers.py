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


if __name__ == "__main__":
    print("Result:", get_int("Enter a number from 1 to 10: ", 1, 10))
    print("Result:", get_text("Enter a title (max 20 characters): ", 1, 20))
    print("Result:", get_phone("Enter a phone number: "))