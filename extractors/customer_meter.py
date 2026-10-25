from extractors.base import BaseExtractor
from models.elements import CustomerMeterElement
from models.stats import ExtractionStats
from repository.model_repository import ELEMENT_ROOTS


class CustomerMeterExtractor(BaseExtractor):
    """Scenario-aware full extraction for Customer Nodes/Meters."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._associated_type_cache = {}

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

    def extract_all(self):
        items = []
        stats = ExtractionStats("Customer Meter")
        for element_id in self.root_ids("CustomerNode"):
            stats.examined += 1
            label = self.common.label(element_id)
            active, active_source, active_alt = self.resolve_active_topology(
                element_id, "CustomerNode_HMIActiveTopology_Data", stats, label
            )
            geometry, _, geometry_source, geometry_alt = self.readers.geometry(
                "CustomerNode_HmiDataSetGeometry_Data", element_id, self.context
            )
            x = y = None
            if isinstance(geometry, tuple):
                x, y = geometry
            else:
                stats.invalid_geometry += 1
            physical, provenance = self.readers.physical(
                ["CustomerNode_Physical_Data"], element_id, self.context
            )
            scenario_ids, alternative_ids = self.physical_provenance(provenance)
            demand, _, _ = self.readers.resolver.resolve_dict(
                "CustomerNode_Demand_Data", element_id, 20, self.context
            )
            billing = self.db.fetchone(
                "SELECT CustomerNode_BillingID FROM CustomerNode "
                "WHERE DomainElementID=? LIMIT 1", (element_id,)
            )
            associated_id = demand.get("Demand_AssociatedElement")
            pattern_id = demand.get("Demand_DemandPattern")
            items.append(CustomerMeterElement(
                id=element_id, label=label, element_type="Customer Meter",
                is_active=active,
                active_topology_source_scenario_id=active_source,
                active_topology_alternative_id=active_alt,
                geometry_source_scenario_id=geometry_source,
                geometry_alternative_id=geometry_alt,
                physical_source_scenario_ids=scenario_ids,
                physical_alternative_ids=alternative_ids,
                x_ft=x, y_ft=y,
                elevation_ft=physical.get("Physical_NodeElevation"),
                physical=physical,
                udx=self.readers.udx(
                    "CustomerNode_HMIUserDefinedExtensions_Data", element_id, self.context
                ),
                billing_id="" if billing is None else (billing["CustomerNode_BillingID"] or ""),
                demand_base_flow_cfs=demand.get("Demand_BaseFlow"),
                demand_pattern_id=pattern_id,
                demand_pattern_label=(self.common.label(pattern_id) if pattern_id is not None else ""),
                associated_element_id=associated_id,
                associated_element_label=(self.common.label(associated_id) if associated_id is not None else ""),
                associated_element_type=self._element_type_for_id(associated_id),
                demand_distribution_start=demand.get("Demand_DistributionStart"),
            ))
            stats.exported += 1
        return items, stats
