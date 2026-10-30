
import sqlite3
import hashlib
import hmac
import secrets

from database import get_connection, initialize_database


def hash_password(password):
    salt = secrets.token_bytes(16)

    password_hash = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=2**14,
        r=8,
        p=1
    )

    return salt.hex() + ":" + password_hash.hex()


def verify_password(password, stored_hash):
    try:
        salt_hex, hash_hex = stored_hash.split(":")
        salt = bytes.fromhex(salt_hex)

        new_hash = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=2**14,
            r=8,
            p=1
        )

        return hmac.compare_digest(new_hash.hex(), hash_hex)

    except (ValueError, TypeError):
        return False


def register_user(username, email, password):
    initialize_database()

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO users
            (username, email, password_hash, role)
            VALUES (?, ?, ?, 'user')
        """, (username, email, hash_password(password)))

        conn.commit()
        return True, "Account created successfully."

    except sqlite3.IntegrityError:
        return False, "Username or email already exists."

    finally:
        conn.close()


def login_user(username, password):
    initialize_database()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT user_id, username, password_hash, role
        FROM users
        WHERE username = ? AND is_active = 1
    """, (username,))

    user = cursor.fetchone()
    conn.close()

    if user and verify_password(password, user[2]):
        return {
            "user_id": user[0],
            "username": user[1],
            "role": user[3]
        }

    return None


def validate_account(username, email, password):
    if not all(isinstance(value, str) for value in (username, email, password)):
        return False, "Username, email, and password are required."

    if not username.strip() or not email.strip() or not password:
        return False, "Username, email, and password are required."

    if "@" not in email.strip():
        return False, "Please provide a valid email address."

    return True, "Account details are valid."


def create_first_admin(username, email, password):
    initialize_database()

    valid, message = validate_account(username, email, password)

    if not valid:
        return False, message

    conn = get_connection()

    try:
        cursor = conn.cursor()

        cursor.execute(
            "SELECT user_id FROM users WHERE role = 'admin' LIMIT 1"
        )

        if cursor.fetchone():
            return False, "An admin account already exists."

        cursor.execute("""
            INSERT INTO users
            (username, email, password_hash, role)
            VALUES (?, ?, ?, 'admin')
        """, (
            username.strip(),
            email.strip().lower(),
            hash_password(password)
        ))

        conn.commit()
        return True, "First admin account created successfully."

    except sqlite3.IntegrityError:
        return False, "Username or email already exists."

    finally:
        conn.close()

