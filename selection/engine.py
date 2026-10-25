from selection.models import SelectionSet


OPS = {"eq", "ne", "contains", "startswith", "endswith", "gt", "gte", "lt", "lte", "in"}


class SelectionEngine:
    def __init__(self, groups):
        self.groups = groups
        self.by_id = {
            group_name: {e.id: e for e in elements}
            for group_name, elements in groups.items()
        }

        self.global_by_id = {}
        for group_name, elements in groups.items():
            for e in elements:
                self.global_by_id[e.id] = (group_name, e)

    def new_selection(self, name="Selection"):
        return SelectionSet(name=name)

    def available_types(self):
        return [k for k, v in self.groups.items() if v]

    def elements(self, element_type=None):
        if element_type is None:
            for group_name, values in self.groups.items():
                for e in values:
                    yield group_name, e
        else:
            for e in self.groups.get(element_type, []):
                yield element_type, e

    def get_value(self, element, field):
        # Core properties can be referred to directly.
        if hasattr(element, field):
            return getattr(element, field)

        lower = field.lower()
        if lower == "id":
            return element.id
        if lower == "label":
            return element.label
        if lower in {"active", "isactive", "is_active"}:
            return element.is_active
        if lower in {"type", "element_type"}:
            return element.element_type

        # Explicit dynamic namespaces.
        for prefix, attr in (
            ("physical.", "physical"),
            ("udx.", "udx"),
            ("initial.", "initial_settings"),
        ):
            if lower.startswith(prefix):
                key = field[len(prefix):]
                return getattr(element, attr, {}).get(key)

        # Auto-search dynamic fields when the field is unique enough.
        for attr in ("physical", "udx", "initial_settings"):
            data = getattr(element, attr, {})
            if field in data:
                return data[field]

        return None

    @staticmethod
    def _compare(actual, op, expected):
        if op not in OPS:
            raise ValueError(f"Operador não suportado: {op}")

        if op == "eq":
            return actual == expected
        if op == "ne":
            return actual != expected
        if op == "contains":
            return actual is not None and str(expected).lower() in str(actual).lower()
        if op == "startswith":
            return actual is not None and str(actual).lower().startswith(str(expected).lower())
        if op == "endswith":
            return actual is not None and str(actual).lower().endswith(str(expected).lower())
        if op == "in":
            return actual in expected

        if actual is None:
            return False

        try:
            a = float(actual)
            b = float(expected)
        except (TypeError, ValueError):
            return False

        return {
            "gt": a > b,
            "gte": a >= b,
            "lt": a < b,
            "lte": a <= b,
        }[op]

    def filter_elements(self, element_types=None, filters=None, match="all"):
        element_types = element_types or self.available_types()
        filters = filters or []

        if match not in {"all", "any"}:
            raise ValueError("match deve ser 'all' ou 'any'.")

        results = []
        for element_type in element_types:
            for element in self.groups.get(element_type, []):
                checks = []
                for field, op, expected in filters:
                    actual = self.get_value(element, field)
                    checks.append(self._compare(actual, op, expected))

                accepted = all(checks) if match == "all" else any(checks)
                if not filters:
                    accepted = True

                if accepted:
                    results.append((element_type, element))

        return results

    def select_filtered(self, selection, element_types=None, filters=None, match="all"):
        matches = self.filter_elements(
            element_types=element_types,
            filters=filters,
            match=match,
        )
        for element_type, e in matches:
            selection.add(element_type, e.id)
        return len(matches)

    def select_ids(self, selection, ids, element_type=None):
        ids = {int(x) for x in ids}
        count = 0

        if element_type:
            for element_id in ids:
                if element_id in self.by_id.get(element_type, {}):
                    selection.add(element_type, element_id)
                    count += 1
            return count

        for element_id in ids:
            found = self.global_by_id.get(element_id)
            if found:
                group_name, _ = found
                selection.add(group_name, element_id)
                count += 1
        return count

    def select_labels(self, selection, labels, element_type=None):
        wanted = {str(x).casefold() for x in labels}
        count = 0

        for group_name, e in self.elements(element_type):
            if str(e.label).casefold() in wanted:
                selection.add(group_name, e.id)
                count += 1
        return count

    def include_pipe_dependencies(self, selection):
        """Inclui automaticamente os nós usados pelos Pipes selecionados."""
        added = 0
        pipe_ids = list(selection.selected.get("Pipe", set()))

        for pipe_id in pipe_ids:
            pipe = self.by_id.get("Pipe", {}).get(pipe_id)
            if pipe is None:
                continue

            for node_id in (pipe.start_node_id, pipe.end_node_id):
                if node_id is None:
                    continue
                found = self.global_by_id.get(node_id)
                if found is None:
                    continue

                group_name, _ = found
                if not selection.contains(group_name, node_id):
                    selection.add(group_name, node_id)
                    added += 1

        return added

    def selected_groups(self, selection):
        result = {}
        for group_name, ids in selection.selected.items():
            lookup = self.by_id.get(group_name, {})
            values = [lookup[i] for i in sorted(ids) if i in lookup]
            if values:
                result[group_name] = values
        return result

    def summary(self, selection):
        return {
            group_name: len(ids)
            for group_name, ids in selection.selected.items()
            if ids
        }
