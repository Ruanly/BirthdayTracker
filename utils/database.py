import psycopg2


class DatabaseConnection:
    """A context manager for a sqlite3 connection."""

    def __init__(self, url):
        self.database_url = url

    def __enter__(self):
        self.conn = psycopg2.connect(self.database_url, sslmode='require')
        cursor = self.conn.cursor()
        return cursor

    def __exit__(self, exception_type, exception_value, exception_traceback):
        self.conn.commit()
        self.conn.close()