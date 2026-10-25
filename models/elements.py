from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class WaterGemsElement:
    id: int
    label: str
    element_type: str
    is_active: Optional[bool] = None

    active_topology_source_scenario_id: Optional[int] = None
    active_topology_alternative_id: Optional[int] = None

    geometry_source_scenario_id: Optional[int] = None
    geometry_alternative_id: Optional[int] = None

    topology_source_scenario_id: Optional[int] = None
    topology_alternative_id: Optional[int] = None

    physical_source_scenario_ids: list[int] = field(default_factory=list)
    physical_alternative_ids: list[int] = field(default_factory=list)

    physical: dict[str, Any] = field(default_factory=dict)
    initial_settings: dict[str, Any] = field(default_factory=dict)
    udx: dict[str, Any] = field(default_factory=dict)


@dataclass
class NodeElement(WaterGemsElement):
    x_ft: Optional[float] = None
    y_ft: Optional[float] = None
    elevation_ft: Optional[float] = None


@dataclass
class LinkElement(WaterGemsElement):
    start_node_id: Optional[int] = None
    end_node_id: Optional[int] = None
    start_node_label: str = ""
    start_node_type: str = ""
    end_node_label: str = ""
    end_node_type: str = ""

    start_node_resolution: str = ""
    end_node_resolution: str = ""

    geometry_ft: list[tuple[float, float]] = field(default_factory=list)
    length_ft: Optional[float] = None


@dataclass
class DirectedNodeElement(NodeElement):
    downstream_link_id: Optional[int] = None


@dataclass
class CustomerMeterElement(NodeElement):
    """Customer Meter plus its scenario-resolved demand relationship."""
    billing_id: str = ""
    demand_base_flow_cfs: Optional[float] = None
    demand_pattern_id: Optional[int] = None
    demand_pattern_label: str = ""
    associated_element_id: Optional[int] = None
    associated_element_label: str = ""
    associated_element_type: str = ""
    demand_distribution_start: Optional[float] = None
