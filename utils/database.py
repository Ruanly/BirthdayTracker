import sqlite3


class DatabaseConnection:
    """A context manager for a sqlite3 connection."""

    def __enter__(self):
        self.conn = sqlite3.connect('data.db')
        cursor = self.conn.cursor()
        return cursor

    def __exit__(self, exception_type, exception_value, exception_traceback):
        self.conn.commit()
        self.conn.close()