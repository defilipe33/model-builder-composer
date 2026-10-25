class SchemaInspector:
    def __init__(self, db):
        self.db = db
        self._tables = None
        self._columns = {}

    def tables(self):
        if self._tables is None:
            rows = self.db.fetchall(
                """
                SELECT name
                FROM sqlite_master
                WHERE type='table'
                  AND name NOT LIKE 'sqlite_%'
                """
            )
            self._tables = {r["name"] for r in rows}
        return self._tables

    def table_exists(self, name):
        return name in self.tables()

    def columns(self, name):
        if name not in self._columns:
            if not self.table_exists(name):
                self._columns[name] = []
            else:
                safe = name.replace('"', '""')
                rows = self.db.fetchall(f'PRAGMA table_info("{safe}")')
                self._columns[name] = [r["name"] for r in rows]
        return self._columns[name]
