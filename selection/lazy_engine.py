from selection.models import SelectionSet


TYPE_ALIASES = {
    "pipe": "Pipe",
    "pipes": "Pipe",
    "junction": "Junction",
    "junctions": "Junction",
    "reservoir": "Reservoir",
    "reservoirs": "Reservoir",
    "air valve": "Air Valve",
    "airvalve": "Air Valve",
    "airvalves": "Air Valve",
    "hydrant": "Hydrant",
    "hydrants": "Hydrant",
    "tank": "Tank",
    "tanks": "Tank",
    "conventional tank": "Conventional Tank",
    "conventionaltank": "Conventional Tank",
    "tcv": "TCV",
    "fcv": "FCV",
    "prv": "PRV",
    "pbv": "PBV",
    "check valve": "Check Valve",
    "checkvalve": "Check Valve",
    "pump": "Standard Pump",
    "standard pump": "Standard Pump",
    "standardpump": "Standard Pump",
    "vspb": "Variable Speed Pump Battery",
    "variable speed pump battery": "Variable Speed Pump Battery",
    "customer meter": "Customer Meter",
    "customer meters": "Customer Meter",
    "customermeter": "Customer Meter",
}


class LazySelectionEngine:
    def __init__(self, model_repository, query_repository, topology_resolver):
        self.model = model_repository
        self.query = query_repository
        self.topology_resolver = topology_resolver

    def new_selection(self, name="Selection"):
        return SelectionSet(name=name)

    def normalize_type(self, raw):
        key = str(raw).strip().casefold()
        if key in TYPE_ALIASES:
            return TYPE_ALIASES[key]

        for element_type, _ in self.available_types():
            if element_type.casefold() == key:
                return element_type

        raise ValueError(
            f'Tipo "{raw}" não reconhecido. Use "types" para ver os tipos disponíveis.'
        )

    def available_types(self):
        return self.model.available_types()

    def preview(self, element_type, limit=200, offset=0):
        element_type = self.normalize_type(element_type)
        if limit <= 0:
            raise ValueError("O limite do preview deve ser maior que zero.")
        if limit > 5000:
            raise ValueError("O limite máximo do preview é 5000.")
        return self.model.preview(element_type, limit=limit, offset=offset)

    def select_type(self, selection, element_type):
        element_type = self.normalize_type(element_type)
        ids = self.model.root_ids(element_type)
        for element_id in ids:
            selection.add(element_type, element_id)
        return len(ids)

    def select_ids(self, selection, element_type, ids):
        element_type = self.normalize_type(element_type)

        report = {
            "requested": len(ids),
            "selected_now": 0,
            "already_selected": 0,
            "not_found": [],
            "deleted": [],
        }

        for element_id in ids:
            element_id = int(element_id)

            if selection.contains(element_type, element_id):
                report["already_selected"] += 1
                continue

            if self.model.is_deleted_id(element_id):
                report["deleted"].append(element_id)
                continue

            if not self.model.has_id(element_type, element_id):
                report["not_found"].append(element_id)
                continue

            selection.add(element_type, element_id)
            report["selected_now"] += 1

        return report

    def select_labels(self, selection, element_type, labels):
        element_type = self.normalize_type(element_type)
        ids = self.model.find_ids_by_label(element_type, labels)
        for element_id in ids:
            selection.add(element_type, element_id)
        return len(ids)

    def select_active(self, selection, element_type, expected):
        element_type = self.normalize_type(element_type)
        ids = self.query.filter_active(element_type, expected)
        for element_id in ids:
            selection.add(element_type, element_id)
        return len(ids)

    def select_filter(self, selection, element_type, namespace, field, op, expected):
        element_type = self.normalize_type(element_type)
        ids = self.query.filter_dynamic(
            element_type, namespace, field, op, expected
        )
        for element_id in ids:
            selection.add(element_type, element_id)
        return len(ids)

    def dependency_policy(self, element_type):
        element_type = self.normalize_type(element_type)

        if element_type == "Pipe":
            return {
                "requires_dependencies": True,
                "description": (
                    "Pipes require their start and stop node-like elements "
                    "for ModelBuilder connectivity."
                ),
            }

        return {
            "requires_dependencies": False,
            "description": (
                "Point elements are self-contained for selection and do not "
                "receive automatic dependencies."
            ),
        }

    def include_pipe_dependencies(self, selection):
        added = 0
        pipe_ids = sorted(selection.selected.get("Pipe", set()))
        if not pipe_ids:
            return 0

        for pipe_id in pipe_ids:
            row, _, _ = self.model.resolver.resolve_row(
                "BaseLink_HmiDataSetGeometry_Data",
                pipe_id,
                1,
                self.model.context,
            )
            geometry = None
            if row is not None and row["HMIGeometry"] is not None:
                from readers.geometry import read_wkb
                decoded = read_wkb(row["HMIGeometry"])
                if isinstance(decoded, list):
                    geometry = decoded

            resolved = self.topology_resolver.resolve_pipe_endpoints(
                pipe_id, geometry=geometry
            )

            for node_id, node_type in (
                (resolved["start_node_id"], resolved["start_node_type"]),
                (resolved["end_node_id"], resolved["end_node_type"]),
            ):
                if node_id is None or node_type in {"Unknown", "Pipe"}:
                    continue

                try:
                    canonical_type = self.normalize_type(node_type)
                except ValueError:
                    canonical_type = node_type

                if not selection.contains(canonical_type, node_id):
                    selection.add(canonical_type, node_id)
                    added += 1

        return added

    def summary(self, selection):
        return {
            group_name: len(ids)
            for group_name, ids in selection.selected.items()
            if ids
        }
