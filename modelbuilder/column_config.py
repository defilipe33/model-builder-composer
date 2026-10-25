from dataclasses import dataclass, field
from pathlib import Path
import json
import re
import unicodedata


CORE_DEFAULTS = {
    "Pipe": [
        "SourceElementID",
        "SourceDomainElementID",
        "Label",
        "IsActive",
        "StartNodeLabel",
        "StopNodeLabel",
        "StartNodeSourceID",
        "StopNodeSourceID",
        "StartNodeResolution",
        "StopNodeResolution",
        "Diameter_mm",
        "Material",
        "HazenWilliamsC",
        "ManningsN",
        "Length_m",
        "SourceElementType",
    ],
    "Junction": [
        "SourceElementID",
        "SourceDomainElementID",
        "Label",
        "IsActive",
        "X_m",
        "Y_m",
        "Elevation_m",
        "SourceElementType",
    ],
    "Reservoir": [
        "SourceElementID",
        "SourceDomainElementID",
        "Label",
        "IsActive",
        "X_m",
        "Y_m",
        "Elevation_m",
        "HGLPattern",
        "SourceElementType",
    ],
    "Air Valve": [
        "SourceElementID",
        "SourceDomainElementID",
        "Label",
        "IsActive",
        "X_m",
        "Y_m",
        "Elevation_m",
        "TreatAsJunction",
        "SourceElementType",
    ],
    "Hydrant": [
        "SourceElementID",
        "SourceDomainElementID",
        "Label",
        "IsActive",
        "X_m",
        "Y_m",
        "Elevation_m",
        "LateralDiameter_mm",
        "LateralLength_m",
        "LateralMinorLossCoefficient",
        "SourceElementType",
    ],
    "Tank": [
        "SourceElementID",
        "SourceDomainElementID",
        "Label",
        "IsActive",
        "X_m",
        "Y_m",
        "Elevation_m",
        "TankBaseElevation_m",
        "MinimumLevel_m",
        "MaximumLevel_m",
        "Diameter_mm",
        "SourceElementType",
    ],
    "Conventional Tank": [
        "SourceElementID",
        "SourceDomainElementID",
        "Label",
        "IsActive",
        "X_m",
        "Y_m",
        "Elevation_m",
        "TankBaseElevation_m",
        "MinimumLevel_m",
        "MaximumLevel_m",
        "Diameter_mm",
        "SourceElementType",
    ],
    "TCV": [
        "SourceElementID",
        "SourceDomainElementID",
        "Label",
        "IsActive",
        "X_m",
        "Y_m",
        "Elevation_m",
        "Diameter_mm",
        "DownstreamLinkSourceID",
        "HeadlossCoefficient",
        "TCVDischargeCoefficient",
        "RelativeClosure",
        "SourceElementType",
    ],
    "FCV": [
        "SourceElementID",
        "SourceDomainElementID",
        "Label",
        "IsActive",
        "X_m",
        "Y_m",
        "Elevation_m",
        "Diameter_mm",
        "DownstreamLinkSourceID",
        "FlowSetting",
        "SourceElementType",
    ],
    "PRV": [
        "SourceElementID",
        "SourceDomainElementID",
        "Label",
        "IsActive",
        "X_m",
        "Y_m",
        "Elevation_m",
        "Diameter_mm",
        "DownstreamLinkSourceID",
        "PressureSetting",
        "SourceElementType",
    ],
    "PBV": [
        "SourceElementID",
        "SourceDomainElementID",
        "Label",
        "IsActive",
        "X_m",
        "Y_m",
        "Elevation_m",
        "Diameter_mm",
        "DownstreamLinkSourceID",
        "SourceElementType",
    ],
    "Check Valve": [
        "SourceElementID",
        "SourceDomainElementID",
        "Label",
        "IsActive",
        "X_m",
        "Y_m",
        "Elevation_m",
        "DownstreamLinkSourceID",
        "SourceElementType",
    ],
    "Standard Pump": [
        "SourceElementID",
        "SourceDomainElementID",
        "Label",
        "IsActive",
        "X_m",
        "Y_m",
        "Elevation_m",
        "DownstreamLinkSourceID",
        "PumpDefinitionID",
        "IsVariableSpeedPump",
        "SourceElementType",
    ],
    "Variable Speed Pump Battery": [
        "SourceElementID",
        "SourceDomainElementID",
        "Label",
        "IsActive",
        "X_m",
        "Y_m",
        "Elevation_m",
        "DownstreamLinkSourceID",
        "SourceElementType",
    ],
    "Customer Meter": [
        "SourceElementID",
        "SourceDomainElementID",
        "Label",
        "BillingID",
        "IsActive",
        "X_m",
        "Y_m",
        "Elevation_m",
        "Zone",
        "Concepcao",
        "Setor",
        "Subsetor",
        "Setor_VRP",
        "Categoria",
        "Tipo_Categoria",
        "Economias",
        "Fase",
        "C_S_Tipo1",
        "C_S_Tipo2",
        "Mes_Civil",
        "DemandBase_Ls",
        "DemandPatternID",
        "DemandPatternLabel",
        "AssociatedElementID",
        "AssociatedElementLabel",
        "AssociatedElementType",
        "DemandDistributionStart",
        "SourceElementType",
    ],
}


