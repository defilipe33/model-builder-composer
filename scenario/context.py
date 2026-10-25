from dataclasses import dataclass


ALTERNATIVE_TYPES = {
    "geometry": 1,
    "topology": 2,
    "active_topology": 3,
    "physical": 4,
    "initial_settings": 21,
    "udx": 100,
}


@dataclass
class ScenarioContext:
    selected_scenario_id: int
    active_scenario_id: int | None
    scenario_chain: list[int]
    alternatives_by_type: dict[int, list[tuple[int, int]]]

    def alternatives(self, alternative_type_id):
        return self.alternatives_by_type.get(alternative_type_id, [])
