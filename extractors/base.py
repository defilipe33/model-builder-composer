class BaseExtractor:
    def __init__(self, db, schema, common, readers, context):
        self.db = db
        self.schema = schema
        self.common = common
        self.readers = readers
        self.context = context

    def root_ids(self, table):
        return self.common.root_ids(table)

    def resolve_active_topology(self, element_id, active_table, stats, label=""):
        state, source_scenario, alt_id = self.readers.active_state(
            active_table, element_id, self.context
        )

        if state is None:
            stats.unresolved_active_topology += 1
            stats.add_issue(
                element_id,
                label,
                "Active Topology unresolved",
                f"No record resolved in {active_table}",
            )
        elif state:
            stats.active += 1
        else:
            stats.inactive += 1

        return state, source_scenario, alt_id

    @staticmethod
    def physical_provenance(provenance):
        scenario_ids = []
        alternative_ids = []

        for _, (scenario_id, alternative_id) in provenance.items():
            if scenario_id is not None and scenario_id not in scenario_ids:
                scenario_ids.append(scenario_id)
            if alternative_id is not None and alternative_id not in alternative_ids:
                alternative_ids.append(alternative_id)

        return scenario_ids, alternative_ids
