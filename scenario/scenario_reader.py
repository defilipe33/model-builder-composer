from dataclasses import dataclass


@dataclass
class Scenario:
    id: int
    parent_id: int | None
    domain_dataset_id: int
    is_active: bool = False
    depth: int = 0
    name: str | None = None

    @property
    def display_name(self):
        if self.name:
            return self.name
        return "Base" if self.parent_id is None else f"Scenario {self.id}"


class ScenarioReader:
    def __init__(self, db, schema):
        self.db = db
        self.schema = schema
        self._name_source = self._discover_name_source()

    def active_scenario_id(self):
        if not self.schema.table_exists("HMIDomainDataSet"):
            return None

        row = self.db.fetchone(
            """
            SELECT ActiveScenarioID
            FROM HMIDomainDataSet
            WHERE ActiveScenarioID IS NOT NULL
            ORDER BY DomainDataSetID
            LIMIT 1
            """
        )
        return None if row is None else row["ActiveScenarioID"]

    def _discover_name_source(self):
        """
        Alguns bancos Bentley armazenam nomes de support elements em estruturas
        auxiliares. Procuramos, de modo conservador, tabelas que contenham um
        identificador de cenário + Name/Label.
        """
        for table in self.schema.tables():
            try:
                cols = self.schema.columns(table)
            except Exception:
                continue

            names = []
            for c in cols:
                names.append(c["name"] if isinstance(c, dict) else c)

            id_col = None
            for candidate in (
                "ScenarioID",
                "SupportElementID",
                "ElementID",
            ):
                if candidate in names:
                    id_col = candidate
                    break

            if id_col is None:
                continue

            name_col = None
            for candidate in (
                "ScenarioName",
                "Name",
                "ScenarioLabel",
                "Label",
                "SmartLabel",
            ):
                if candidate in names:
                    name_col = candidate
                    break

            if name_col is not None and table not in {
                "HMIScenario",
                "HMIModelingElement",
            }:
                return table, id_col, name_col

        return None

    def _scenario_name(self, scenario_id):
        # First choice: same support-element labeling pattern that works for
        # Selection Sets in full WaterGEMS databases.
        if self.schema.table_exists("HMIModelingElement"):
            row = self.db.fetchone(
                """
                SELECT Label, SmartLabel
                FROM HMIModelingElement
                WHERE ElementID=?
                  AND COALESCE(IsDeleted,0)=0
                LIMIT 1
                """,
                (int(scenario_id),),
            )
            if row is not None:
                for key in ("Label", "SmartLabel"):
                    value = row[key]
                    if value is not None and str(value).strip():
                        return str(value).strip()

        if self._name_source is not None:
            table, id_col, name_col = self._name_source
            # qident isn't needed here because names come only from schema
            # introspection, but quote defensively anyway.
            qt = '"' + table.replace('"', '""') + '"'
            qi = '"' + id_col.replace('"', '""') + '"'
            qn = '"' + name_col.replace('"', '""') + '"'
            row = self.db.fetchone(
                f"""
                SELECT {qn} AS value
                FROM {qt}
                WHERE {qi}=?
                LIMIT 1
                """,
                (int(scenario_id),),
            )
            if row is not None and row["value"] is not None:
                value = str(row["value"]).strip()
                if value:
                    return value

        return None

    def scenarios(self):
        if not self.schema.table_exists("HMIScenario"):
            return []

        active_id = self.active_scenario_id()
        rows = self.db.fetchall(
            """
            SELECT ScenarioID, ParentID, DomainDataSetID
            FROM HMIScenario
            WHERE COALESCE(IsDeleted, 0)=0
            ORDER BY ScenarioID
            """
        )

        by_id = {
            r["ScenarioID"]: Scenario(
                id=r["ScenarioID"],
                parent_id=r["ParentID"],
                domain_dataset_id=r["DomainDataSetID"],
                is_active=(r["ScenarioID"] == active_id),
                name=self._scenario_name(r["ScenarioID"]),
            )
            for r in rows
        }

        def depth(scenario_id, seen=None):
            seen = set() if seen is None else set(seen)
            if scenario_id in seen:
                return 0
            seen.add(scenario_id)
            s = by_id[scenario_id]
            if s.parent_id is None or s.parent_id not in by_id:
                return 0
            return 1 + depth(s.parent_id, seen)

        for s in by_id.values():
            s.depth = depth(s.id)

        return list(by_id.values())

    def tree_order(self):
        scenarios = self.scenarios()
        by_parent = {}
        for s in scenarios:
            by_parent.setdefault(s.parent_id, []).append(s)

        for children in by_parent.values():
            children.sort(key=lambda s: (s.display_name.casefold(), s.id))

        result = []

        def visit(parent_id):
            for s in by_parent.get(parent_id, []):
                result.append(s)
                visit(s.id)

        visit(None)

        known = {s.id for s in result}
        for s in sorted(scenarios, key=lambda x: x.id):
            if s.id not in known:
                result.append(s)

        return result
