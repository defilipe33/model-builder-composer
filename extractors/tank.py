from extractors.base import BaseExtractor
from models.elements import NodeElement
from models.stats import ExtractionStats


class TankExtractor(BaseExtractor):
    def extract_all(self):
        result = {}
        stats_map = {}

        conventional_ids = set(self.root_ids("ConventionalTank"))

        configs = [
            {
                "type": "Conventional Tank",
                "ids": sorted(conventional_ids),
                "physical": [
                    "BaseIdahoNode_Physical_Data",
                    "BaseTank_Physical_Data",
                    "IdahoTank_Physical_Data",
                    "ConventionalTank_Physical_Data",
                ],
                "udx": "ConventionalTank_HMIUserDefinedExtensions_Data",
            },
            {
                "type": "Tank",
                "ids": [
                    i for i in self.root_ids("IdahoTank")
                    if i not in conventional_ids
                ],
                "physical": [
                    "BaseIdahoNode_Physical_Data",
                    "BaseTank_Physical_Data",
                    "IdahoTank_Physical_Data",
                ],
                "udx": "IdahoTank_HMIUserDefinedExtensions_Data",
            },
        ]

        for config in configs:
            items = []
            stats = ExtractionStats(config["type"])

            for element_id in config["ids"]:
                stats.examined += 1
                label = self.common.label(element_id)

                is_active, active_source, active_alt = self.resolve_active_topology(
                    element_id,
                    "BaseIdahoNode_HMIActiveTopology_Data",
                    stats,
                    label,
                )

                geometry, _, geometry_source, geometry_alt = self.readers.geometry(
                    "BaseIdahoNode_HmiDataSetGeometry_Data",
                    element_id,
                    self.context,
                )
                if not isinstance(geometry, tuple):
                    stats.invalid_geometry += 1
                    stats.add_issue(
                        element_id, label, "Geometry unresolved",
                        "Tank geometry was not resolved as a Point.",
                    )
                    x = y = None
                else:
                    x, y = geometry

                physical, physical_prov = self.readers.physical(
                    config["physical"], element_id, self.context
                )
                phys_scenarios, phys_alts = self.physical_provenance(physical_prov)

                if not physical:
                    stats.missing_physical += 1
                    stats.add_issue(
                        element_id, label, "Physical unresolved",
                        "No physical record was resolved.",
                    )

                items.append(
                    NodeElement(
                        id=element_id,
                        label=label,
                        element_type=config["type"],
                        is_active=is_active,
                        active_topology_source_scenario_id=active_source,
                        active_topology_alternative_id=active_alt,
                        geometry_source_scenario_id=geometry_source,
                        geometry_alternative_id=geometry_alt,
                        physical_source_scenario_ids=phys_scenarios,
                        physical_alternative_ids=phys_alts,
                        x_ft=x,
                        y_ft=y,
                        elevation_ft=physical.get("Physical_NodeElevation"),
                        physical=physical,
                        udx=self.readers.udx(
                            config["udx"], element_id, self.context
                        ),
                    )
                )
                stats.exported += 1

            result[config["type"]] = items
            stats_map[config["type"]] = stats

        return result, stats_map
