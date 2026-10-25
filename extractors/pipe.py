from extractors.base import BaseExtractor
from models.elements import LinkElement
from models.stats import ExtractionStats


class PipeExtractor(BaseExtractor):
    def extract_all(self):
        items = []
        stats = ExtractionStats("Pipe")

        for element_id in self.root_ids("IdahoPipe"):
            stats.examined += 1
            label = self.common.label(element_id)

            is_active, active_source, active_alt = self.resolve_active_topology(
                element_id,
                "BaseLink_HMIActiveTopology_Data",
                stats,
                label,
            )

            geometry, length, geometry_source, geometry_alt = self.readers.geometry(
                "BaseLink_HmiDataSetGeometry_Data",
                element_id,
                self.context,
            )

            topology_row, topology_source, topology_alt = self.readers.topology(
                "BaseLink_HMIDataSetTopology_Data",
                element_id,
                self.context,
            )

            if not isinstance(geometry, list):
                stats.invalid_geometry += 1
                stats.add_issue(
                    element_id, label, "Geometry unresolved",
                    "Pipe geometry was not resolved as a LineString.",
                )

            if topology_row is None:
                stats.invalid_topology += 1
                stats.add_issue(
                    element_id, label, "Topology unresolved",
                    "Start/end node topology could not be resolved.",
                )
                start_id = None
                end_id = None
            else:
                start_id = topology_row["HMITopologyStartNodeID"]
                end_id = topology_row["HMITopologyStopNodeID"]

            physical, physical_prov = self.readers.physical(
                ["BaseLink_Physical_Data", "IdahoPipe_Physical_Data"],
                element_id,
                self.context,
            )
            phys_scenarios, phys_alts = self.physical_provenance(physical_prov)

            if not physical:
                stats.missing_physical += 1
                stats.add_issue(
                    element_id, label, "Physical unresolved",
                    "No physical record was resolved.",
                )

            items.append(
                LinkElement(
                    id=element_id,
                    label=label,
                    element_type="Pipe",
                    is_active=is_active,
                    active_topology_source_scenario_id=active_source,
                    active_topology_alternative_id=active_alt,
                    geometry_source_scenario_id=geometry_source,
                    geometry_alternative_id=geometry_alt,
                    topology_source_scenario_id=topology_source,
                    topology_alternative_id=topology_alt,
                    physical_source_scenario_ids=phys_scenarios,
                    physical_alternative_ids=phys_alts,
                    start_node_id=start_id,
                    end_node_id=end_id,
                    geometry_ft=geometry if isinstance(geometry, list) else [],
                    length_ft=length,
                    physical=physical,
                    initial_settings=self.readers.initial_settings(
                        "IdahoPipe_InitialSettings_Data",
                        element_id,
                        self.context,
                    ),
                    udx=self.readers.udx(
                        "IdahoPipe_HMIUserDefinedExtensions_Data",
                        element_id,
                        self.context,
                    ),
                )
            )
            stats.exported += 1

        return items, stats
