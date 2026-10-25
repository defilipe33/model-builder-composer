import struct

from readers.common import qident
from repository.model_repository import ELEMENT_ROOTS


class WaterGemsSelectionSetRepository:
    """
    Leitor read-only de Selection Sets nativos do WaterGEMS.

    HMISelectionSet:
      - metadados básicos
      - SelectionSetElementIDs = sequência little-endian de uint32
      - membros só são decodificados quando explicitamente solicitados
    """

    def __init__(self, db, schema):
        self.db = db
        self.schema = schema
        self._name_source = self._discover_name_source()

    def _discover_name_source(self):
        """
        Tenta encontrar dinamicamente alguma tabela do modelo completo que associe
        SelectionSetID/SupportElementID a Name/Label.

        Os bancos diagnósticos usados no desenvolvimento não preservaram essa
        metainformação, então não hardcodamos uma tabela não confirmada.
        """
        for table in self.schema.tables():
            try:
                cols = self.schema.columns(table)
            except Exception:
                continue

            names = []
            for c in cols:
                name = c["name"] if isinstance(c, dict) else c
                names.append(name)

            id_col = None
            for candidate in ("SelectionSetID", "SupportElementID"):
                if candidate in names:
                    id_col = candidate
                    break

            if id_col is None:
                continue

            name_col = None
            for candidate in ("Name", "Label", "SelectionSetName", "SelectionSetLabel"):
                if candidate in names:
                    name_col = candidate
                    break

            if name_col is not None and table != "HMISelectionSet":
                return table, id_col, name_col

        return None

    def _name_for_id(self, selection_set_id):
        # Selection Sets are support/modeling elements. In Bentley model databases,
        # support-element labels are exposed through HMIModelingElement.
        if self.schema.table_exists("HMIModelingElement"):
            row = self.db.fetchone(
                """
                SELECT Label
                FROM HMIModelingElement
                WHERE ElementID=?
                  AND COALESCE(IsDeleted,0)=0
                LIMIT 1
                """,
                (selection_set_id,),
            )
            if row is not None and row["Label"] is not None:
                value = str(row["Label"]).strip()
                if value:
                    return value

        if self._name_source is None:
            return None

        table, id_col, name_col = self._name_source
        row = self.db.fetchone(
            f"""
            SELECT {qident(name_col)} AS value
            FROM {qident(table)}
            WHERE {qident(id_col)}=?
            LIMIT 1
            """,
            (selection_set_id,),
        )
        if row is None or row["value"] is None:
            return None
        value = str(row["value"]).strip()
        return value or None

    def list_sets(self):
        if not self.schema.table_exists("HMISelectionSet"):
            return []

        rows = self.db.fetchall(
            """
            SELECT SelectionSetID, SelectionSetType, SelectionSetCount
            FROM HMISelectionSet
            WHERE COALESCE(IsDeleted,0)=0
            ORDER BY SelectionSetID
            """
        )

        result = []
        for row in rows:
            sid = int(row["SelectionSetID"])
            name = self._name_for_id(sid)
            result.append(
                {
                    "id": sid,
                    "name": name or f"Selection Set {sid}",
                    "name_resolved": bool(name),
                    "type": int(row["SelectionSetType"]),
                    "count": int(row["SelectionSetCount"]),
                }
            )
        return result

    def member_ids(self, selection_set_id):
        row = self.db.fetchone(
            """
            SELECT SelectionSetCount, SelectionSetElementIDs
            FROM HMISelectionSet
            WHERE SelectionSetID=?
              AND COALESCE(IsDeleted,0)=0
            LIMIT 1
            """,
            (int(selection_set_id),),
        )

        if row is None:
            raise ValueError("Selection Set não encontrado.")

        blob = row["SelectionSetElementIDs"]
        expected = int(row["SelectionSetCount"])

        if blob is None:
            return []

        if len(blob) % 4 != 0:
            raise ValueError(
                f"SelectionSetElementIDs possui tamanho inválido ({len(blob)} bytes)."
            )

        count = len(blob) // 4
        values = list(struct.unpack("<" + ("I" * count), blob))

        if expected != count:
            raise ValueError(
                f"Selection Set declara {expected} membros, mas o BLOB contém {count}."
            )

        return values

    def group_live_members(self, selection_set_id, model_repo, batch_size=800):
        """
        Classifica membros por tipo usando as tabelas raiz, sem extrair propriedades.

        Tombstones são ignorados por meio do join HMIDomainElement.IsDeleted=0.
        IDs de tipos ainda não suportados pela aplicação ficam em `unsupported`.
        """
        member_ids = self.member_ids(selection_set_id)
        if not member_ids:
            return {}, []

        remaining = set(member_ids)
        grouped = {}

        for element_type, table in ELEMENT_ROOTS.items():
            if not remaining or not self.schema.table_exists(table):
                continue

            found = set()
            ids_list = list(remaining)

            for start in range(0, len(ids_list), batch_size):
                batch = ids_list[start:start + batch_size]
                placeholders = ",".join("?" for _ in batch)

                if self.schema.table_exists("HMIDomainElement"):
                    sql = f"""
                        SELECT DISTINCT r.DomainElementID
                        FROM {qident(table)} r
                        JOIN HMIDomainElement d
                          ON d.DomainElementID=r.DomainElementID
                         AND COALESCE(d.IsDeleted,0)=0
                        WHERE r.DomainElementID IN ({placeholders})
                    """
                else:
                    sql = f"""
                        SELECT DISTINCT r.DomainElementID
                        FROM {qident(table)} r
                        WHERE r.DomainElementID IN ({placeholders})
                    """

                rows = self.db.fetchall(sql, tuple(batch))
                found.update(int(r["DomainElementID"]) for r in rows)

            if found:
                grouped[element_type] = found
                remaining.difference_update(found)

        return grouped, sorted(remaining)
