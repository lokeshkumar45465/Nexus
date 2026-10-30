from getpass import getpass

from auth import create_first_admin


def main():

    print("\n================================")
    print(" EDGE SIGHT - ADMIN SETUP")
    print("================================\n")

    username = input("Enter admin username: ").strip()
    email = input("Enter admin email: ").strip()

    password = getpass("Enter admin password: ")
    confirm_password = getpass("Confirm admin password: ")

    if password != confirm_password:
        print("\nPasswords do not match.")
        return

    success, message = create_first_admin(
        username,
        email,
        password
    )

    print("\n" + message)


if __name__ == "__main__":
    main()
