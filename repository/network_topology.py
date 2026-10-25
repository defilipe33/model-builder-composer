from collections import defaultdict
from readers.common import qident
from readers.geometry import read_wkb


NODE_ROOTS = {
    "Junction": "IdahoJunction",
    "Reservoir": "IdahoReservoir",
    "Air Valve": "AirValve",
    "Hydrant": "IdahoHydrant",
    "Tank": "IdahoTank",
    "Conventional Tank": "ConventionalTank",
    "TCV": "TCV",
    "FCV": "FCV",
    "PRV": "PRV",
    "PBV": "PBV",
    "Check Valve": "CheckValve",
    "Standard Pump": "StandardPump",
    "Variable Speed Pump Battery": "VariableSpeedPumpBattery",
}

DIRECTED_TYPES = {
    "TCV", "FCV", "PRV", "PBV", "Check Valve",
    "Standard Pump", "Variable Speed Pump Battery",
}


class NetworkTopologyResolver:
    """
    Resolve endpoints de Pipes usando:
      1) BaseLink topology direta;
      2) DirectedNode.DownstreamLinkID;
      3) coordenadas dos nós como fallback.

    A resolução geométrica é propositalmente conservadora.
    """

    def __init__(self, db, schema, common, resolver, context):
        self.db = db
        self.schema = schema
        self.common = common
        self.resolver = resolver
        self.context = context
        self._directed_by_downstream = None
        self._node_type_cache = {}
        self._node_point_cache = {}

    def _resolve_directed_map(self):
        if self._directed_by_downstream is not None:
            return self._directed_by_downstream

        result = {}
        table = "BaseDirectedNode_HMIDataSetTopology_Data"
        if not self.schema.table_exists(table):
            self._directed_by_downstream = result
            return result

        for scenario_id, alt_id in self.context.alternatives(2):
            rows = self.db.fetchall(
                f"""
                SELECT t.DomainElementID, t.HMITopologyDownstreamLinkID
                FROM {qident(table)} t
                JOIN HMIDomainElement d
                  ON d.DomainElementID=t.DomainElementID
                 AND COALESCE(d.IsDeleted,0)=0
                WHERE t.AlternativeID=?
                  AND t.HMITopologyDownstreamLinkID IS NOT NULL
                """,
                (alt_id,),
            )

            # Higher-priority alternative wins because we fill only once.
            for r in rows:
                link_id = r["HMITopologyDownstreamLinkID"]
                if link_id not in result:
                    result[link_id] = r["DomainElementID"]

        self._directed_by_downstream = result
        return result

    def _node_type(self, node_id):
        if node_id in self._node_type_cache:
            return self._node_type_cache[node_id]

        for element_type, table in NODE_ROOTS.items():
            if not self.schema.table_exists(table):
                continue
            row = self.db.fetchone(
                f"""
                SELECT 1
                FROM {qident(table)} r
                JOIN HMIDomainElement d
                  ON d.DomainElementID=r.DomainElementID
                 AND COALESCE(d.IsDeleted,0)=0
                WHERE r.DomainElementID=?
                LIMIT 1
                """,
                (node_id,),
            )
            if row is not None:
                self._node_type_cache[node_id] = element_type
                return element_type

        self._node_type_cache[node_id] = "Unknown"
        return "Unknown"

    def _node_point(self, node_id):
        if node_id in self._node_point_cache:
            return self._node_point_cache[node_id]

        element_type = self._node_type(node_id)
        table = (
            "BaseDirectedNode_HmiDataSetGeometry_Data"
            if element_type in DIRECTED_TYPES
            else "BaseIdahoNode_HmiDataSetGeometry_Data"
        )

        row, _, _ = self.resolver.resolve_row(
            table, node_id, 1, self.context
        )
        point = None
        if row is not None and row["HMIGeometry"] is not None:
            decoded = read_wkb(row["HMIGeometry"])
            if isinstance(decoded, tuple):
                point = decoded

        self._node_point_cache[node_id] = point
        return point

    def _candidate_nodes_near_point(self, point, tolerance=1e-6):
        if point is None:
            return []

        x, y = point
        candidates = []

        # Query only the geometry tables, then resolve node type lazily.
        for table in (
            "BaseIdahoNode_HmiDataSetGeometry_Data",
            "BaseDirectedNode_HmiDataSetGeometry_Data",
        ):
            if not self.schema.table_exists(table):
                continue

            for scenario_id, alt_id in self.context.alternatives(1):
                rows = self.db.fetchall(
                    f"""
                    SELECT g.DomainElementID, g.HMIGeometry
                    FROM {qident(table)} g
                    JOIN HMIDomainElement d
                      ON d.DomainElementID=g.DomainElementID
                     AND COALESCE(d.IsDeleted,0)=0
                    WHERE g.AlternativeID=?
                    """,
                    (alt_id,),
                )
                for r in rows:
                    if r["HMIGeometry"] is None:
                        continue
                    decoded = read_wkb(r["HMIGeometry"])
                    if not isinstance(decoded, tuple):
                        continue
                    dx = decoded[0] - x
                    dy = decoded[1] - y
                    if dx * dx + dy * dy <= tolerance * tolerance:
                        candidates.append(r["DomainElementID"])

                # Only the highest-priority geometry alternative is needed.
                break

        # Deduplicate preserving order.
        seen = set()
        out = []
        for node_id in candidates:
            if node_id not in seen:
                seen.add(node_id)
                out.append(node_id)
        return out

    def resolve_pipe_endpoints(self, pipe_id, geometry=None):
        direct_row, _, _ = self.resolver.resolve_row(
            "BaseLink_HMIDataSetTopology_Data",
            pipe_id,
            2,
            self.context,
        )

        start_id = end_id = None
        start_resolution = end_resolution = ""

        if direct_row is not None:
            start_id = direct_row["HMITopologyStartNodeID"]
            end_id = direct_row["HMITopologyStopNodeID"]

            if start_id is not None:
                start_resolution = "BaseLink"
            if end_id is not None:
                end_resolution = "BaseLink"

        directed_map = self._resolve_directed_map()

        # DirectedNode -> downstream link means that directed node is the start endpoint.
        directed_start = directed_map.get(pipe_id)
        if start_id is None and directed_start is not None:
            start_id = directed_start
            start_resolution = "DirectedNode.DownstreamLinkID"

        # Geometry fallback.
        if isinstance(geometry, list) and geometry:
            if start_id is None:
                candidates = self._candidate_nodes_near_point(geometry[0])
                if len(candidates) == 1:
                    start_id = candidates[0]
                    start_resolution = "Geometry"
                elif len(candidates) > 1:
                    # If one candidate is directed and owns this downstream link, prefer it.
                    if directed_start in candidates:
                        start_id = directed_start
                        start_resolution = "Geometry+DirectedNode"

            if end_id is None:
                candidates = self._candidate_nodes_near_point(geometry[-1])

                # Avoid selecting same endpoint unless the model truly loops back.
                candidates = [c for c in candidates if c != start_id]

                if len(candidates) == 1:
                    end_id = candidates[0]
                    end_resolution = "Geometry"
                elif len(candidates) > 1:
                    # Prefer non-directed nodes for stop if unique among candidates.
                    non_directed = [
                        c for c in candidates
                        if self._node_type(c) not in DIRECTED_TYPES
                    ]
                    if len(non_directed) == 1:
                        end_id = non_directed[0]
                        end_resolution = "Geometry(non-directed preferred)"

        return {
            "start_node_id": start_id,
            "end_node_id": end_id,
            "start_node_type": self._node_type(start_id) if start_id is not None else "Unknown",
            "end_node_type": self._node_type(end_id) if end_id is not None else "Unknown",
            "start_node_label": self.common.label(start_id) if start_id is not None else "",
            "end_node_label": self.common.label(end_id) if end_id is not None else "",
            "start_resolution": start_resolution or "Unresolved",
            "end_resolution": end_resolution or "Unresolved",
        }
