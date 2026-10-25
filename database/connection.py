import sqlite3
from pathlib import Path


class WaterGemsDatabase:
    def __init__(self, path):
        self.path = Path(path)
        if not self.path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {self.path}")

        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    def close(self):
        self.connection.close()

    def fetchall(self, sql, params=()):
        return self.connection.execute(sql, params).fetchall()

    def fetchone(self, sql, params=()):
        return self.connection.execute(sql, params).fetchone()
