from readers.common import qident
from display_units import DisplayUnitSystem
from modelbuilder.column_config import CORE_DEFAULTS
from modelbuilder.profiles.watergems_2019 import PROFILE


CORE_FIELD_MAP = {
    "ID": "DomainElementID",
    "Label": "Label",
    "IsActive": "IsActive",
}


NODE_LIKE_TYPES = {
    "Junction",
    "Reservoir",
    "Air Valve",
    "Hydrant",
    "Tank",
    "Conventional Tank",
    "TCV",
    "FCV",
    "PRV",
    "PBV",
    "Check Valve",
    "Standard Pump",
    "Variable Speed Pump Battery",
    "Customer Meter",
}


def geometry_fields_for_type(element_type):
    common = [
        "Geometry.HasGeometry",
        "Geometry.SourceScenarioID",
        "Geometry.AlternativeID",
        "Geometry.DiagnosticStatus",
    ]

    if element_type == "Pipe":
        return common + [
            "Geometry.VertexCount",
            "Geometry.Length",
            "Geometry.IsZeroLength",
            "Geometry.HasCoincidentEndpoints",
            "Geometry.StartNodeID",
            "Geometry.StartNodeLabel",
            "Geometry.StartNodeType",
            "Geometry.StartNodeResolution",
            "Geometry.StartX",
            "Geometry.StartY",
            "Geometry.StopNodeID",
            "Geometry.StopNodeLabel",
            "Geometry.StopNodeType",
            "Geometry.StopNodeResolution",
            "Geometry.StopX",
            "Geometry.StopY",
        ]

    if element_type in NODE_LIKE_TYPES:
        return common + [
            "Geometry.X",
            "Geometry.Y",
        ]

    return common


def modelbuilder_fields_for_type(element_type):
    return [
        f"ModelBuilder.{name}"
        for name in CORE_DEFAULTS.get(element_type, [])
    ]


