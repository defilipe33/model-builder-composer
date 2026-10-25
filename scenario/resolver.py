from readers.common import qident
from scenario.context import ScenarioContext


class AlternativeResolver:
    def __init__(self, db, schema):
        self.db = db
        self.schema = schema

    def build_context(self, selected_scenario_id):
        rows = self.db.fetchall(
            """
            SELECT ScenarioID, ParentID
            FROM HMIScenario
            WHERE COALESCE(IsDeleted, 0)=0
            """
        )
        parents = {r["ScenarioID"]: r["ParentID"] for r in rows}

        if selected_scenario_id not in parents:
            raise ValueError(f"Cenário inexistente: {selected_scenario_id}")

        chain = []
        current = selected_scenario_id
        seen = set()

        while current is not None:
            if current in seen:
                raise ValueError("Ciclo encontrado na árvore de cenários.")
            seen.add(current)
            chain.append(current)
            current = parents.get(current)

        active_row = self.db.fetchone(
            """
            SELECT ActiveScenarioID
            FROM HMIDomainDataSet
            WHERE ActiveScenarioID IS NOT NULL
            ORDER BY DomainDataSetID
            LIMIT 1
            """
        )
        active_id = None if active_row is None else active_row["ActiveScenarioID"]

        alternatives_by_type = {}

        if self.schema.table_exists("HMIScenarioAlternative"):
            rows = self.db.fetchall(
                """
                SELECT ScenarioID, AlternativeTypeID, AlternativeID
                FROM HMIScenarioAlternative
                """
            )
            lookup = {
                (r["ScenarioID"], r["AlternativeTypeID"]): r["AlternativeID"]
                for r in rows
            }

            type_ids = sorted({r["AlternativeTypeID"] for r in rows})

            for type_id in type_ids:
                values = []
                used_alt_ids = set()
                for scenario_id in chain:
                    alt_id = lookup.get((scenario_id, type_id))
                    if alt_id is None or alt_id in used_alt_ids:
                        continue
                    used_alt_ids.add(alt_id)
                    values.append((scenario_id, alt_id))
                alternatives_by_type[type_id] = values

        return ScenarioContext(
            selected_scenario_id=selected_scenario_id,
            active_scenario_id=active_id,
            scenario_chain=chain,
            alternatives_by_type=alternatives_by_type,
        )

    def resolve_row(self, table, element_id, alternative_type_id, context):
        if not self.schema.table_exists(table):
            return None, None, None

        cols = self.schema.columns(table)
        if "DomainElementID" not in cols:
            return None, None, None

        if "AlternativeID" not in cols:
            row = self.db.fetchone(
                f"""
                SELECT *
                FROM {qident(table)}
                WHERE DomainElementID=?
                LIMIT 1
                """,
                (element_id,),
            )
            return row, None, None

        for scenario_id, alternative_id in context.alternatives(alternative_type_id):
            row = self.db.fetchone(
                f"""
                SELECT *
                FROM {qident(table)}
                WHERE DomainElementID=?
                  AND AlternativeID=?
                LIMIT 1
                """,
                (element_id, alternative_id),
            )
            if row is not None:
                return row, scenario_id, alternative_id

        return None, None, None

    def resolve_dict(self, table, element_id, alternative_type_id, context):
        row, source_scenario, alternative_id = self.resolve_row(
            table, element_id, alternative_type_id, context
        )
        if row is None:
            return {}, source_scenario, alternative_id

        data = {
            k: row[k]
            for k in row.keys()
            if k not in {"DomainElementID", "AlternativeID"}
        }
        return data, source_scenario, alternative_id
