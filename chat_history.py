
from database import get_connection, initialize_database


# ---------------------------------------
# 1. Create a new conversation
# ---------------------------------------

def create_conversation(user_id, title="New Chat"):
    initialize_database()

    conn = get_connection()

    try:
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO conversations (user_id, title)
            VALUES (?, ?)
        """, (user_id, title))

        conn.commit()

        return cursor.lastrowid

    finally:
        conn.close()


# ---------------------------------------
# 2. Get all conversations for one user
# ---------------------------------------

def get_user_conversations(user_id):
    initialize_database()

    conn = get_connection()

    try:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT conversation_id, title, created_at, updated_at
            FROM conversations
            WHERE user_id = ?
            ORDER BY updated_at DESC, conversation_id DESC
        """, (user_id,))

        return [dict(row) for row in cursor.fetchall()]

    finally:
        conn.close()


# ---------------------------------------
# 3. Save a message
# ---------------------------------------

def save_message(user_id, conversation_id, role, content):
    initialize_database()

    if role not in ("user", "assistant", "system"):
        return False

    if not isinstance(content, str) or not content.strip():
        return False

    conn = get_connection()

    try:
        cursor = conn.cursor()

        # Verify that this conversation belongs to this user
        cursor.execute("""
            SELECT conversation_id
            FROM conversations
            WHERE conversation_id = ? AND user_id = ?
        """, (conversation_id, user_id))

        if not cursor.fetchone():
            return False

        # Save the message
        cursor.execute("""
            INSERT INTO messages (conversation_id, role, content)
            VALUES (?, ?, ?)
        """, (conversation_id, role, content))

        # Update the conversation's last activity time
        cursor.execute("""
            UPDATE conversations
            SET updated_at = CURRENT_TIMESTAMP
            WHERE conversation_id = ? AND user_id = ?
        """, (conversation_id, user_id))

        conn.commit()
        return True

    finally:
        conn.close()


# ---------------------------------------
# 4. Load messages from a conversation
# ---------------------------------------

def get_conversation_messages(user_id, conversation_id):
    initialize_database()

    conn = get_connection()

    try:
        cursor = conn.cursor()

        # Check ownership before retrieving messages
        cursor.execute("""
            SELECT conversation_id
            FROM conversations
            WHERE conversation_id = ? AND user_id = ?
        """, (conversation_id, user_id))

        if not cursor.fetchone():
            return []

        cursor.execute("""
            SELECT message_id, role, content, created_at
            FROM messages
            WHERE conversation_id = ?
            ORDER BY message_id ASC
        """, (conversation_id,))

        return [dict(row) for row in cursor.fetchall()]

    finally:
        conn.close()


# ---------------------------------------
# 5. Rename a conversation
# ---------------------------------------

def rename_conversation(user_id, conversation_id, new_title):
    initialize_database()

    new_title = new_title.strip()

    if not new_title or len(new_title) > 100:
        return False

    conn = get_connection()

    try:
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE conversations
            SET title = ?, updated_at = CURRENT_TIMESTAMP
            WHERE conversation_id = ? AND user_id = ?
        """, (new_title, conversation_id, user_id))

        conn.commit()

        return cursor.rowcount > 0

    finally:
        conn.close()


# ---------------------------------------
# 6. Delete a conversation
# ---------------------------------------

def delete_conversation(user_id, conversation_id):
    initialize_database()

    conn = get_connection()

    try:
        cursor = conn.cursor()

        # Only delete a conversation owned by this user
        cursor.execute("""
            DELETE FROM conversations
            WHERE conversation_id = ? AND user_id = ?
        """, (conversation_id, user_id))

        conn.commit()

        return cursor.rowcount > 0

    finally:
        conn.close()
