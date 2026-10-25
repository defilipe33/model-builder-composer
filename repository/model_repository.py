from readers.common import qident


ELEMENT_ROOTS = {
    "Pipe": "IdahoPipe",
    "Junction": "IdahoJunction",
    "Reservoir": "IdahoReservoir",
    "Air Valve": "AirValve",
    "Hydrant": "IdahoHydrant",
    "Tank": "IdahoTank",
    "Conventional Tank": "ConventionalTank",
    "TCV": "TCV",
    "FCV": "FCV",
    "PRV": "PRV",
    "PBV": "PBV",
    "Check Valve": "CheckValve",
    "Standard Pump": "StandardPump",
    "Variable Speed Pump Battery": "VariableSpeedPumpBattery",
    "Customer Meter": "CustomerNode",
}


class ModelRepository:
    def __init__(self, db, schema, common, resolver, context):
        self.db = db
        self.schema = schema
        self.common = common
        self.resolver = resolver
        self.context = context

    def available_types(self):
        result = []
        for element_type, root in ELEMENT_ROOTS.items():
            if not self.schema.table_exists(root):
                continue
            count = self.count_type(element_type)
            if count > 0:
                result.append((element_type, count))
        return result

    def root_table(self, element_type):
        try:
            return ELEMENT_ROOTS[element_type]
        except KeyError:
            raise ValueError(f"Tipo não suportado: {element_type}")

    def _live_join(self, alias="r"):
        """
        WaterGEMS mantém tombstones nas tabelas raiz após exclusão.
        HMIDomainElement.IsDeleted define se o elemento ainda pertence ao modelo.
        """
        if self.schema.table_exists("HMIDomainElement"):
            return (
                "JOIN HMIDomainElement d "
                f"ON d.DomainElementID = {alias}.DomainElementID "
                "AND COALESCE(d.IsDeleted, 0)=0"
            )

        if self.schema.table_exists("HMIModelingElement"):
            return (
                "JOIN HMIModelingElement d "
                f"ON d.ElementID = {alias}.DomainElementID "
                "AND COALESCE(d.IsDeleted, 0)=0"
            )

        return ""

    def count_type(self, element_type):
        table = self.root_table(element_type)
        if not self.schema.table_exists(table):
            return 0

        join = self._live_join("r")
        row = self.db.fetchone(
            f"""
            SELECT COUNT(DISTINCT r.DomainElementID) AS n
            FROM {qident(table)} r
            {join}
            WHERE r.DomainElementID IS NOT NULL
            """
        )
        return int(row["n"])

    def count_deleted_type(self, element_type):
        table = self.root_table(element_type)
        if (
            not self.schema.table_exists(table)
            or not self.schema.table_exists("HMIDomainElement")
        ):
            return 0

        row = self.db.fetchone(
            f"""
            SELECT COUNT(DISTINCT r.DomainElementID) AS n
            FROM {qident(table)} r
            JOIN HMIDomainElement d
              ON d.DomainElementID=r.DomainElementID
            WHERE r.DomainElementID IS NOT NULL
              AND COALESCE(d.IsDeleted, 0)<>0
            """
        )
        return int(row["n"])

    def root_ids(self, element_type, limit=None, offset=0):
        table = self.root_table(element_type)
        join = self._live_join("r")

        sql = (
            f"SELECT DISTINCT r.DomainElementID "
            f"FROM {qident(table)} r "
            f"{join} "
            f"WHERE r.DomainElementID IS NOT NULL "
            f"ORDER BY r.DomainElementID"
        )
        params = []
        if limit is not None:
            sql += " LIMIT ? OFFSET ?"
            params.extend([int(limit), int(offset)])

        rows = self.db.fetchall(sql, tuple(params))
        return [r["DomainElementID"] for r in rows]

    def label_for_id(self, element_id):
        return self.common.label(element_id)

    def preview(self, element_type, limit=200, offset=0):
        ids = self.root_ids(element_type, limit=limit, offset=offset)
        return [
            {
                "element_type": element_type,
                "id": element_id,
                "label": self.label_for_id(element_id),
            }
            for element_id in ids
        ]


    def find_ids_by_label(self, element_type, labels):
        labels = [str(x) for x in labels]
        if not labels:
            return []

        table = self.root_table(element_type)
        placeholders = ",".join("?" for _ in labels)
        live_join = self._live_join("r")

        rows = self.db.fetchall(
            f"""
            SELECT DISTINCT r.DomainElementID
            FROM {qident(table)} r
            {live_join}
            JOIN HMIModelingElement h
              ON h.ElementID = r.DomainElementID
            WHERE h.Label IN ({placeholders})
              AND COALESCE(h.IsDeleted, 0)=0
            """,
            tuple(labels),
        )
        return [r["DomainElementID"] for r in rows]

    def is_deleted_id(self, element_id):
        if self.schema.table_exists("HMIDomainElement"):
            row = self.db.fetchone(
                """
                SELECT COALESCE(IsDeleted,0) AS IsDeleted
                FROM HMIDomainElement
                WHERE DomainElementID=?
                LIMIT 1
                """,
                (element_id,),
            )
            return row is not None and bool(row["IsDeleted"])

        if self.schema.table_exists("HMIModelingElement"):
            row = self.db.fetchone(
                """
                SELECT COALESCE(IsDeleted,0) AS IsDeleted
                FROM HMIModelingElement
                WHERE ElementID=?
                LIMIT 1
                """,
                (element_id,),
            )
            return row is not None and bool(row["IsDeleted"])

        return False

    def is_live_id(self, element_id):
        if self.schema.table_exists("HMIDomainElement"):
            row = self.db.fetchone(
                """
                SELECT COALESCE(IsDeleted,0) AS IsDeleted
                FROM HMIDomainElement
                WHERE DomainElementID=?
                LIMIT 1
                """,
                (element_id,),
            )
            return row is not None and not bool(row["IsDeleted"])

        if self.schema.table_exists("HMIModelingElement"):
            row = self.db.fetchone(
                """
                SELECT COALESCE(IsDeleted,0) AS IsDeleted
                FROM HMIModelingElement
                WHERE ElementID=?
                LIMIT 1
                """,
                (element_id,),
            )
            return row is not None and not bool(row["IsDeleted"])

        return True

    def has_id(self, element_type, element_id):
        table = self.root_table(element_type)
        join = self._live_join("r")

        row = self.db.fetchone(
            f"""
            SELECT 1
            FROM {qident(table)} r
            {join}
            WHERE r.DomainElementID=?
            LIMIT 1
            """,
            (element_id,),
        )
        return row is not None
