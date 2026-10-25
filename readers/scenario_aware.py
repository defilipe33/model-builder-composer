from readers.geometry import read_wkb


class ScenarioAwareReaders:
    def __init__(self, resolver):
        self.resolver = resolver

    def active_state(self, table, element_id, context):
        row, source_scenario, alt_id = self.resolver.resolve_row(
            table, element_id, 3, context
        )
        if row is None:
            return None, source_scenario, alt_id

        value = row["HMIActiveTopologyIsActive"]
        if value is None:
            return None, source_scenario, alt_id

        return bool(value), source_scenario, alt_id

    def geometry(self, table, element_id, context):
        row, source_scenario, alt_id = self.resolver.resolve_row(
            table, element_id, 1, context
        )
        if row is None:
            return None, None, source_scenario, alt_id

        geometry = read_wkb(row["HMIGeometry"]) if row["HMIGeometry"] is not None else None
        length = (
            row["HMIGeometryScaledLength"]
            if "HMIGeometryScaledLength" in row.keys()
            else None
        )
        return geometry, length, source_scenario, alt_id

    def topology(self, table, element_id, context):
        return self.resolver.resolve_row(table, element_id, 2, context)

    def physical(self, tables, element_id, context):
        merged = {}
        provenance = {}
        for table in tables:
            data, source_scenario, alt_id = self.resolver.resolve_dict(
                table, element_id, 4, context
            )
            if data:
                merged.update(data)
                provenance[table] = (source_scenario, alt_id)
        return merged, provenance

    def initial_settings(self, table, element_id, context):
        if not table:
            return {}
        data, _, _ = self.resolver.resolve_dict(
            table, element_id, 21, context
        )
        return data

    def udx(self, table, element_id, context):
        if not table:
            return {}
        data, _, _ = self.resolver.resolve_dict(
            table, element_id, 100, context
        )
        return data
