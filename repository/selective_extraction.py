from models.elements import (
    LinkElement, NodeElement, DirectedNodeElement, CustomerMeterElement,
)
from repository.model_repository import ELEMENT_ROOTS


NODE_CONFIGS = {
    "Junction": {
        "root": "IdahoJunction",
        "active": "BaseIdahoNode_HMIActiveTopology_Data",
        "geometry": "BaseIdahoNode_HmiDataSetGeometry_Data",
        "physical": ["BaseIdahoNode_Physical_Data", "IdahoJunction_Physical_Data"],
        "udx": "IdahoJunction_HMIUserDefinedExtensions_Data",
    },
    "Reservoir": {
        "root": "IdahoReservoir",
        "active": "BaseIdahoNode_HMIActiveTopology_Data",
        "geometry": "BaseIdahoNode_HmiDataSetGeometry_Data",
        "physical": ["BaseIdahoNode_Physical_Data", "IdahoReservoir_Physical_Data"],
        "udx": "IdahoReservoir_HMIUserDefinedExtensions_Data",
    },
    "Air Valve": {
        "root": "AirValve",
        "active": "BaseIdahoNode_HMIActiveTopology_Data",
        "geometry": "BaseIdahoNode_HmiDataSetGeometry_Data",
        "physical": ["BaseIdahoNode_Physical_Data", "AirValve_Physical_Data"],
        "udx": "AirValve_HMIUserDefinedExtensions_Data",
    },
    "Hydrant": {
        "root": "IdahoHydrant",
        "active": "BaseIdahoNode_HMIActiveTopology_Data",
        "geometry": "BaseIdahoNode_HmiDataSetGeometry_Data",
        "physical": ["BaseIdahoNode_Physical_Data", "IdahoHydrant_Physical_Data"],
        "udx": "IdahoHydrant_HMIUserDefinedExtensions_Data",
    },
}

DIRECTED_CONFIGS = {
    "TCV": (
        ["BaseDirectedNode_Physical_Data", "BaseValve_Physical_Data", "TCV_Physical_Data"],
        "TCV_InitialSettings_Data", "TCV_HMIUserDefinedExtensions_Data"
    ),
    "FCV": (
        ["BaseDirectedNode_Physical_Data", "BaseValve_Physical_Data",
         "PressureValve_Physical_Data", "FCV_Physical_Data"],
        "FCV_InitialSettings_Data", "FCV_HMIUserDefinedExtensions_Data"
    ),
    "PRV": (
        ["BaseDirectedNode_Physical_Data", "BaseValve_Physical_Data",
         "PressureValve_Physical_Data", "PRV_Physical_Data"],
        "PressureValve_InitialSettings_Data", "PRV_HMIUserDefinedExtensions_Data"
    ),
    "PBV": (
        ["BaseDirectedNode_Physical_Data", "BaseValve_Physical_Data", "PBV_Physical_Data"],
        "PBV_InitialSettings_Data", "PBV_HMIUserDefinedExtensions_Data"
    ),
    "Check Valve": (
        ["BaseDirectedNode_Physical_Data", "CheckValve_Physical_Data"],
        None, "CheckValve_HMIUserDefinedExtensions_Data"
    ),
    "Standard Pump": (
        ["BaseDirectedNode_Physical_Data", "BasePump_Physical_Data", "StandardPump_Physical_Data"],
        "StandardPump_InitialSettings_Data", "StandardPump_HMIUserDefinedExtensions_Data"
    ),
    "Variable Speed Pump Battery": (
        ["BaseDirectedNode_Physical_Data", "VariableSpeedPumpBattery_Physical_Data"],
        "VariableSpeedPumpBattery_InitialSettings_Data",
        "VariableSpeedPumpBattery_HMIUserDefinedExtensions_Data"
    ),
}


