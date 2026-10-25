from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QCheckBox,
    QPushButton,
    QScrollArea,
    QWidget,
    QDialogButtonBox,
    QTabWidget,
)


GROUPS = [
    ("core", "Core"),
    ("geometry", "Geometry"),
    ("modelbuilder", "ModelBuilder / Exportação"),
    ("physical", "Physical"),
    ("udx", "User Data Extensions"),
    ("initial", "Initial Settings"),
]


class TableColumnsDialog(QDialog):
    def __init__(self, backend, element_type, selected_columns, parent=None):
        super().__init__(parent)
        self.backend = backend
        self.element_type = element_type
        self.selected_columns = list(selected_columns)
        self.checkboxes = {}

        self.setWindowTitle(f"Colunas da tabela — {element_type}")
        self.resize(700, 620)

        layout = QVBoxLayout(self)

        note = QLabel(
            "Estas colunas controlam apenas a visualização da tabela.\n"
            "Geometry mostra a geometria/topologia resolvida para inspeção. "
            "ModelBuilder / Exportação mostra os valores canônicos que o "
            "exportador produz.\n"
            "As colunas efetivamente gravadas no Excel continuam sendo "
            "configuradas separadamente em Colunas exportação."
        )
        note.setWordWrap(True)
        layout.addWidget(note)

        buttons_top = QHBoxLayout()
        self.btn_all = QPushButton("Selecionar tudo")
        self.btn_min = QPushButton("ID + Label")
        self.btn_none = QPushButton("Limpar")
        buttons_top.addWidget(self.btn_all)
        buttons_top.addWidget(self.btn_min)
        buttons_top.addWidget(self.btn_none)
        buttons_top.addStretch(1)
        layout.addLayout(buttons_top)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 1)

        available = backend.all_available_table_fields() if element_type == "__ALL__" else backend.available_table_fields(element_type)
        current = set(selected_columns)

        for group_key, title in GROUPS:
            page = QWidget()
            page_layout = QVBoxLayout(page)
            page_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

            fields = available.get(group_key, [])
            if not fields:
                page_layout.addWidget(QLabel("Nenhum campo disponível."))
            else:
                for field in fields:
                    cb = QCheckBox(field)
                    cb.setChecked(field in current)
                    self.checkboxes[field] = cb
                    page_layout.addWidget(cb)

            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setWidget(page)
            self.tabs.addTab(scroll, title)

        self.btn_all.clicked.connect(
            lambda: [cb.setChecked(True) for cb in self.checkboxes.values()]
        )
        self.btn_none.clicked.connect(
            lambda: [cb.setChecked(False) for cb in self.checkboxes.values()]
        )
        self.btn_min.clicked.connect(self.select_minimum)

        box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        box.accepted.connect(self.accept)
        box.rejected.connect(self.reject)
        layout.addWidget(box)

    def select_minimum(self):
        required = {"Core.ID", "Core.Label"}
        for field, cb in self.checkboxes.items():
            cb.setChecked(field in required)

    def accept(self):
        selected = [
            field
            for field, cb in self.checkboxes.items()
            if cb.isChecked()
        ]

        if "Core.ID" not in selected:
            selected.insert(0, "Core.ID")
        if "Core.Label" not in selected:
            selected.insert(1, "Core.Label")

        self.selected_columns = selected
        super().accept()
