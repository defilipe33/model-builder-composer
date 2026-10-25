FT_TO_M = 0.3048
FT_TO_MM = 304.8
FT_TO_IN = 12.0


class DisplayUnitSystem:
    """
    Controls units shown in GUI/table/samples and numeric filter interpretation.

    WaterGEMS SQLite stores the known dimensional fields below internally in feet.
    SI:
      lengths/elevations -> m
      diameters -> mm
    US:
      lengths/elevations -> ft
      diameters -> in

    Unknown/auxiliary fields are intentionally left unchanged rather than guessed.
    """

    SI = "SI"
    US = "US"

    DIAMETER_FIELDS = {
        "Physical_PipeDiameter",
        "Physical_ValveDiameter",
        "Physical_HydrantLateralDiameter",
        "Physical_Diameter",
        "Physical_TankDiameter",
    }

    LENGTH_FIELDS = {
        "Physical_NodeElevation",
        "Physical_HydrantLateralLength",
        "Physical_TankBaseElevation",
        "Physical_MinimumLevel",
        "Physical_MaximumLevel",
    }

    def __init__(self, system=SI):
        self.system = self.SI
        self.set_system(system)

    def set_system(self, system):
        value = str(system).upper().strip()
        if value not in {self.SI, self.US}:
            raise ValueError("Sistema de unidades deve ser SI ou US.")
        self.system = value

    def field_kind(self, field):
        text = str(field)
        leaf = text.split(".")[-1]

        if leaf in self.DIAMETER_FIELDS:
            return "diameter"

        if leaf in self.LENGTH_FIELDS:
            return "length"

        # Geometry values come from WaterGEMS internal coordinates (feet).
        # ModelBuilder.* fields intentionally keep their explicit export units
        # (e.g. X_m, Diameter_mm) and are therefore not converted here.
        if text.startswith("Geometry.") and leaf in {
            "X", "Y",
            "StartX", "StartY",
            "StopX", "StopY",
            "MinX", "MinY",
            "MaxX", "MaxY",
            "Length",
        }:
            return "length"

        return None

    def unit_label(self, field):
        kind = self.field_kind(field)
        if kind == "diameter":
            return "mm" if self.system == self.SI else "in"
        if kind == "length":
            return "m" if self.system == self.SI else "ft"
        return None

    def display_field_name(self, field):
        unit = self.unit_label(field)
        return f"{field} [{unit}]" if unit else field

    def to_display(self, field, value):
        if value is None:
            return None

        kind = self.field_kind(field)
        if kind is None:
            return value

        try:
            number = float(value)
        except (TypeError, ValueError):
            return value

        if kind == "diameter":
            converted = (
                number * FT_TO_MM
                if self.system == self.SI
                else number * FT_TO_IN
            )
        else:
            converted = (
                number * FT_TO_M
                if self.system == self.SI
                else number
            )

        return round(converted, 6)

    def to_storage(self, field, value):
        """
        Converts a numeric value typed in the currently displayed units
        back to WaterGEMS' internal feet for comparisons.
        """
        kind = self.field_kind(field)
        if kind is None or value is None:
            return value

        if isinstance(value, bool):
            return value

        try:
            number = float(value)
        except (TypeError, ValueError):
            return value

        if kind == "diameter":
            return (
                number / FT_TO_MM
                if self.system == self.SI
                else number / FT_TO_IN
            )

        return (
            number / FT_TO_M
            if self.system == self.SI
            else number
        )
