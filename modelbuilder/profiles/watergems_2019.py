from units import cfs_to_lps, ft_to_m, ft_to_mm


def first(data, *keys):
    for key in keys:
        value = data.get(key)
        if value is not None:
            return value
    return None


def common(element):
    return {
        "SourceElementID": f"WG_SRC_{element.id}",
        "SourceDomainElementID": element.id,
        "Label": element.label,
        "IsActive": element.is_active,
    }


def node_row(element):
    row = common(element)
    row.update({
        "X_m": ft_to_m(element.x_ft),
        "Y_m": ft_to_m(element.y_ft),
        "Elevation_m": ft_to_m(element.elevation_ft),
    })
    return append_dynamic_fields(row, element)


def junction(element):
    return node_row(element)


def reservoir(element):
    row = node_row(element)
    row["HGLPattern"] = first(
        element.physical,
        "Physical_HglPattern",
        "Physical_HGLPattern",
    )
    return append_dynamic_fields(row, element)


def air_valve(element):
    row = node_row(element)
    row["TreatAsJunction"] = first(
        element.physical,
        "Physical_TreatAirValveAsJunction",
    )
    return append_dynamic_fields(row, element)


def hydrant(element):
    row = node_row(element)
    row.update({
        "LateralDiameter_mm": ft_to_mm(first(
            element.physical,
            "Physical_HydrantLateralDiameter",
        )),
        "LateralLength_m": ft_to_m(first(
            element.physical,
            "Physical_HydrantLateralLength",
        )),
        "LateralMinorLossCoefficient": first(
            element.physical,
            "Physical_HydrantLateralMinorLossCoefficient",
        ),
    })
    return append_dynamic_fields(row, element)


def tank(element):
    row = node_row(element)
    p = element.physical
    row.update({
        "TankBaseElevation_m": ft_to_m(first(p, "Physical_TankBaseElevation")),
        "MinimumLevel_m": ft_to_m(first(p, "Physical_MinimumLevel")),
        "MaximumLevel_m": ft_to_m(first(p, "Physical_MaximumLevel")),
        "Diameter_mm": ft_to_mm(first(p, "Physical_Diameter", "Physical_TankDiameter")),
    })
    return append_dynamic_fields(row, element)


def customer_meter(element):
    row = node_row(element)
    physical = element.physical
    udx = element.udx
    row.update({
        "BillingID": element.billing_id,
        "Zone": first(physical, "Physical_Zone", "Zone"),
        "Concepcao": first(udx, "Concepcao", "Concepção"),
        "Setor": first(physical, "Setor"),
        "Subsetor": first(physical, "Subsetor"),
        "Setor_VRP": first(udx, "SETOR_VRP", "Setor_VRP", "Stor_VRP"),
        "Categoria": first(udx, "Categoria"),
        "Tipo_Categoria": first(udx, "Tipo_Categoria"),
        "Economias": first(udx, "Economias"),
        "Fase": first(physical, "Faseamento", "Fase"),
        "C_S_Tipo1": first(udx, "C_S_Tipo1"),
        "C_S_Tipo2": first(udx, "C_S_Tipo2"),
        "Mes_Civil": first(udx, "Mes_Civil"),
        "DemandBase_Ls": cfs_to_lps(element.demand_base_flow_cfs),
        "DemandPatternID": element.demand_pattern_id,
        "DemandPatternLabel": element.demand_pattern_label,
        "AssociatedElementID": element.associated_element_id,
        "AssociatedElementLabel": element.associated_element_label,
        "AssociatedElementType": element.associated_element_type,
        "DemandDistributionStart": element.demand_distribution_start,
    })
    return append_dynamic_fields(row, element)


def pipe(element):
    p = element.physical
    row = common(element)
    row.update({
        "StartNodeLabel": element.start_node_label,
        "StopNodeLabel": element.end_node_label,
        "StartNodeSourceID": (
            f"WG_SRC_{element.start_node_id}"
            if element.start_node_id is not None else None
        ),
        "StartNodeResolution": element.start_node_resolution,
        "StopNodeResolution": element.end_node_resolution,
        "StopNodeSourceID": (
            f"WG_SRC_{element.end_node_id}"
            if element.end_node_id is not None else None
        ),
        "Diameter_mm": ft_to_mm(first(p, "Physical_PipeDiameter")),
        "Material": first(p, "Physical_PipeMaterial"),
        "HazenWilliamsC": first(p, "Physical_HazenWilliamsC"),
        "ManningsN": first(p, "Physical_PipeMannings"),
        "Length_m": ft_to_m(element.length_ft),
    })
    return append_dynamic_fields(row, element)


def directed_node(element):
    p = element.physical
    row = node_row(element)
    row.update({
        "Diameter_mm": ft_to_mm(first(
            p,
            "Physical_ValveDiameter",
            "Physical_PipeDiameter",
        )),
        "DownstreamLinkSourceID": (
            f"WG_SRC_{element.downstream_link_id}"
            if element.downstream_link_id is not None else None
        ),
    })

    # Add common settings when present, without depending on a specific valve family.
    candidates = {
        "FlowSetting": (
            "InitialSettings_FlowSetting",
            "Physical_FlowSetting",
        ),
        "PressureSetting": (
            "PressureValveSetting",
            "InitialSettings_PressureSetting",
        ),
        "HeadlossCoefficient": (
            "InitialSettings_HeadlossCoefficient",
        ),
        "TCVDischargeCoefficient": (
            "InitialSettings_TCVDischargeCoefficient",
        ),
        "RelativeClosure": (
            "InitialSettings_RelativeClosure",
        ),
        "PumpDefinitionID": (
            "Physical_PumpDefinitionID",
        ),
        "IsVariableSpeedPump": (
            "Physical_IsVariableSpeedPump",
        ),
    }

    merged = {**element.physical, **element.initial_settings}
    for out_name, keys in candidates.items():
        value = first(merged, *keys)
        if value is not None:
            row[out_name] = value

    return append_dynamic_fields(row, element)



def append_dynamic_fields(row, element):
    for key, value in getattr(element, "physical", {}).items():
        row[f"Physical.{key}"] = value

    for key, value in getattr(element, "udx", {}).items():
        row[f"UDX.{key}"] = value

    for key, value in getattr(element, "initial_settings", {}).items():
        row[f"Initial.{key}"] = value

    return row


PROFILE = {
    "name": "WaterGEMS 2019",
    "sheets": {
        "Pipe": ("Pipes", pipe),
        "Junction": ("Junctions", junction),
        "Reservoir": ("Reservoirs", reservoir),
        "Air Valve": ("AirValves", air_valve),
        "Hydrant": ("Hydrants", hydrant),
        "Tank": ("Tanks", tank),
        "Conventional Tank": ("Tanks", tank),
        "TCV": ("TCVs", directed_node),
        "FCV": ("FCVs", directed_node),
        "PRV": ("PRVs", directed_node),
        "PBV": ("PBVs", directed_node),
        "Check Valve": ("CheckValves", directed_node),
        "Standard Pump": ("Pumps", directed_node),
        "Variable Speed Pump Battery": ("VSPB", directed_node),
        "Customer Meter": ("Customer Meters", customer_meter),
    },
}