def _shapefile_base_name(column):
    """Return a DBF-safe short name, retaining the most useful portion."""
    ascii_name = unicodedata.normalize("NFKD", str(column)).encode(
        "ascii", "ignore"
    ).decode("ascii")
    cleaned = re.sub(r"[^A-Za-z0-9_]", "_", ascii_name).strip("_")
    # Namespaced fields (Physical.*, Geometry.*, UDX.*, etc.) carry their
    # distinguishing information at the end. Plain fields are more readable
    # from the beginning, such as StartNodeLabel -> StartNodeL.
    base = cleaned[-10:] if "." in str(column) else cleaned[:10]
    base = base or "FIELD"
    if not re.match(r"[A-Za-z]", base):
        base = f"F{base}"[:10]
    return base


def suggested_shapefile_field_names(columns):
    """Suggest unique DBF names according to field namespace."""
    names = {}
    used = set()
    for column in columns:
        base = _shapefile_base_name(column)
        candidate = base
        suffix = 1
        while candidate.casefold() in used:
            marker = str(suffix)
            candidate = f"{base[:10 - len(marker)]}{marker}"
            suffix += 1
        names[column] = candidate
        used.add(candidate.casefold())
    return names


def validate_shapefile_field_names(names):
    """Return a Portuguese validation message, or None for valid DBF names."""
    used = set()
    for source_column, name in names.items():
        value = str(name).strip()
        if not value:
            return f"O campo '{source_column}' está sem nome."
        if len(value) > 10:
            return f"O nome '{value}' tem mais de 10 caracteres."
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", value):
            return (
                f"O nome '{value}' é inválido. Use letras, números ou _, "
                "começando por uma letra."
            )
        key = value.casefold()
        if key in used:
            return f"O nome '{value}' está repetido nesta camada."
        used.add(key)
    return None


