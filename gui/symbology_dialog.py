from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QComboBox,
    QDialogButtonBox,
    QLabel,
    QPushButton,
    QScrollArea,
    QWidget,
    QCheckBox,
    QGroupBox,
)


SYMBOLS = [
    ("circle", "Círculo"),
    ("square", "Quadrado"),
    ("diamond", "Losango"),
    ("triangle", "Triângulo"),
    ("cross", "Cruz +"),
    ("x", "X"),
    ("star", "Estrela"),
]


class SymbologyDialog(QDialog):
    def __init__(self, available_types, settings, defaults, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Simbologia do mapa")
        self.resize(590, 720)

        self.available_types = [
            t for t in available_types if t != "Pipe"
        ]
        self.settings = {
            "mode": settings.get("mode", "by_type"),
            "all_point_symbol": settings.get("all_point_symbol", "circle"),
            "group_valves": bool(settings.get("group_valves", False)),
            "valve_symbol": settings.get("valve_symbol", "diamond"),
            "overrides": dict(settings.get("overrides", {})),
        }
        self.defaults = defaults

        root = QVBoxLayout(self)

        intro = QLabel(
            "A simbologia afeta apenas a visualização. "
            "Elementos selecionados continuam vermelhos."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        general = QGroupBox("Regras gerais")
        form = QFormLayout(general)

        self.mode = QComboBox()
        self.mode.addItem("Padrão por tipo", "by_type")
        self.mode.addItem(
            "Todos os elementos pontuais com o mesmo símbolo",
            "all_points",
        )

        idx = self.mode.findData(self.settings["mode"])
        if idx >= 0:
            self.mode.setCurrentIndex(idx)

        self.all_symbol = QComboBox()
        self._fill_symbols(self.all_symbol)
        self._set_combo_value(
            self.all_symbol, self.settings["all_point_symbol"]
        )

        self.group_valves = QCheckBox(
            "Usar um símbolo comum para válvulas"
        )
        self.group_valves.setChecked(self.settings["group_valves"])

        self.valve_symbol = QComboBox()
        self._fill_symbols(self.valve_symbol)
        self._set_combo_value(
            self.valve_symbol, self.settings["valve_symbol"]
        )

        form.addRow("Modo:", self.mode)
        form.addRow("Símbolo geral:", self.all_symbol)
        form.addRow(self.group_valves)
        form.addRow("Símbolo das válvulas:", self.valve_symbol)

        root.addWidget(general)

        note = QLabel(
            "Sobrescrições específicas têm prioridade sobre as regras gerais. "
            "Assim, você pode agrupar todas as válvulas e ainda deixar uma PRV "
            "com símbolo diferente."
        )
        note.setWordWrap(True)
        root.addWidget(note)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        container_layout = QFormLayout(container)

        self.type_combos = {}

        for element_type in self.available_types:
            combo = QComboBox()
            combo.addItem("Automático / regra geral", None)
            self._fill_symbols(combo)

            override = self.settings["overrides"].get(element_type)
            if override:
                self._set_combo_value(combo, override)

            self.type_combos[element_type] = combo
            container_layout.addRow(element_type, combo)

        scroll.setWidget(container)
        root.addWidget(scroll, 1)

        bottom = QHBoxLayout()
        self.reset_btn = QPushButton("Restaurar padrão")
        self.reset_btn.clicked.connect(self.restore_defaults)
        bottom.addWidget(self.reset_btn)
        bottom.addStretch(1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        bottom.addWidget(buttons)

        root.addLayout(bottom)

        self.mode.currentIndexChanged.connect(self._update_enabled)
        self.group_valves.toggled.connect(self._update_enabled)
        self._update_enabled()

    @staticmethod
    def _fill_symbols(combo):
        for key, label in SYMBOLS:
            combo.addItem(label, key)

    @staticmethod
    def _set_combo_value(combo, value):
        idx = combo.findData(value)
        if idx >= 0:
            combo.setCurrentIndex(idx)

    def _update_enabled(self):
        self.all_symbol.setEnabled(
            self.mode.currentData() == "all_points"
        )
        self.valve_symbol.setEnabled(self.group_valves.isChecked())

    def restore_defaults(self):
        self.mode.setCurrentIndex(
            self.mode.findData(self.defaults["mode"])
        )
        self._set_combo_value(
            self.all_symbol,
            self.defaults["all_point_symbol"],
        )
        self.group_valves.setChecked(
            self.defaults["group_valves"]
        )
        self._set_combo_value(
            self.valve_symbol,
            self.defaults["valve_symbol"],
        )

        for element_type, combo in self.type_combos.items():
            combo.setCurrentIndex(0)
            override = self.defaults.get("overrides", {}).get(element_type)
            if override:
                self._set_combo_value(combo, override)

        self._update_enabled()

    def values(self):
        overrides = {}

        for element_type, combo in self.type_combos.items():
            value = combo.currentData()
            if value:
                overrides[element_type] = value

        return {
            "mode": self.mode.currentData(),
            "all_point_symbol": self.all_symbol.currentData(),
            "group_valves": self.group_valves.isChecked(),
            "valve_symbol": self.valve_symbol.currentData(),
            "overrides": overrides,
        }
