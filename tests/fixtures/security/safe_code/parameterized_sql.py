# Safe code sample: Parameterized SQL Queries
# These patterns should NOT trigger security warnings


def get_user_by_id(user_id):
    """Safe: Parameterized query with placeholder."""
    query = "SELECT * FROM users WHERE id = ?"
    return db.execute(query, (user_id,))


def search_users(name):
    """Safe: Parameterized LIKE query."""
    query = "SELECT * FROM users WHERE name LIKE ?"
    return db.execute(query, (f"%{name}%",))


def delete_user(user_id):
    """Safe: Parameterized DELETE with named parameter."""
    sql = "DELETE FROM users WHERE id = :user_id"
    cursor.execute(sql, {"user_id": user_id})


def update_email(user_id, new_email):
    """Safe: Parameterized UPDATE with positional parameters."""
    query = "UPDATE users SET email = %s WHERE id = %s"
    db.execute(query, (new_email, user_id))


# Safe: Using SQLAlchemy ORM
def get_user_orm(user_id):
    """Safe: Using ORM query instead of raw SQL."""
    return User.query.filter_by(id=user_id).first()


# Safe: Using prepared statements
def insert_user(name, email):
    """Safe: Prepared statement with parameters."""
    stmt = text("INSERT INTO users (name, email) VALUES (:name, :email)")
    db.execute(stmt, {"name": name, "email": email})
