# Vulnerable code sample: SQL Injection
# These patterns should be detected by SecurityChecker


def get_user_by_id(user_id):
    """Vulnerable: SQL injection via f-string."""
    query = f"SELECT * FROM users WHERE id = {user_id}"
    return db.execute(query)


def search_users(name):
    """Vulnerable: SQL injection with string formatting."""
    query = f"SELECT * FROM users WHERE name LIKE '%{name}%'"
    return db.execute(query)


def delete_user(user_id):
    """Vulnerable: SQL injection in DELETE statement."""
    sql = f"DELETE FROM users WHERE id = {user_id}"
    cursor.execute(sql)


def update_email(user_id, new_email):
    """Vulnerable: SQL injection in UPDATE statement."""
    query = f"UPDATE users SET email = '{new_email}' WHERE id = {user_id}"
    db.execute(query)