class TableQueryService:
    """
    Serviço de consulta para a GUI.

    Mantém a interface lazy:
    - paginação;
    - filtros retornam IDs;
    - valores de colunas dinâmicas são resolvidos apenas para a página atual.

    Nesta V3.1, filtros Core/Physical/UDX/Initial reutilizam o QueryRepository
    scenario-aware já existente.
    """

    def __init__(
        self,
        model_repo,
        query_repo,
        resolver,
        context,
        common,
        schema,
        spatial_repo=None,
        topology_resolver=None,
        extraction=None,
    ):
        self.model = model_repo
        self.query = query_repo
        self.resolver = resolver
        self.context = context
        self.common = common
        self.schema = schema
        self.spatial_repo = spatial_repo
        self.topology_resolver = topology_resolver
        self.extraction = extraction
        self._modelbuilder_cache = {}
        self.display_units = DisplayUnitSystem(DisplayUnitSystem.SI)

    def set_unit_system(self, system):
        self.display_units.set_system(system)

    def unit_system(self):
        return self.display_units.system

    def display_field_name(self, field):
        return self.display_units.display_field_name(field)

    def all_ids(self, element_type):
        return self.model.root_ids(element_type)

    def filtered_ids(self, element_type, filter_def=None):
        if filter_def is None:
            return self.all_ids(element_type)

        field = filter_def.field
        op = filter_def.operator
        value = filter_def.value

        if field == "Core.IsActive":
            if op not in {"eq", "ne"}:
                raise ValueError("IsActive aceita apenas = ou !=.")
            expected = bool(value)
            ids = self.query.filter_active(element_type, expected)
            if op == "eq":
                return ids
            all_ids = set(self.all_ids(element_type))
            return [x for x in all_ids if x not in set(ids)]

        if field == "Core.Label":
            ids = self.all_ids(element_type)
            result = []
            for element_id in ids:
                label = self.common.label(element_id)
                if self._compare(label, op, value):
                    result.append(element_id)
            return result

        if field == "Core.ID":
            ids = self.all_ids(element_type)
            return [x for x in ids if self._compare(x, op, value)]

        if "." not in field:
            raise ValueError("Campo inválido.")

        namespace, actual_field = field.split(".", 1)
        namespace = namespace.casefold()

        if namespace == "physical":
            storage_value = self.display_units.to_storage(field, value)
            return self.query.filter_dynamic(
                element_type, "physical", actual_field, op, storage_value
            )

        if namespace == "udx":
            return self.query.filter_dynamic(
                element_type, "udx", actual_field, op, value
            )

        if namespace == "initial":
            # QueryRepository V2 não tinha namespace initial.
            # Resolver seletivamente apenas os IDs candidatos.
            storage_value = self.display_units.to_storage(field, value)
            return self._filter_initial(
                element_type, actual_field, op, storage_value
            )

        if namespace in {"geometry", "modelbuilder"}:
            storage_value = (
                self.display_units.to_storage(field, value)
                if namespace == "geometry"
                else value
            )
            result = []
            for element_id in self.all_ids(element_type):
                actual = self.raw_value_for_field(
                    element_type, element_id, field
                )
                if self._compare(actual, op, storage_value):
                    result.append(element_id)
            return result

        raise ValueError(f"Namespace não suportado: {namespace}")

    def _filter_initial(self, element_type, field, op, expected):
        from repository.dynamic_fields import ELEMENT_TABLES

        tables = ELEMENT_TABLES.get(element_type, {}).get("initial", [])
        result = []

        for element_id in self.all_ids(element_type):
            actual = None
            for table in tables:
                if not self.schema.table_exists(table):
                    continue
                data, _, _ = self.resolver.resolve_dict(
                    table, element_id, 21, self.context
                )
                if field in data and data[field] is not None:
                    actual = data[field]

            if self._compare(actual, op, expected):
                result.append(element_id)

        return result

    def page(self, element_type, ids, offset, limit, visible_columns):
        page_ids = ids[offset: offset + limit]
        labels = self.common.labels(page_ids)
        rows = []

        for element_id in page_ids:
            row = {
                "Core.ID": element_id,
                "Core.Label": labels.get(int(element_id), ""),
            }

            for field in visible_columns:
                if field in row:
                    continue
                row[field] = self.value_for_field(element_type, element_id, field)

            rows.append(row)

        return rows

    def value_for_field(self, element_type, element_id, field):
        value = self.raw_value_for_field(element_type, element_id, field)
        return self.display_units.to_display(field, value)

    def raw_value_for_field(self, element_type, element_id, field):
        if field == "Core.ID":
            return element_id
        if field == "Core.Label":
            return self.common.label(element_id)

        if field == "Core.IsActive":
            table = self._active_table(element_type)
            row, _, _ = self.resolver.resolve_row(
                table, element_id, 3, self.context
            )
            if row is None:
                return None
            value = row["HMIActiveTopologyIsActive"]
            return None if value is None else bool(value)

        if "." not in field:
            return None

        namespace, actual_field = field.split(".", 1)
        namespace = namespace.casefold()

        if namespace == "physical":
            return self._dynamic_value(
                element_type, element_id, "physical", actual_field, 4
            )

        if namespace == "udx":
            return self._dynamic_value(
                element_type, element_id, "udx", actual_field, 100
            )

        if namespace == "initial":
            return self._dynamic_value(
                element_type, element_id, "initial", actual_field, 21
            )

        if namespace == "geometry":
            return self._geometry_value(
                element_type, element_id, actual_field
            )

        if namespace == "modelbuilder":
            return self._modelbuilder_value(
                element_type, element_id, actual_field
            )

        return None

    def _dynamic_value(self, element_type, element_id, namespace, field, alt_type):
        from repository.dynamic_fields import ELEMENT_TABLES

        tables = ELEMENT_TABLES.get(element_type, {}).get(namespace, [])
        value = None

        for table in tables:
            if not self.schema.table_exists(table):
                continue
            data, _, _ = self.resolver.resolve_dict(
                table, element_id, alt_type, self.context
            )
            if field in data and data[field] is not None:
                value = data[field]

        return value


    @staticmethod
    def _polyline_length(geometry):
        if not isinstance(geometry, list) or len(geometry) < 2:
            return None

        total = 0.0
        for p1, p2 in zip(geometry[:-1], geometry[1:]):
            try:
                dx = float(p2[0]) - float(p1[0])
                dy = float(p2[1]) - float(p1[1])
            except Exception:
                return None
            total += (dx * dx + dy * dy) ** 0.5
        return total

    @staticmethod
    def _coincident_points(p1, p2, tolerance_ft=0.003280839895):
        # 1 mm tolerance in WaterGEMS internal feet.
        if not (
            isinstance(p1, tuple) and len(p1) == 2
            and isinstance(p2, tuple) and len(p2) == 2
        ):
            return None

        dx = float(p2[0]) - float(p1[0])
        dy = float(p2[1]) - float(p1[1])
        return (dx * dx + dy * dy) ** 0.5 <= tolerance_ft

    def _geometry_value(self, element_type, element_id, actual_field):
        if self.spatial_repo is None:
            return None

        geometry, source = self.spatial_repo.geometry_with_source(
            element_type,
            int(element_id),
        )

        if actual_field == "HasGeometry":
            return geometry is not None
        if actual_field == "SourceScenarioID":
            return source.get("scenario_id")
        if actual_field == "AlternativeID":
            return source.get("alternative_id")

        if actual_field == "DiagnosticStatus":
            if geometry is None:
                return "SEM_GEOMETRIA"

            if element_type == "Pipe":
                length = self._polyline_length(geometry)
                if length is not None and length <= 0.003280839895:
                    return "COMPRIMENTO_ZERO"

            return "OK"

        if element_type == "Pipe":
            topology = (
                self.topology_resolver.resolve_pipe_endpoints(
                    int(element_id),
                    geometry=geometry if isinstance(geometry, list) else None,
                )
                if self.topology_resolver is not None
                else {}
            )

            mapping = {
                "VertexCount": len(geometry) if isinstance(geometry, list) else 0,
                "Length": self._polyline_length(geometry),
                "IsZeroLength": (
                    self._polyline_length(geometry) is not None
                    and self._polyline_length(geometry) <= 0.003280839895
                ),
                "StartNodeID": topology.get("start_node_id"),
                "StartNodeLabel": topology.get("start_node_label"),
                "StartNodeType": topology.get("start_node_type"),
                "StartNodeResolution": topology.get("start_resolution"),
                "StopNodeID": topology.get("end_node_id"),
                "StopNodeLabel": topology.get("end_node_label"),
                "StopNodeType": topology.get("end_node_type"),
                "StopNodeResolution": topology.get("end_resolution"),
            }

            if actual_field in mapping:
                return mapping[actual_field]

            start_type = topology.get("start_node_type")
            start_id = topology.get("start_node_id")
            stop_type = topology.get("end_node_type")
            stop_id = topology.get("end_node_id")

            start_point = None
            stop_point = None

            if start_id is not None and start_type not in {None, "Unknown"}:
                start_point = self.spatial_repo.geometry(
                    start_type, int(start_id)
                )
            if stop_id is not None and stop_type not in {None, "Unknown"}:
                stop_point = self.spatial_repo.geometry(
                    stop_type, int(stop_id)
                )

            if actual_field == "HasCoincidentEndpoints":
                return self._coincident_points(start_point, stop_point)

            if actual_field == "StartX":
                return start_point[0] if isinstance(start_point, tuple) else None
            if actual_field == "StartY":
                return start_point[1] if isinstance(start_point, tuple) else None
            if actual_field == "StopX":
                return stop_point[0] if isinstance(stop_point, tuple) else None
            if actual_field == "StopY":
                return stop_point[1] if isinstance(stop_point, tuple) else None

            return None

        if isinstance(geometry, tuple) and len(geometry) == 2:
            if actual_field == "X":
                return geometry[0]
            if actual_field == "Y":
                return geometry[1]

        return None

    def _modelbuilder_row(self, element_type, element_id):
        key = (element_type, int(element_id))
        if key in self._modelbuilder_cache:
            return self._modelbuilder_cache[key]

        row = {}

        if self.extraction is not None:
            groups = self.extraction.extract_selected(
                {element_type: {int(element_id)}}
            )
            elements = groups.get(element_type, [])

            if elements:
                mapping = PROFILE["sheets"].get(element_type)
                if mapping is not None:
                    _, mapper = mapping
                    row = mapper(elements[0])
                    row["SourceElementType"] = element_type

        self._modelbuilder_cache[key] = row
        return row

    def _modelbuilder_value(self, element_type, element_id, actual_field):
        return self._modelbuilder_row(
            element_type, element_id
        ).get(actual_field)


    def available_field_names(self, element_type, column_config):
        groups = column_config.groups(element_type)
        return (
            ["Core.ID", "Core.Label", "Core.IsActive"]
            + geometry_fields_for_type(element_type)
            + modelbuilder_fields_for_type(element_type)
            + list(groups.get("physical", []))
            + list(groups.get("udx", []))
            + list(groups.get("initial", []))
        )

    def expression_ids(self, element_type, expression, column_config):
        from repository.expression_filter import parse_expression, Binary
        ast = parse_expression(expression)
        all_ids = set(self.all_ids(element_type))
        available = set(self.available_field_names(element_type, column_config))

        def eval_node(node):
            if isinstance(node, Binary):
                left = eval_node(node.left)
                right = eval_node(node.right)
                return left & right if node.operator == "AND" else left | right

            if node.field not in available:
                return set()

            op = node.operator
            value = node.value
            if op == "LIKE" or (op in {"=", "!="} and isinstance(value, str) and "%" in value):
                text = str(value)
                starts, ends = text.startswith("%"), text.endswith("%")
                needle = text.strip("%")
                if starts and ends: simple = "contains"
                elif starts: simple = "endswith"
                elif ends: simple = "startswith"
                else: simple = "eq"
                ids = set(self._condition_ids(element_type, node.field, simple, needle))
                return all_ids - ids if op == "!=" else ids

            mapping = {"=":"eq", "!=":"ne", ">":"gt", ">=":"gte", "<":"lt", "<=":"lte"}
            return set(self._condition_ids(element_type, node.field, mapping[op], value))

        return sorted(eval_node(ast))

    def _condition_ids(self, element_type, field, op, value):
        from gui.filter_models import FilterDefinition
        return self.filtered_ids(element_type, FilterDefinition(field, op, value))

    def sample_values(self, element_type, field, limit=100, scan_all=False):
        ids = self.all_ids(element_type)
        if not scan_all:
            ids = ids[:max(1000, limit * 10)]
        values=[]; seen=set()
        for element_id in ids:
            value=self.value_for_field(element_type, element_id, field)
            if value is None: continue
            key=repr(value)
            if key in seen: continue
            seen.add(key); values.append(value)
            if not scan_all and len(values) >= limit: break
        return values

    @staticmethod
    def _compare(actual, op, expected):
        if op == "eq":
            return actual == expected
        if op == "ne":
            return actual != expected
        if op == "contains":
            return actual is not None and str(expected).casefold() in str(actual).casefold()
        if op == "startswith":
            return actual is not None and str(actual).casefold().startswith(str(expected).casefold())
        if op == "endswith":
            return actual is not None and str(actual).casefold().endswith(str(expected).casefold())

        if actual is None:
            return False

        try:
            a = float(actual)
            b = float(expected)
        except (TypeError, ValueError):
            return False

        if op == "gt":
            return a > b
        if op == "gte":
            return a >= b
        if op == "lt":
            return a < b
        if op == "lte":
            return a <= b

        raise ValueError(f"Operador não suportado: {op}")

    @staticmethod
    def _active_table(element_type):
        if element_type == "Pipe":
            return "BaseLink_HMIActiveTopology_Data"
        if element_type == "Customer Meter":
            return "CustomerNode_HMIActiveTopology_Data"

        if element_type in {
            "TCV", "FCV", "PRV", "PBV",
            "Check Valve", "Standard Pump",
            "Variable Speed Pump Battery",
        }:
            return "BaseDirectedNode_HMIActiveTopology_Data"

        return "BaseIdahoNode_HMIActiveTopology_Data"
