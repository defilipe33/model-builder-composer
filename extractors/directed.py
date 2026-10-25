from extractors.base import BaseExtractor
from models.elements import DirectedNodeElement
from models.stats import ExtractionStats


DIRECTED_CONFIGS = [
    ("TCV", "TCV",
     ["BaseDirectedNode_Physical_Data", "BaseValve_Physical_Data", "TCV_Physical_Data"],
     "TCV_InitialSettings_Data", "TCV_HMIUserDefinedExtensions_Data"),
    ("FCV", "FCV",
     ["BaseDirectedNode_Physical_Data", "BaseValve_Physical_Data",
      "PressureValve_Physical_Data", "FCV_Physical_Data"],
     "FCV_InitialSettings_Data", "FCV_HMIUserDefinedExtensions_Data"),
    ("PRV", "PRV",
     ["BaseDirectedNode_Physical_Data", "BaseValve_Physical_Data",
      "PressureValve_Physical_Data", "PRV_Physical_Data"],
     "PressureValve_InitialSettings_Data", "PRV_HMIUserDefinedExtensions_Data"),
    ("PBV", "PBV",
     ["BaseDirectedNode_Physical_Data", "BaseValve_Physical_Data", "PBV_Physical_Data"],
     "PBV_InitialSettings_Data", "PBV_HMIUserDefinedExtensions_Data"),
    ("Check Valve", "CheckValve",
     ["BaseDirectedNode_Physical_Data", "CheckValve_Physical_Data"],
     None, "CheckValve_HMIUserDefinedExtensions_Data"),
    ("Standard Pump", "StandardPump",
     ["BaseDirectedNode_Physical_Data", "BasePump_Physical_Data", "StandardPump_Physical_Data"],
     "StandardPump_InitialSettings_Data", "StandardPump_HMIUserDefinedExtensions_Data"),
    ("Variable Speed Pump Battery", "VariableSpeedPumpBattery",
     ["BaseDirectedNode_Physical_Data", "VariableSpeedPumpBattery_Physical_Data"],
     "VariableSpeedPumpBattery_InitialSettings_Data",
     "VariableSpeedPumpBattery_HMIUserDefinedExtensions_Data"),
]


class DirectedNodeExtractor(BaseExtractor):
    def extract_all(self):
        result = {}
        stats_map = {}

        for element_type, root, physical_tables, initial, udx in DIRECTED_CONFIGS:
            items = []
            stats = ExtractionStats(element_type)

            for element_id in self.root_ids(root):
                stats.examined += 1
                label = self.common.label(element_id)

                is_active, active_source, active_alt = self.resolve_active_topology(
                    element_id,
                    "BaseDirectedNode_HMIActiveTopology_Data",
                    stats,
                    label,
                )

                geometry, _, geometry_source, geometry_alt = self.readers.geometry(
                    "BaseDirectedNode_HmiDataSetGeometry_Data",
                    element_id,
                    self.context,
                )
                if not isinstance(geometry, tuple):
                    stats.invalid_geometry += 1
                    stats.add_issue(
                        element_id, label, "Geometry unresolved",
                        "Directed-node geometry was not resolved as a Point.",
                    )
                    x = y = None
                else:
                    x, y = geometry

                topology_row, topology_source, topology_alt = self.readers.topology(
                    "BaseDirectedNode_HMIDataSetTopology_Data",
                    element_id,
                    self.context,
                )
                if topology_row is None:
                    stats.invalid_topology += 1
                    stats.add_issue(
                        element_id, label, "Topology unresolved",
                        "Directed-node topology could not be resolved.",
                    )
                    downstream = None
                else:
                    downstream = None
                    for candidate in (
                        "HMITopologyDownstreamLinkID",
                        "DownstreamLinkID",
                    ):
                        if candidate in topology_row.keys():
                            downstream = topology_row[candidate]
                            break

                physical, physical_prov = self.readers.physical(
                    physical_tables, element_id, self.context
                )
                phys_scenarios, phys_alts = self.physical_provenance(physical_prov)

                if not physical:
                    stats.missing_physical += 1
                    stats.add_issue(
                        element_id, label, "Physical unresolved",
                        "No physical record was resolved.",
                    )

                items.append(
                    DirectedNodeElement(
                        id=element_id,
                        label=label,
                        element_type=element_type,
                        is_active=is_active,
                        active_topology_source_scenario_id=active_source,
                        active_topology_alternative_id=active_alt,
                        geometry_source_scenario_id=geometry_source,
                        geometry_alternative_id=geometry_alt,
                        topology_source_scenario_id=topology_source,
                        topology_alternative_id=topology_alt,
                        physical_source_scenario_ids=phys_scenarios,
                        physical_alternative_ids=phys_alts,
                        x_ft=x,
                        y_ft=y,
                        elevation_ft=physical.get("Physical_NodeElevation"),
                        downstream_link_id=downstream,
                        physical=physical,
                        initial_settings=self.readers.initial_settings(
                            initial, element_id, self.context
                        ),
                        udx=self.readers.udx(
                            udx, element_id, self.context
                        ),
                    )
                )
                stats.exported += 1

            result[element_type] = items
            stats_map[element_type] = stats

        return result, stats_map
