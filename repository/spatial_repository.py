from readers.geometry import read_wkb
from readers.common import qident
import time


DIRECTED_TYPES = {
    "TCV",
    "FCV",
    "PRV",
    "PBV",
    "Check Valve",
    "Standard Pump",
    "Variable Speed Pump Battery",
}


class SpatialRepository:
    """
    Scenario-aware, read-only geometry access for the GUI map.

    No full-model extraction is performed. Callers request explicit (type, id)
    pairs. Geometry AlternativeType = 1.
    """

    def __init__(self, resolver, context, schema):
        self.resolver = resolver
        self.context = context
        self.schema = schema

    @staticmethod
    def geometry_table(element_type):
        if element_type == "Pipe":
            return "BaseLink_HmiDataSetGeometry_Data"
        if element_type == "Customer Meter":
            return "CustomerNode_HmiDataSetGeometry_Data"
        if element_type in DIRECTED_TYPES:
            return "BaseDirectedNode_HmiDataSetGeometry_Data"
        return "BaseIdahoNode_HmiDataSetGeometry_Data"

    def geometry_with_source(self, element_type, element_id):
        """
        Resolve HMIGeometry field-by-field through Geometry Alternative
        inheritance.

        Important: a child Alternative may contain a row for the element but
        HMIGeometry itself can be NULL/invalid. In that case geometry must keep
        falling back to parent Alternatives rather than stopping at that row.
        """
        table = self.geometry_table(element_type)

        if not self.schema.table_exists(table):
            return None, {
                "table": table,
                "alternative_id": None,
                "scenario_id": None,
                "attempts": [],
            }

        cols = self.schema.columns(table)
        if "DomainElementID" not in cols:
            return None, {
                "table": table,
                "alternative_id": None,
                "scenario_id": None,
                "attempts": [],
            }

        attempts = []

        # Geometry tables in the WaterGEMS models inspected are alternative-
        # aware. Preserve support for a non-alternative table if encountered.
        if "AlternativeID" not in cols:
            row = self.resolver.db.fetchone(
                f"""
                SELECT *
                FROM {qident(table)}
                WHERE DomainElementID=?
                LIMIT 1
                """,
                (int(element_id),),
            )

            if row is None:
                return None, {
                    "table": table,
                    "alternative_id": None,
                    "scenario_id": None,
                    "attempts": attempts,
                }

            blob = row["HMIGeometry"]
            attempts.append(
                {
                    "scenario_id": None,
                    "alternative_id": None,
                    "has_row": True,
                    "has_blob": blob is not None,
                }
            )

            if blob is None:
                return None, {
                    "table": table,
                    "alternative_id": None,
                    "scenario_id": None,
                    "attempts": attempts,
                }

            try:
                return read_wkb(blob), {
                    "table": table,
                    "alternative_id": None,
                    "scenario_id": None,
                    "attempts": attempts,
                }
            except Exception as exc:
                attempts[-1]["decode_error"] = str(exc)
                return None, {
                    "table": table,
                    "alternative_id": None,
                    "scenario_id": None,
                    "attempts": attempts,
                }

        # Selected scenario -> parent scenario -> ... root.
        for scenario_id, alternative_id in self.context.alternatives(1):
            row = self.resolver.db.fetchone(
                f"""
                SELECT *
                FROM {qident(table)}
                WHERE DomainElementID=?
                  AND AlternativeID=?
                LIMIT 1
                """,
                (int(element_id), int(alternative_id)),
            )

            if row is None:
                attempts.append(
                    {
                        "scenario_id": scenario_id,
                        "alternative_id": alternative_id,
                        "has_row": False,
                        "has_blob": False,
                    }
                )
                continue

            blob = row["HMIGeometry"]

            attempt = {
                "scenario_id": scenario_id,
                "alternative_id": alternative_id,
                "has_row": True,
                "has_blob": blob is not None,
            }
            attempts.append(attempt)

            # Critical fix: do NOT stop merely because a row exists.
            if blob is None:
                continue

            try:
                geometry = read_wkb(blob)
            except Exception as exc:
                attempt["decode_error"] = str(exc)
                continue

            if geometry is None:
                continue

            return geometry, {
                "table": table,
                "alternative_id": alternative_id,
                "scenario_id": scenario_id,
                "attempts": attempts,
            }

        return None, {
            "table": table,
            "alternative_id": None,
            "scenario_id": None,
            "attempts": attempts,
        }

    def geometry(self, element_type, element_id):
        geometry, _ = self.geometry_with_source(
            element_type,
            element_id,
        )
        return geometry

    @staticmethod
    def geometry_bounds(geometry):
        if isinstance(geometry, tuple) and len(geometry) == 2:
            x, y = geometry
            return float(x), float(y), float(x), float(y)

        if isinstance(geometry, list) and geometry:
            xs = [float(p[0]) for p in geometry]
            ys = [float(p[1]) for p in geometry]
            return min(xs), min(ys), max(xs), max(ys)

        return None

    @staticmethod
    def intersects(bounds, extent):
        if bounds is None:
            return False

        minx, miny, maxx, maxy = bounds
        ex_minx, ex_miny, ex_maxx, ex_maxy = extent

        return not (
            maxx < ex_minx
            or minx > ex_maxx
            or maxy < ex_miny
            or miny > ex_maxy
        )

    def geometries_in_extent(
        self,
        typed_ids,
        extent,
        max_checks=40000,
        max_results=25000,
        max_seconds=10.0,
    ):
        """
        Conservative region scan without a spatial index.

        Stops before the UI can be saturated. Returns partial results plus
        a truncation reason when a safety limit is reached.
        """
        started = time.monotonic()
        rows = []
        checked = 0
        reason = None

        for element_type, element_id in typed_ids:
            if checked >= max_checks:
                reason = "max_checks"
                break

            if time.monotonic() - started >= max_seconds:
                reason = "max_seconds"
                break

            geometry = self.geometry(element_type, element_id)
            checked += 1

            if geometry is None:
                continue

            if self.intersects(self.geometry_bounds(geometry), extent):
                rows.append(
                    {
                        "type": element_type,
                        "id": int(element_id),
                        "geometry": geometry,
                    }
                )

                if len(rows) >= max_results:
                    reason = "max_results"
                    break

        return {
            "rows": rows,
            "checked": checked,
            "truncated": reason is not None,
            "reason": reason,
            "elapsed": time.monotonic() - started,
        }

    def geometries(self, typed_ids):
        result = []
        for element_type, element_id in typed_ids:
            geometry = self.geometry(element_type, element_id)
            if geometry is not None:
                result.append(
                    {
                        "type": element_type,
                        "id": int(element_id),
                        "geometry": geometry,
                    }
                )
        return result
