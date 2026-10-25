from collections import defaultdict, deque

from readers.common import qident


class TopologyExpansionService:
    """
    Scenario-aware graph expansion over the hydraulic network.

    Graph semantics:
      Pipe -- StartNode / StopNode

    Direction:
      StartNode -> Pipe -> StopNode

    Immediate neighbors:
      Pipe -> its start/stop node
      Node -> connected Pipes

    Expansion is lazy. Node -> pipe queries first collect candidate pipes from
    topology alternatives and then resolve each candidate using the selected
    scenario, preventing stale parent alternatives from creating false links.
    """

    def __init__(self, model_repo, topology_resolver):
        self.model = model_repo
        self.topology = topology_resolver
        self.db = model_repo.db
        self.schema = model_repo.schema
        self.resolver = model_repo.resolver
        self.context = model_repo.context

        self._pipe_endpoints_cache = {}
        self._connected_pipe_cache = {}

    def pipe_endpoints(self, pipe_id):
        pipe_id = int(pipe_id)
        if pipe_id in self._pipe_endpoints_cache:
            return self._pipe_endpoints_cache[pipe_id]

        resolved = self.topology.resolve_pipe_endpoints(pipe_id)
        value = (
            resolved["start_node_id"],
            resolved["start_node_type"],
            resolved["end_node_id"],
            resolved["end_node_type"],
        )
        self._pipe_endpoints_cache[pipe_id] = value
        return value

    def _candidate_pipes_for_node(self, node_id):
        table = "BaseLink_HMIDataSetTopology_Data"
        if not self.schema.table_exists(table):
            return set()

        candidates = set()

        for _, alt_id in self.context.alternatives(2):
            rows = self.db.fetchall(
                f"""
                SELECT DISTINCT t.DomainElementID
                FROM {qident(table)} t
                JOIN HMIDomainElement d
                  ON d.DomainElementID=t.DomainElementID
                 AND COALESCE(d.IsDeleted,0)=0
                WHERE t.AlternativeID=?
                  AND (
                    t.HMITopologyStartNodeID=?
                    OR t.HMITopologyStopNodeID=?
                  )
                """,
                (alt_id, int(node_id), int(node_id)),
            )
            candidates.update(int(r["DomainElementID"]) for r in rows)

        return candidates

    def connected_pipes(self, node_id):
        node_id = int(node_id)
        if node_id in self._connected_pipe_cache:
            return self._connected_pipe_cache[node_id]

        connected = []

        for pipe_id in self._candidate_pipes_for_node(node_id):
            start_id, _, stop_id, _ = self.pipe_endpoints(pipe_id)

            if start_id == node_id:
                connected.append((pipe_id, "out"))
            if stop_id == node_id:
                connected.append((pipe_id, "in"))

        self._connected_pipe_cache[node_id] = connected
        return connected

    @staticmethod
    def _canonical_node_pair(node_id, node_type):
        if node_id is None or node_type in {None, "Unknown", "Pipe"}:
            return None
        return (node_type, int(node_id))

    def immediate_neighbors(self, pair, direction="both"):
        element_type, element_id = pair
        element_id = int(element_id)

        if element_type == "Pipe":
            start_id, start_type, stop_id, stop_type = self.pipe_endpoints(
                element_id
            )

            result = []

            if direction in {"both", "upstream"}:
                p = self._canonical_node_pair(start_id, start_type)
                if p is not None:
                    result.append(p)

            if direction in {"both", "downstream"}:
                p = self._canonical_node_pair(stop_id, stop_type)
                if p is not None:
                    result.append(p)

            return result

        # All supported non-Pipe network elements are node-like in this model.
        result = []

        for pipe_id, relation in self.connected_pipes(element_id):
            if direction == "upstream" and relation != "in":
                continue
            if direction == "downstream" and relation != "out":
                continue
            result.append(("Pipe", pipe_id))

        return result

    def expand(
        self,
        seed_pairs,
        levels=1,
        direction="both",
        max_new=50000,
        max_visited=100000,
        stop_types=None,
        include_stop=True,
        stop_on_first=False,
    ):
        """
        Expand the scenario-aware network graph.

        stop_types:
            Iterable of element type names. When a newly reached element has
            one of these types, that branch stops expanding beyond it.

        include_stop:
            If True, the stop element itself is added to the result.
            If False, the branch stops immediately before it.

        stop_on_first:
            If True, the whole traversal stops when the first stop element is
            found. If False, only that branch stops and the traversal continues
            through the other branches.
        """
        if direction not in {"both", "upstream", "downstream"}:
            raise ValueError("Direção inválida.")

        levels = int(levels)
        if levels < 1:
            raise ValueError("Níveis deve ser >= 1.")

        stop_types = set(stop_types or [])

        seeds = {
            (str(element_type), int(element_id))
            for element_type, element_id in seed_pairs
        }

        visited = set(seeds)
        frontier = set(seeds)
        added = set()
        stop_hits = set()

        truncated = False
        reason = None
        stopped_on_first = False

        for level in range(1, levels + 1):
            next_frontier = set()

            for pair in frontier:
                for neighbor in self.immediate_neighbors(pair, direction):
                    if neighbor in visited:
                        continue

                    visited.add(neighbor)

                    is_stop = neighbor[0] in stop_types

                    if is_stop:
                        stop_hits.add(neighbor)

                        if include_stop:
                            added.add(neighbor)

                        if len(added) >= max_new:
                            truncated = True
                            reason = "max_new"
                            break

                        if len(visited) >= max_visited:
                            truncated = True
                            reason = "max_visited"
                            break

                        if stop_on_first:
                            stopped_on_first = True
                            break

                        # Branch ends here: do not put stop element in frontier.
                        continue

                    next_frontier.add(neighbor)
                    added.add(neighbor)

                    if len(added) >= max_new:
                        truncated = True
                        reason = "max_new"
                        break

                    if len(visited) >= max_visited:
                        truncated = True
                        reason = "max_visited"
                        break

                if truncated or stopped_on_first:
                    break

            frontier = next_frontier

            if truncated or stopped_on_first or not frontier:
                break

        counts = defaultdict(int)
        for element_type, _ in added:
            counts[element_type] += 1

        stop_counts = defaultdict(int)
        for element_type, _ in stop_hits:
            stop_counts[element_type] += 1

        return {
            "added_pairs": added,
            "added_counts": dict(sorted(counts.items())),
            "visited_count": len(visited),
            "truncated": truncated,
            "reason": reason,
            "stop_hits": stop_hits,
            "stop_counts": dict(sorted(stop_counts.items())),
            "stopped_on_first": stopped_on_first,
        }

    def connected_component(
        self,
        seed_pairs,
        max_new=50000,
        max_visited=100000,
        stop_types=None,
        include_stop=True,
        allowed_types=None,
        inactive_as_boundary=False,
        is_active=None,
    ):
        """Return the undirected topological component containing ``seed_pairs``.

        ``stop_types`` are included (when requested), but are never traversed
        past.  ``allowed_types`` limits both inclusion and traversal and is
        useful for sector-style inspections.
        """
        seeds = {
            (str(element_type), int(element_id))
            for element_type, element_id in seed_pairs
        }
        stop_types = set(stop_types or [])
        allowed_types = set(allowed_types or [])

        visited = set(seeds)
        queue = deque(seeds)
        added = set()
        boundary_hits = set()
        inactive_hits = set()
        truncated = False
        reason = None

        while queue:
            pair = queue.popleft()
            for neighbor in self.immediate_neighbors(pair, "both"):
                if neighbor in visited:
                    continue

                visited.add(neighbor)

                if allowed_types and neighbor[0] not in allowed_types:
                    continue

                if (
                    inactive_as_boundary
                    and is_active is not None
                    and is_active(*neighbor) is False
                ):
                    # Inactive elements behave like an excluded endpoint:
                    # they are neither selected nor used to reach beyond it.
                    inactive_hits.add(neighbor)
                    continue

                is_boundary = neighbor[0] in stop_types
                if is_boundary:
                    boundary_hits.add(neighbor)
                    if include_stop:
                        added.add(neighbor)
                    if len(added) >= max_new:
                        truncated, reason = True, "max_new"
                        break
                    if len(visited) >= max_visited:
                        truncated, reason = True, "max_visited"
                        break
                    continue

                added.add(neighbor)
                queue.append(neighbor)

                if len(added) >= max_new:
                    truncated, reason = True, "max_new"
                    break
                if len(visited) >= max_visited:
                    truncated, reason = True, "max_visited"
                    break

            if truncated:
                break

        component_pairs = seeds | added
        counts = defaultdict(int)
        for element_type, _ in component_pairs:
            counts[element_type] += 1

        return {
            "component_pairs": component_pairs,
            "added_pairs": added,
            "counts": dict(sorted(counts.items())),
            "boundary_hits": boundary_hits,
            "inactive_hits": inactive_hits,
            "visited_count": len(visited),
            "truncated": truncated,
            "reason": reason,
        }

    def diagnose_components(
        self,
        available_types,
        max_visited=None,
        max_components=None,
        progress_callback=None,
    ):
        """Partition available network elements into topological islands.

        The scan stops safely instead of reporting a partial result as a
        complete network diagnosis.
        """
        allowed_types = set(available_types)
        remaining = set()
        for element_type in sorted(allowed_types):
            for element_id in self.model.root_ids(element_type):
                remaining.add((element_type, int(element_id)))
        total_pairs = len(remaining)

        # Build the graph once.  The former lazy traversal repeated the same
        # endpoint/database lookups for every island, which made a 246k-node
        # model look like tens of millions of visits in the report.
        adjacency = defaultdict(set)
        pipe_pairs = [pair for pair in remaining if pair[0] == "Pipe"]
        for _, pipe_id in pipe_pairs:
            start_id, start_type, end_id, end_type = self.pipe_endpoints(pipe_id)
            for node_id, node_type in ((start_id, start_type), (end_id, end_type)):
                node_pair = self._canonical_node_pair(node_id, node_type)
                if node_pair is None or node_pair not in remaining:
                    continue
                adjacency[("Pipe", pipe_id)].add(node_pair)
                adjacency[node_pair].add(("Pipe", pipe_id))
            if progress_callback is not None:
                progress_callback(len(adjacency), max(1, total_pairs), "Indexando conexões")

        components = []
        visited_total = 0
        truncated = False
        reason = None

        while remaining:
            if max_components is not None and len(components) >= max_components:
                truncated, reason = True, "max_components"
                break

            if max_visited is not None and visited_total >= max_visited:
                truncated, reason = True, "max_visited"
                break

            seed = next(iter(remaining))
            component = set()
            queue = deque([seed])
            while queue:
                pair = queue.popleft()
                if pair in component:
                    continue
                component.add(pair)
                for neighbor in adjacency.get(pair, ()):
                    if neighbor not in component:
                        queue.append(neighbor)

            remaining.difference_update(component)
            visited_total += len(component)
            if progress_callback is not None:
                progress_callback(visited_total, max(1, total_pairs), "Separando ilhas")

            counts = defaultdict(int)
            for element_type, _ in component:
                counts[element_type] += 1
            components.append({
                "size": len(component),
                "counts": dict(sorted(counts.items())),
                "pairs": sorted(component, key=lambda pair: (pair[0], pair[1])),
            })

        components.sort(key=lambda component: component["size"], reverse=True)
        return {
            "components": components,
            "visited_count": visited_total,
            "truncated": truncated,
            "reason": reason,
            "unscanned_count": len(remaining),
        }
