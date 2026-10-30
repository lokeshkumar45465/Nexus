import sqlite3
from pathlib import Path

# Find the main project directory
BASE_DIR = Path(__file__).resolve().parent

# Create database storage folder
DB_DIR = BASE_DIR / "database"
DB_DIR.mkdir(exist_ok=True)

# Database file location
DB_PATH = DB_DIR / "edgesight.db"


# Connect to SQLite database
def get_connection():
    conn = sqlite3.connect(DB_PATH)

    # Enable foreign key relationships
    conn.execute("PRAGMA foreign_keys = ON")

    # Return rows that can be accessed by column name
    conn.row_factory = sqlite3.Row

    return conn


# Create all required database tables
def initialize_database():

    conn = get_connection()

    try:
        cursor = conn.cursor()

        # 1. Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user'
                    CHECK(role IN ('user', 'admin')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active INTEGER NOT NULL DEFAULT 1
                    CHECK(is_active IN (0, 1))
            )
        """)

        # 2. Conversations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                conversation_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL DEFAULT 'New Chat',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (user_id)
                    REFERENCES users(user_id)
                    ON DELETE CASCADE
            )
        """)

        # 3. Messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL,
                role TEXT NOT NULL
                    CHECK(role IN ('user', 'assistant', 'system')),
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (conversation_id)
                    REFERENCES conversations(conversation_id)
                    ON DELETE CASCADE
            )
        """)

        # Improve conversation lookup performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS
            idx_conversations_user
            ON conversations(user_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS
            idx_messages_conversation
            ON messages(conversation_id)
        """)

        conn.commit()

        print("Database initialized successfully!")

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()
