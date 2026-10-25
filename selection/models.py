from dataclasses import dataclass, field
from pathlib import Path
import json


@dataclass
class SelectionSet:
    name: str = "Selection"
    selected: dict[str, set[int]] = field(default_factory=dict)

    def add(self, element_type, element_id):
        self.selected.setdefault(element_type, set()).add(int(element_id))

    def remove(self, element_type, element_id):
        self.selected.setdefault(element_type, set()).discard(int(element_id))

    def contains(self, element_type, element_id):
        return int(element_id) in self.selected.get(element_type, set())

    def count(self, element_type=None):
        if element_type is not None:
            return len(self.selected.get(element_type, set()))
        return sum(len(v) for v in self.selected.values())

    def clear(self):
        self.selected.clear()

    def save(self, path):
        path = Path(path)
        data = {
            "name": self.name,
            "selected": {
                k: sorted(v)
                for k, v in self.selected.items()
            },
        }
        path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path):
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        obj = cls(name=data.get("name", "Selection"))
        obj.selected = {
            k: {int(x) for x in values}
            for k, values in data.get("selected", {}).items()
        }
        return obj