@dataclass
class ColumnConfig:
    columns_by_type: dict[str, list[str]] = field(default_factory=dict)
    available_by_type: dict[str, dict[str, list[str]]] = field(default_factory=dict)
    shapefile_fields_by_type: dict[str, dict[str, str]] = field(default_factory=dict)
    display_names_by_column: dict[str, str] = field(default_factory=dict)
    profile_shapefile_names_by_column: dict[str, str] = field(default_factory=dict)

    def initialize_type(self, element_type, dynamic_fields=None):
        if element_type not in self.available_by_type:
            dynamic_fields = dynamic_fields or {}
            self.available_by_type[element_type] = {
                "core": list(CORE_DEFAULTS.get(element_type, [])),
                "physical": [f"Physical.{x}" for x in dynamic_fields.get("physical", [])],
                "udx": [f"UDX.{x}" for x in dynamic_fields.get("udx", [])],
                "initial": [f"Initial.{x}" for x in dynamic_fields.get("initial", [])],
            }

        if element_type not in self.columns_by_type:
            # Default export remains concise: core only.
            self.columns_by_type[element_type] = list(
                self.available_by_type[element_type]["core"]
            )

    def get(self, element_type):
        return list(self.columns_by_type.get(element_type, []))

    def groups(self, element_type):
        return self.available_by_type.get(
            element_type,
            {"core": [], "physical": [], "udx": [], "initial": []},
        )

    def available(self, element_type):
        groups = self.groups(element_type)
        out = []
        for namespace in ("core", "physical", "udx", "initial"):
            out.extend(groups.get(namespace, []))
        return out

    def set(self, element_type, columns):
        allowed = set(self.available(element_type))
        invalid = [c for c in columns if c not in allowed]
        if invalid:
            raise ValueError(
                "Colunas inválidas: " + ", ".join(invalid)
            )
        selected = list(dict.fromkeys(columns))
        self.columns_by_type[element_type] = selected
        # A field removed from export must lose any previous custom DBF name,
        # so a later re-add receives the normal suggestion again.
        saved = self.shapefile_fields_by_type.get(element_type, {})
        self.shapefile_fields_by_type[element_type] = {
            column: name for column, name in saved.items()
            if column in selected
        }

    def add(self, element_type, columns):
        current = self.get(element_type)
        self.set(element_type, current + list(columns))

    def reset(self, element_type=None):
        if element_type is None:
            for t in list(self.available_by_type):
                self.set(t, self.available_by_type[t].get("core", []))
        else:
            self.set(
                element_type,
                self.available_by_type.get(element_type, {}).get("core", []),
            )

    def select_all(self, element_type):
        self.set(element_type, self.available(element_type))

    def select_group(self, element_type, group):
        group = group.casefold()
        if group not in {"core", "physical", "udx", "initial"}:
            raise ValueError("Grupo deve ser core, physical, udx ou initial.")
        self.set(element_type, self.groups(element_type).get(group, []))

    def shapefile_field_names(self, element_type, columns):
        """Return saved names where present, otherwise current suggestions."""
        suggestions = suggested_shapefile_field_names(columns)
        saved = self.shapefile_fields_by_type.get(element_type, {})
        return {
            column: str(saved.get(
                column,
                self.profile_shapefile_names_by_column.get(
                    column, suggestions[column]
                ),
            ))
            for column in columns
        }

    def set_shapefile_field_names(self, element_type, names):
        names = {str(column): str(name).strip() for column, name in names.items()}
        error = validate_shapefile_field_names(names)
        if error:
            raise ValueError(error)
        self.shapefile_fields_by_type[element_type] = names

    def display_name(self, column):
        """Return the user-facing name configured by a column profile."""
        return self.display_names_by_column.get(str(column), str(column))

    def profile_columns(self):
        """All known export columns, regardless of their element type."""
        columns = set()
        for element_type in self.available_by_type:
            columns.update(self.available(element_type))
        return sorted(columns, key=str.casefold)

    def write_txt_profile(self, path, enabled_columns=None):
        """Write a portable, tab-delimited UTF-8 column profile."""
        columns = self.profile_columns()
        if enabled_columns is None:
            enabled_columns = {
                column
                for element_type in self.available_by_type
                for column in self.get(element_type)
            }
        enabled = {column: column in enabled_columns for column in columns}
        suggested = suggested_shapefile_field_names(columns)
        current_names = {}
        for element_type, names in self.shapefile_fields_by_type.items():
            for column, name in names.items():
                if column not in current_names and name:
                    current_names[column] = name
        lines = [
            "# Model Builder Composer - Perfil de colunas",
            "# Formato: 1 | UTF-8 | campos separados por tabulação",
            "# ChaveColuna\tHabilitada\tNomeExibicao\tNomeShapefile",
            "ChaveColuna\tHabilitada\tNomeExibicao\tNomeShapefile",
        ]
        for column in columns:
            lines.append("\t".join((
                column,
                "TRUE" if enabled[column] else "FALSE",
                self.display_name(column),
                self.profile_shapefile_names_by_column.get(
                    column, current_names.get(column, suggested[column])
                ),
            )))
        Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")
        return len(columns)

    @staticmethod
    def _read_profile_entries(path):
        entries = {}
        errors = []
        for line_no, line in enumerate(
            Path(path).read_text(encoding="utf-8-sig").splitlines(), start=1
        ):
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            fields = [value.strip() for value in line.split("\t")]
            if fields[0] == "ChaveColuna":
                continue
            if len(fields) != 4:
                errors.append(f"linha {line_no}: esperado 4 campos separados por tabulação")
                continue
            column, enabled, display_name, shapefile_name = fields
            value = enabled.casefold()
            if value not in {"true", "false"}:
                errors.append(f"linha {line_no}: Habilitada deve ser TRUE ou FALSE")
                continue
            if not column:
                errors.append(f"linha {line_no}: ChaveColuna vazia")
                continue
            if column in entries:
                errors.append(f"linha {line_no}: ChaveColuna repetida '{column}'")
                continue
            entries[column] = {
                "enabled": value == "true",
                "display_name": display_name or column,
                "shapefile_name": shapefile_name,
            }
        if errors:
            raise ValueError("Perfil TXT inválido:\n- " + "\n- ".join(errors))
        return entries

    def load_txt_profile(self, path, apply_to_export=True):
        """Apply a TXT profile to all applicable element types.

        Applicability is never authored in the file. A row is applied only to
        element types that expose that column in the currently loaded model.
        """
        entries = self._read_profile_entries(path)
        known = set(self.profile_columns())
        unknown = sorted(set(entries) - known, key=str.casefold)
        applicable = {column: data for column, data in entries.items() if column in known}

        for column, data in applicable.items():
            self.display_names_by_column[column] = data["display_name"]
            if data["shapefile_name"]:
                self.profile_shapefile_names_by_column[column] = (
                    data["shapefile_name"]
                )

        for element_type in self.available_by_type:
            available = self.available(element_type)
            selected = set(self.get(element_type))
            if apply_to_export:
                for column, data in applicable.items():
                    if column not in available:
                        continue
                    if data["enabled"]:
                        selected.add(column)
                    else:
                        selected.discard(column)
                ordered = [column for column in available if column in selected]
                self.set(element_type, ordered)
            else:
                ordered = [column for column in available if column in selected]

            names = self.shapefile_field_names(element_type, ordered)
            for column in ordered:
                profile_value = applicable.get(column, {}).get("shapefile_name", "")
                if profile_value:
                    names[column] = profile_value
            error = validate_shapefile_field_names(names)
            if error:
                raise ValueError(
                    f"Perfil TXT inválido para {element_type}: {error}"
                )
            self.set_shapefile_field_names(element_type, names)

        return {
            "read": len(entries),
            "applied": len(applicable),
            "unknown": unknown,
            "enabled_columns": {
                column for column, data in applicable.items() if data["enabled"]
            },
        }

    def save(self, path):
        payload = {
            "columns_by_type": self.columns_by_type,
            "available_by_type": self.available_by_type,
            "shapefile_fields_by_type": self.shapefile_fields_by_type,
            "display_names_by_column": self.display_names_by_column,
            "profile_shapefile_names_by_column": self.profile_shapefile_names_by_column,
        }
        Path(path).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def load(self, path):
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        self.columns_by_type = {
            str(k): [str(x) for x in v]
            for k, v in data.get("columns_by_type", {}).items()
        }
        self.available_by_type = {
            str(k): {
                str(group): [str(x) for x in cols]
                for group, cols in groups.items()
            }
            for k, groups in data.get("available_by_type", {}).items()
        }
        self.shapefile_fields_by_type = {
            str(element_type): {
                str(column): str(name)
                for column, name in names.items()
            }
            for element_type, names in data.get(
                "shapefile_fields_by_type", {}
            ).items()
        }
        self.display_names_by_column = {
            str(column): str(name)
            for column, name in data.get("display_names_by_column", {}).items()
        }
        self.profile_shapefile_names_by_column = {
            str(column): str(name)
            for column, name in data.get(
                "profile_shapefile_names_by_column", {}
            ).items()
        }
