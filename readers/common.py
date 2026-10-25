def qident(name):
    return '"' + name.replace('"', '""') + '"'


class CommonReader:
    def __init__(self, db, schema):
        self.db = db
        self.schema = schema

    def label(self, element_id):
        table = "HMIModelingElement"
        if not self.schema.table_exists(table):
            return ""

        cols = self.schema.columns(table)
        id_col = "ElementID" if "ElementID" in cols else "DomainElementID"

        row = self.db.fetchone(
            f"SELECT Label FROM {qident(table)} WHERE {qident(id_col)}=? LIMIT 1",
            (element_id,),
        )
        return "" if row is None else (row["Label"] or "")

    def labels(self, element_ids):
        """Resolve labels in batches instead of issuing one query per ID."""
        table = "HMIModelingElement"
        if not self.schema.table_exists(table):
            return {}

        cols = self.schema.columns(table)
        id_col = "ElementID" if "ElementID" in cols else "DomainElementID"
        result = {}
        ids = [int(element_id) for element_id in set(element_ids)]
        for start in range(0, len(ids), 900):
            batch = ids[start:start + 900]
            placeholders = ",".join("?" for _ in batch)
            rows = self.db.fetchall(
                f"SELECT {qident(id_col)} AS ElementID, Label "
                f"FROM {qident(table)} "
                f"WHERE {qident(id_col)} IN ({placeholders})",
                tuple(batch),
            )
            result.update({
                int(row["ElementID"]): row["Label"] or ""
                for row in rows
            })
        return result

    def root_ids(self, table):
        if not self.schema.table_exists(table):
            return []
        if "DomainElementID" not in self.schema.columns(table):
            return []

        rows = self.db.fetchall(
            f"""
            SELECT DISTINCT DomainElementID
            FROM {qident(table)}
            WHERE DomainElementID IS NOT NULL
            ORDER BY DomainElementID
            """
        )
        return [r["DomainElementID"] for r in rows]
