from extractors.base import BaseExtractor
from models.elements import NodeElement
from models.stats import ExtractionStats


NODE_CONFIGS = [
    {
        "type": "Junction",
        "root": "IdahoJunction",
        "active": "BaseIdahoNode_HMIActiveTopology_Data",
        "geometry": "BaseIdahoNode_HmiDataSetGeometry_Data",
        "physical": ["BaseIdahoNode_Physical_Data", "IdahoJunction_Physical_Data"],
        "udx": "IdahoJunction_HMIUserDefinedExtensions_Data",
    },
    {
        "type": "Reservoir",
        "root": "IdahoReservoir",
        "active": "BaseIdahoNode_HMIActiveTopology_Data",
        "geometry": "BaseIdahoNode_HmiDataSetGeometry_Data",
        "physical": ["BaseIdahoNode_Physical_Data", "IdahoReservoir_Physical_Data"],
        "udx": "IdahoReservoir_HMIUserDefinedExtensions_Data",
    },
    {
        "type": "Air Valve",
        "root": "AirValve",
        "active": "BaseIdahoNode_HMIActiveTopology_Data",
        "geometry": "BaseIdahoNode_HmiDataSetGeometry_Data",
        "physical": ["BaseIdahoNode_Physical_Data", "AirValve_Physical_Data"],
        "udx": "AirValve_HMIUserDefinedExtensions_Data",
    },
    {
        "type": "Hydrant",
        "root": "IdahoHydrant",
        "active": "BaseIdahoNode_HMIActiveTopology_Data",
        "geometry": "BaseIdahoNode_HmiDataSetGeometry_Data",
        "physical": ["BaseIdahoNode_Physical_Data", "IdahoHydrant_Physical_Data"],
        "udx": "IdahoHydrant_HMIUserDefinedExtensions_Data",
    },
]


class NodeExtractor(BaseExtractor):
    def extract_config(self, config):
        items = []
        stats = ExtractionStats(config["type"])

        for element_id in self.root_ids(config["root"]):
            stats.examined += 1
            label = self.common.label(element_id)

            is_active, active_source, active_alt = self.resolve_active_topology(
                element_id, config["active"], stats, label
            )

            geometry, _, geometry_source, geometry_alt = self.readers.geometry(
                config["geometry"], element_id, self.context
            )
            if not isinstance(geometry, tuple):
                stats.invalid_geometry += 1
                stats.add_issue(
                    element_id, label, "Geometry unresolved",
                    "Node geometry was not resolved as a Point.",
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

        return items, stats

    def extract_all(self):
        result = {}
        stats = {}
        for config in NODE_CONFIGS:
            elements, s = self.extract_config(config)
            result[config["type"]] = elements
            stats[config["type"]] = s
        return result, stats
