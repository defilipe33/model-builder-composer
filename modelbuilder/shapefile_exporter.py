"""GIS export for WaterGEMS ModelBuilder.

Each selected element type is written as a separate ESRI Shapefile layer.
Pipes are exported as complete LineStrings, preserving every vertex.
"""

from __future__ import annotations

import csv
from pathlib import Path

import shapefile

from modelbuilder.profiles.watergems_2019 import PROFILE
from modelbuilder.column_config import validate_shapefile_field_names
from units import ft_to_m


LAYER_NAMES = {
    "Pipe": "Pipes",
    "Junction": "Junctions",
    "Reservoir": "Reservoirs",
    "Air Valve": "AirValves",
    "Hydrant": "Hydrants",
    "Tank": "Tanks",
    "Conventional Tank": "ConventionalTanks",
    "TCV": "TCVs",
    "FCV": "FCVs",
    "PRV": "PRVs",
    "PBV": "PBVs",
    "Check Valve": "CheckValves",
    "Standard Pump": "Pumps",
    "Variable Speed Pump Battery": "VSPBs",
    "Customer Meter": "CustomerMeters",
}

def _field_definition(values):
    present = [value for value in values if value is not None]
    if present and all(isinstance(value, bool) for value in present):
        return "L", 1, 0
    if present and all(
        isinstance(value, int) and not isinstance(value, bool)
        for value in present
    ):
        return "N", 18, 0
    if present and all(isinstance(value, (int, float)) for value in present):
        return "F", 20, 8

    width = max((len(str(value)) for value in present), default=1)
    return "C", min(max(width, 1), 254), 0


def _layer_columns(element_type, column_config):
    return list(column_config.get(element_type))


def _element_row(element_type, element):
    mapping = PROFILE["sheets"].get(element_type)
    if mapping is None:
        return None
    _, mapper = mapping
    row = mapper(element)
    row["SourceElementType"] = element_type
    return row


def _write_layer(output_dir, element_type, elements, column_config):
    layer_name = LAYER_NAMES.get(element_type, element_type.replace(" ", ""))
    shape_type = shapefile.POLYLINE if element_type == "Pipe" else shapefile.POINT
    base_path = output_dir / layer_name
    columns = _layer_columns(element_type, column_config)
    if not columns:
        raise ValueError(
            f"Não há campos definidos para {element_type}. "
            "Configure Colunas de exportação antes de gerar o Shapefile."
        )
    prepared = []
    skipped = 0

    for element in elements:
        row = _element_row(element_type, element)
        if row is None:
            skipped += 1
            continue

        if element_type == "Pipe":
            geometry = getattr(element, "geometry_ft", [])
            if not isinstance(geometry, list) or len(geometry) < 2:
                skipped += 1
                continue
            points = [[ft_to_m(x), ft_to_m(y)] for x, y in geometry]
            if len({(point[0], point[1]) for point in points}) < 2:
                skipped += 1
                continue
        else:
            x_ft = getattr(element, "x_ft", None)
            y_ft = getattr(element, "y_ft", None)
            if x_ft is None or y_ft is None:
                skipped += 1
                continue
            points = [ft_to_m(x_ft), ft_to_m(y_ft)]

        prepared.append((points, row))

    field_names = column_config.shapefile_field_names(element_type, columns)
    error = validate_shapefile_field_names(field_names)
    if error:
        raise ValueError(f"Nomes de campos Shapefile inválidos: {error}")
    field_map = []
    for column in columns:
        dbf_name = field_names[column]
        values = [row.get(column) for _, row in prepared]
        kind, size, decimal = _field_definition(values)
        field_map.append((column, dbf_name, kind, size, decimal))

    with shapefile.Writer(str(base_path), shapeType=shape_type, encoding="utf-8") as writer:
        for _, dbf_name, kind, size, decimal in field_map:
            writer.field(dbf_name, kind, size=size, decimal=decimal)

        for geometry, row in prepared:
            if element_type == "Pipe":
                writer.line([geometry])
            else:
                writer.point(*geometry)
            writer.record(*[row.get(column) for column, *_ in field_map])

    base_path.with_suffix(".cpg").write_text("UTF-8", encoding="ascii")
    return {
        "layer": layer_name,
        "element_type": element_type,
        "exported": len(prepared),
        "skipped": skipped,
        "field_map": field_map,
    }


def export_shapefiles(
    selected_groups,
    output_dir,
    column_config,
    selection_name="Selection",
    scenario_id=None,
    progress_callback=None,
):
    """Write selected groups to a new folder of ModelBuilder-ready layers."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=False)

    total = sum(len(elements) for elements in selected_groups.values())
    done = 0
    layers = []
    skipped_types = []

    for element_type, elements in selected_groups.items():
        if element_type not in PROFILE["sheets"]:
            skipped_types.append(element_type)
            done += len(elements)
            continue

        layer = _write_layer(output_dir, element_type, elements, column_config)
        layers.append(layer)
        done += len(elements)
        if progress_callback:
            progress_callback(done, total, f"Gravando camada {layer['layer']}")

    with (output_dir / "field_mapping.csv").open(
        "w", newline="", encoding="utf-8-sig"
    ) as stream:
        writer = csv.writer(stream)
        writer.writerow(["Layer", "OriginalColumn", "ShapefileColumn", "DBFType"])
        for layer in layers:
            for original, dbf_name, kind, _, _ in layer["field_map"]:
                writer.writerow([layer["layer"], original, dbf_name, kind])

    lines = [
        "Model Builder Composer - Exportação GIS",
        f"SelectionSet: {selection_name}",
        f"Scenario ID: {scenario_id}",
        "",
        "As coordenadas foram exportadas em metros.",
        "O arquivo .prj não é criado porque o banco WaterGEMS não informa o CRS.",
        "Defina ou reprojete o CRS antes de importar caso o modelo seja georreferenciado.",
        "",
        "Camadas:",
    ]
    for layer in layers:
        lines.append(
            f"- {layer['layer']}.shp: {layer['exported']} exportado(s); "
            f"{layer['skipped']} sem geometria válida."
        )
    if skipped_types:
        lines.extend(["", "Tipos sem perfil ModelBuilder: " + ", ".join(skipped_types)])
    lines.extend([
        "",
        "Importe primeiro as camadas de pontos; em seguida, Pipes.shp.",
        "Para os pipes, ative 'Establish connectivity using spatial data'.",
        "Consulte field_mapping.csv para os nomes abreviados dos campos DBF.",
    ])
    (output_dir / "README.txt").write_text("\n".join(lines), encoding="utf-8")

    if progress_callback:
        progress_callback(total, total, "Camadas GIS concluídas")
    return output_dir, layers