class SelectiveExtractionService:
    def __init__(self, db, schema, common, readers, context, topology_resolver):
        self.db = db
        self.schema = schema
        self.common = common
        self.readers = readers
        self.context = context
        self.topology_resolver = topology_resolver
        self._associated_type_cache = {}


    def _is_live(self, element_id):
        if self.schema.table_exists("HMIDomainElement"):
            row = self.db.fetchone(
                """
                SELECT COALESCE(IsDeleted,0) AS IsDeleted
                FROM HMIDomainElement
                WHERE DomainElementID=?
                LIMIT 1
                """,
                (element_id,),
            )
            return row is not None and not bool(row["IsDeleted"])

        if self.schema.table_exists("HMIModelingElement"):
            row = self.db.fetchone(
                """
                SELECT COALESCE(IsDeleted,0) AS IsDeleted
                FROM HMIModelingElement
                WHERE ElementID=?
                LIMIT 1
                """,
                (element_id,),
            )
            return row is not None and not bool(row["IsDeleted"])

        return True

    def _active(self, table, element_id):
        return self.readers.active_state(table, element_id, self.context)

    def _physical(self, tables, element_id):
        data, provenance = self.readers.physical(
            tables, element_id, self.context
        )
        scenario_ids = []
        alt_ids = []
        for _, (scenario_id, alt_id) in provenance.items():
            if scenario_id is not None and scenario_id not in scenario_ids:
                scenario_ids.append(scenario_id)
            if alt_id is not None and alt_id not in alt_ids:
                alt_ids.append(alt_id)
        return data, scenario_ids, alt_ids

    def _extract_pipe(self, element_id):
        label = self.common.label(element_id)
        active, active_source, active_alt = self._active(
            "BaseLink_HMIActiveTopology_Data", element_id
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

        resolved_topology = self.topology_resolver.resolve_pipe_endpoints(
            element_id,
            geometry=geometry if isinstance(geometry, list) else None,
        )
        start_id = resolved_topology["start_node_id"]
        end_id = resolved_topology["end_node_id"]

        physical, phys_scenarios, phys_alts = self._physical(
            ["BaseLink_Physical_Data", "IdahoPipe_Physical_Data"],
            element_id,
        )

        return LinkElement(
            id=element_id,
            label=label,
            element_type="Pipe",
            is_active=active,
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
            start_node_label=resolved_topology['start_node_label'],
            start_node_type=resolved_topology['start_node_type'],
            end_node_label=resolved_topology['end_node_label'],
            end_node_type=resolved_topology['end_node_type'],
            start_node_resolution=resolved_topology['start_resolution'],
            end_node_resolution=resolved_topology['end_resolution'],
            geometry_ft=geometry if isinstance(geometry, list) else [],
            length_ft=length,
            physical=physical,
            initial_settings=self.readers.initial_settings(
                "IdahoPipe_InitialSettings_Data", element_id, self.context
            ),
            udx=self.readers.udx(
                "IdahoPipe_HMIUserDefinedExtensions_Data", element_id, self.context
            ),
        )

    def _extract_node(self, element_type, element_id):
        cfg = NODE_CONFIGS[element_type]
        label = self.common.label(element_id)

        active, active_source, active_alt = self._active(
            cfg["active"], element_id
        )
        geometry, _, geometry_source, geometry_alt = self.readers.geometry(
            cfg["geometry"], element_id, self.context
        )
        x = y = None
        if isinstance(geometry, tuple):
            x, y = geometry

        physical, phys_scenarios, phys_alts = self._physical(
            cfg["physical"], element_id
        )

        return NodeElement(
            id=element_id,
            label=label,
            element_type=element_type,
            is_active=active,
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
            udx=self.readers.udx(cfg["udx"], element_id, self.context),
        )

    def _extract_tank(self, element_type, element_id):
        label = self.common.label(element_id)
        active, active_source, active_alt = self._active(
            "BaseIdahoNode_HMIActiveTopology_Data", element_id
        )
        geometry, _, geometry_source, geometry_alt = self.readers.geometry(
            "BaseIdahoNode_HmiDataSetGeometry_Data", element_id, self.context
        )
        x = y = None
        if isinstance(geometry, tuple):
            x, y = geometry

        tables = [
            "BaseIdahoNode_Physical_Data",
            "BaseTank_Physical_Data",
            "IdahoTank_Physical_Data",
        ]
        if element_type == "Conventional Tank":
            tables.append("ConventionalTank_Physical_Data")

        physical, phys_scenarios, phys_alts = self._physical(tables, element_id)

        udx = (
            "ConventionalTank_HMIUserDefinedExtensions_Data"
            if element_type == "Conventional Tank"
            else "IdahoTank_HMIUserDefinedExtensions_Data"
        )

        return NodeElement(
            id=element_id,
            label=label,
            element_type=element_type,
            is_active=active,
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
            udx=self.readers.udx(udx, element_id, self.context),
        )

    def _extract_directed(self, element_type, element_id):
        physical_tables, initial_table, udx_table = DIRECTED_CONFIGS[element_type]
        label = self.common.label(element_id)

        active, active_source, active_alt = self._active(
            "BaseDirectedNode_HMIActiveTopology_Data", element_id
        )
        geometry, _, geometry_source, geometry_alt = self.readers.geometry(
            "BaseDirectedNode_HmiDataSetGeometry_Data", element_id, self.context
        )
        x = y = None
        if isinstance(geometry, tuple):
            x, y = geometry

        topology_row, topology_source, topology_alt = self.readers.topology(
            "BaseDirectedNode_HMIDataSetTopology_Data",
            element_id,
            self.context,
        )
        downstream = None
        if topology_row is not None:
            for candidate in ("HMITopologyDownstreamLinkID", "DownstreamLinkID"):
                if candidate in topology_row.keys():
                    downstream = topology_row[candidate]
                    break

        physical, phys_scenarios, phys_alts = self._physical(
            physical_tables, element_id
        )

        return DirectedNodeElement(
            id=element_id,
            label=label,
            element_type=element_type,
            is_active=active,
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
                initial_table, element_id, self.context
            ),
            udx=self.readers.udx(udx_table, element_id, self.context),
        )

    def _element_type_for_id(self, element_id):
        if element_id is None:
            return ""
        if element_id in self._associated_type_cache:
            return self._associated_type_cache[element_id]
        for element_type, table in ELEMENT_ROOTS.items():
            if not self.schema.table_exists(table):
                continue
            row = self.db.fetchone(
                f"SELECT 1 FROM {table} WHERE DomainElementID=? LIMIT 1",
                (element_id,),
            )
            if row is not None:
                self._associated_type_cache[element_id] = element_type
                return element_type
        self._associated_type_cache[element_id] = "Unknown"
        return "Unknown"

    def _extract_customer_meter(self, element_id):
        label = self.common.label(element_id)
        active, active_source, active_alt = self._active(
            "CustomerNode_HMIActiveTopology_Data", element_id
        )
        geometry, _, geometry_source, geometry_alt = self.readers.geometry(
            "CustomerNode_HmiDataSetGeometry_Data", element_id, self.context
        )
        x = y = None
        if isinstance(geometry, tuple):
            x, y = geometry
        physical, phys_scenarios, phys_alts = self._physical(
            ["CustomerNode_Physical_Data"], element_id
        )
        udx = self.readers.udx(
            "CustomerNode_HMIUserDefinedExtensions_Data", element_id, self.context
        )
        demand, _, _ = self.readers.resolver.resolve_dict(
            "CustomerNode_Demand_Data", element_id, 20, self.context
        )
        billing = self.db.fetchone(
            "SELECT CustomerNode_BillingID FROM CustomerNode "
            "WHERE DomainElementID=? LIMIT 1", (element_id,)
        )
        associated_id = demand.get("Demand_AssociatedElement")
        pattern_id = demand.get("Demand_DemandPattern")
        return CustomerMeterElement(
            id=element_id, label=label, element_type="Customer Meter",
            is_active=active,
            active_topology_source_scenario_id=active_source,
            active_topology_alternative_id=active_alt,
            geometry_source_scenario_id=geometry_source,
            geometry_alternative_id=geometry_alt,
            physical_source_scenario_ids=phys_scenarios,
            physical_alternative_ids=phys_alts,
            x_ft=x, y_ft=y,
            elevation_ft=physical.get("Physical_NodeElevation"),
            physical=physical, udx=udx,
            billing_id="" if billing is None else (billing["CustomerNode_BillingID"] or ""),
            demand_base_flow_cfs=demand.get("Demand_BaseFlow"),
            demand_pattern_id=pattern_id,
            demand_pattern_label=(self.common.label(pattern_id) if pattern_id is not None else ""),
            associated_element_id=associated_id,
            associated_element_label=(self.common.label(associated_id) if associated_id is not None else ""),
            associated_element_type=self._element_type_for_id(associated_id),
            demand_distribution_start=demand.get("Demand_DistributionStart"),
        )

    def extract_selected(self, selected):
        groups = {}

        for element_type, ids in selected.items():
            if not ids:
                continue

            elements = []
            for element_id in sorted(ids):
                # Safety check: saved/stale SelectionSets must never resurrect
                # tombstones that were deleted from the WaterGEMS model.
                if not self._is_live(element_id):
                    continue

                if element_type == "Pipe":
                    elements.append(self._extract_pipe(element_id))
                elif element_type in NODE_CONFIGS:
                    elements.append(self._extract_node(element_type, element_id))
                elif element_type in {"Tank", "Conventional Tank"}:
                    elements.append(self._extract_tank(element_type, element_id))
                elif element_type in DIRECTED_CONFIGS:
                    elements.append(self._extract_directed(element_type, element_id))
                elif element_type == "Customer Meter":
                    elements.append(self._extract_customer_meter(element_id))

            if elements:
                groups[element_type] = elements

        # Resolve pipe labels after selected node-like objects exist.
        node_lookup = {}
        for element_type, elements in groups.items():
            if element_type == "Pipe":
                continue
            for e in elements:
                if hasattr(e, "x_ft"):
                    node_lookup[e.id] = (e.label, e.element_type)

        for p in groups.get("Pipe", []):
            if p.start_node_id in node_lookup:
                p.start_node_label, p.start_node_type = node_lookup[p.start_node_id]
            if p.end_node_id in node_lookup:
                p.end_node_label, p.end_node_type = node_lookup[p.end_node_id]

        return groups
