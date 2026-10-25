from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QPushButton,
    QTabWidget,
    QWidget,
    QScrollArea,
    QCheckBox,
    QDialogButtonBox,
)


GROUPS = [
    ("core", "Core"),
    ("physical", "Physical"),
    ("udx", "User Data Extensions"),
    ("initial", "Initial Settings"),
]


class ColumnConfigDialog(QDialog):
    def __init__(self, backend, initial_type=None, parent=None):
        super().__init__(parent)
        self.backend = backend
        self.checkboxes = {}
        self.setWindowTitle("Colunas para ModelBuilder")
        self.resize(720, 620)

        root = QVBoxLayout(self)

        header = QHBoxLayout()
        header.addWidget(QLabel("Tipo de elemento:"))
        self.type_combo = QComboBox()
        for element_type, _ in backend.available_types():
            self.type_combo.addItem(element_type)
        header.addWidget(self.type_combo, 1)

        self.btn_all = QPushButton("Selecionar tudo")
        self.btn_none = QPushButton("Limpar")
        self.btn_core = QPushButton("Somente Core")
        header.addWidget(self.btn_all)
        header.addWidget(self.btn_none)
        header.addWidget(self.btn_core)
        root.addLayout(header)

        self.tabs = QTabWidget()
        root.addWidget(self.tabs, 1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        self.type_combo.currentTextChanged.connect(self.rebuild)
        self.btn_all.clicked.connect(self.select_all)
        self.btn_none.clicked.connect(self.select_none)
        self.btn_core.clicked.connect(self.select_core)

        if initial_type:
            idx = self.type_combo.findText(initial_type)
            if idx >= 0:
                self.type_combo.setCurrentIndex(idx)

        self.rebuild(self.type_combo.currentText())

    def rebuild(self, element_type):
        self.tabs.clear()
        self.checkboxes.clear()

        current = set(self.backend.column_config.get(element_type))
        groups = self.backend.column_config.groups(element_type)

        for group_key, title in GROUPS:
            page = QWidget()
            page_layout = QVBoxLayout(page)
            page_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

            fields = groups.get(group_key, [])
            if not fields:
                page_layout.addWidget(QLabel("Nenhum campo encontrado neste modelo."))
            else:
                for column in fields:
                    cb = QCheckBox(column)
                    cb.setChecked(column in current)
                    self.checkboxes[column] = cb
                    page_layout.addWidget(cb)

            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setWidget(page)
            self.tabs.addTab(scroll, title)

    def select_all(self):
        for cb in self.checkboxes.values():
            cb.setChecked(True)

    def select_none(self):
        for cb in self.checkboxes.values():
            cb.setChecked(False)

    def select_core(self):
        element_type = self.type_combo.currentText()
        core = set(self.backend.column_config.groups(element_type).get("core", []))
        for column, cb in self.checkboxes.items():
            cb.setChecked(column in core)

    def accept(self):
        element_type = self.type_combo.currentText()
        selected = [
            column
            for column, cb in self.checkboxes.items()
            if cb.isChecked()
        ]
        self.backend.column_config.set(element_type, selected)
        super().accept()
