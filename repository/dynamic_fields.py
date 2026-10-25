from collections import defaultdict


ELEMENT_TABLES = {
    "Pipe": {
        "physical": ["BaseLink_Physical_Data", "IdahoPipe_Physical_Data"],
        "initial": ["IdahoPipe_InitialSettings_Data"],
        "udx": ["IdahoPipe_HMIUserDefinedExtensions_Data"],
    },
    "Junction": {
        "physical": ["BaseIdahoNode_Physical_Data", "IdahoJunction_Physical_Data"],
        "initial": ["IdahoJunction_InitialSettings_Data"],
        "udx": ["IdahoJunction_HMIUserDefinedExtensions_Data"],
    },
    "Reservoir": {
        "physical": ["BaseIdahoNode_Physical_Data", "IdahoReservoir_Physical_Data"],
        "initial": ["IdahoReservoir_InitialSettings_Data"],
        "udx": ["IdahoReservoir_HMIUserDefinedExtensions_Data"],
    },
    "Air Valve": {
        "physical": ["BaseIdahoNode_Physical_Data", "AirValve_Physical_Data"],
        "initial": ["AirValve_InitialSettings_Data"],
        "udx": ["AirValve_HMIUserDefinedExtensions_Data"],
    },
    "Hydrant": {
        "physical": ["BaseIdahoNode_Physical_Data", "IdahoHydrant_Physical_Data"],
        "initial": ["IdahoHydrant_InitialSettings_Data"],
        "udx": ["IdahoHydrant_HMIUserDefinedExtensions_Data"],
    },
    "Tank": {
        "physical": [
            "BaseIdahoNode_Physical_Data",
            "BaseTank_Physical_Data",
            "IdahoTank_Physical_Data",
        ],
        "initial": ["IdahoTank_InitialSettings_Data"],
        "udx": ["IdahoTank_HMIUserDefinedExtensions_Data"],
    },
    "Conventional Tank": {
        "physical": [
            "BaseIdahoNode_Physical_Data",
            "BaseTank_Physical_Data",
            "IdahoTank_Physical_Data",
            "ConventionalTank_Physical_Data",
        ],
        "initial": ["ConventionalTank_InitialSettings_Data"],
        "udx": ["ConventionalTank_HMIUserDefinedExtensions_Data"],
    },
    "TCV": {
        "physical": [
            "BaseDirectedNode_Physical_Data",
            "BaseValve_Physical_Data",
            "TCV_Physical_Data",
        ],
        "initial": ["TCV_InitialSettings_Data"],
        "udx": ["TCV_HMIUserDefinedExtensions_Data"],
    },
    "FCV": {
        "physical": [
            "BaseDirectedNode_Physical_Data",
            "BaseValve_Physical_Data",
            "PressureValve_Physical_Data",
            "FCV_Physical_Data",
        ],
        "initial": ["FCV_InitialSettings_Data"],
        "udx": ["FCV_HMIUserDefinedExtensions_Data"],
    },
    "PRV": {
        "physical": [
            "BaseDirectedNode_Physical_Data",
            "BaseValve_Physical_Data",
            "PressureValve_Physical_Data",
            "PRV_Physical_Data",
        ],
        "initial": ["PressureValve_InitialSettings_Data", "PRV_InitialSettings_Data"],
        "udx": ["PRV_HMIUserDefinedExtensions_Data"],
    },
    "PBV": {
        "physical": [
            "BaseDirectedNode_Physical_Data",
            "BaseValve_Physical_Data",
            "PBV_Physical_Data",
        ],
        "initial": ["PBV_InitialSettings_Data"],
        "udx": ["PBV_HMIUserDefinedExtensions_Data"],
    },
    "Check Valve": {
        "physical": [
            "BaseDirectedNode_Physical_Data",
            "CheckValve_Physical_Data",
        ],
        "initial": [],
        "udx": ["CheckValve_HMIUserDefinedExtensions_Data"],
    },
    "Standard Pump": {
        "physical": [
            "BaseDirectedNode_Physical_Data",
            "BasePump_Physical_Data",
            "StandardPump_Physical_Data",
        ],
        "initial": ["StandardPump_InitialSettings_Data"],
        "udx": ["StandardPump_HMIUserDefinedExtensions_Data"],
    },
    "Variable Speed Pump Battery": {
        "physical": [
            "BaseDirectedNode_Physical_Data",
            "VariableSpeedPumpBattery_Physical_Data",
        ],
        "initial": ["VariableSpeedPumpBattery_InitialSettings_Data"],
        "udx": ["VariableSpeedPumpBattery_HMIUserDefinedExtensions_Data"],
    },
    "Customer Meter": {
        "physical": ["CustomerNode_Physical_Data"],
        "initial": [],
        "udx": ["CustomerNode_HMIUserDefinedExtensions_Data"],
    },
}

SYSTEM_COLUMNS = {
    "DomainElementID",
    "AlternativeID",
    "RowVersion",
    "HMIID",
    "ID",
}


class DynamicFieldDiscovery:
    def __init__(self, schema):
        self.schema = schema

    def _columns(self, table):
        if not self.schema.table_exists(table):
            return []

        cols = self.schema.columns(table)
        result = []
        for col in cols:
            name = col["name"] if isinstance(col, dict) else col
            if name in SYSTEM_COLUMNS:
                continue
            result.append(name)
        return result

    def fields_for_type(self, element_type):
        cfg = ELEMENT_TABLES.get(element_type, {})
        out = {
            "physical": [],
            "initial": [],
            "udx": [],
        }

        for namespace in ("physical", "initial", "udx"):
            seen = set()
            for table in cfg.get(namespace, []):
                for field in self._columns(table):
                    if field not in seen:
                        seen.add(field)
                        out[namespace].append(field)

        return out
