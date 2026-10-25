from dataclasses import dataclass, field


@dataclass
class DiagnosticIssue:
    element_type: str
    element_id: int
    label: str
    issue: str
    details: str = ""


@dataclass
class ExtractionStats:
    element_type: str
    examined: int = 0
    exported: int = 0
    active: int = 0
    inactive: int = 0
    unresolved_active_topology: int = 0
    invalid_geometry: int = 0
    invalid_topology: int = 0
    missing_physical: int = 0
    issues: list[DiagnosticIssue] = field(default_factory=list)

    def add_issue(self, element_id, label, issue, details=""):
        self.issues.append(
            DiagnosticIssue(
                element_type=self.element_type,
                element_id=element_id,
                label=label,
                issue=issue,
                details=details,
            )
        )
