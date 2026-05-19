"""
Run lightweight ALTER TABLE migrations on startup.
SQLAlchemy create_all() won't add columns to existing tables,
so we do it manually with raw SQL (SQLite supports ADD COLUMN).
"""
from sqlalchemy import text
from sqlalchemy.orm import Session


_MIGRATIONS = [
    # OAuthToken: drop old unique constraint on provider (handled by recreate),
    # add user_id column
    ("oauth_tokens",      "user_id",    "ALTER TABLE oauth_tokens ADD COLUMN user_id INTEGER REFERENCES users(id)"),
    ("email_history",     "user_id",    "ALTER TABLE email_history ADD COLUMN user_id INTEGER REFERENCES users(id)"),
    ("sender_profiles",   "user_id",    "ALTER TABLE sender_profiles ADD COLUMN user_id INTEGER REFERENCES users(id)"),
    ("conversation_turns","user_id",    "ALTER TABLE conversation_turns ADD COLUMN user_id INTEGER REFERENCES users(id)"),
    ("conversation_summaries","user_id","ALTER TABLE conversation_summaries ADD COLUMN user_id INTEGER REFERENCES users(id)"),
]


def run(engine):
    with engine.connect() as conn:
        for table, column, sql in _MIGRATIONS:
            # Check if column already exists
            try:
                existing = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
                col_names = [row[1] for row in existing]
                if column not in col_names:
                    conn.execute(text(sql))
                    conn.commit()
            except Exception:
                pass  # Table might not exist yet (first run)
