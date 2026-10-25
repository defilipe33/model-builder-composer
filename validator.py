from dataclasses import dataclass, field


@dataclass
class ValidationReport:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def validate(groups):
    report = ValidationReport()

    nodes = {}
    for elements in groups.values():
        for e in elements:
            if hasattr(e, "x_ft"):
                nodes[e.id] = e

    for p in groups.get("Pipe", []):
        if p.start_node_id is not None and p.start_node_id not in nodes:
            report.warnings.append(
                f"{p.label}: nó inicial {p.start_node_id} não encontrado entre os nós exportados."
            )
        if p.end_node_id is not None and p.end_node_id not in nodes:
            report.warnings.append(
                f"{p.label}: nó final {p.end_node_id} não encontrado entre os nós exportados."
            )

    return report
