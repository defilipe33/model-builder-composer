from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QSpinBox,
    QComboBox,
    QCheckBox,
    QDialogButtonBox,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QGroupBox,
)


class TopologyStopDialog(QDialog):
    def __init__(
        self,
        available_types,
        parent=None,
        default_direction="upstream",
    ):
        super().__init__(parent)

        self.setWindowTitle("Expansão topológica com parada")
        self.resize(540, 620)

        root = QVBoxLayout(self)

        intro = QLabel(
            "Expanda o SelectionSet pela topologia até encontrar um dos "
            "tipos marcados abaixo. Quando um tipo de parada é encontrado, "
            "aquela ramificação não continua além dele."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        form = QFormLayout()

        self.direction = QComboBox()
        self.direction.addItem("Conectados — ambas as direções", "both")
        self.direction.addItem("Upstream topológico", "upstream")
        self.direction.addItem("Downstream topológico", "downstream")

        idx = self.direction.findData(default_direction)
        if idx >= 0:
            self.direction.setCurrentIndex(idx)

        self.levels = QSpinBox()
        self.levels.setRange(1, 500)
        self.levels.setValue(100)
        self.levels.setToolTip(
            "Limite máximo de passos topológicos. "
            "A expansão também para quando encontra os tipos selecionados."
        )

        form.addRow("Direção:", self.direction)
        form.addRow("Máximo de níveis:", self.levels)
        root.addLayout(form)

        group = QGroupBox("Tipos que interrompem a expansão")
        group_layout = QVBoxLayout(group)

        quick = QHBoxLayout()
        self.btn_reservoir_tank = QPushButton("Reservoir + Tank")
        self.btn_valves = QPushButton("Válvulas")
        self.btn_pumps = QPushButton("Pumps")
        self.btn_clear = QPushButton("Limpar")

        quick.addWidget(self.btn_reservoir_tank)
        quick.addWidget(self.btn_valves)
        quick.addWidget(self.btn_pumps)
        quick.addWidget(self.btn_clear)
        group_layout.addLayout(quick)

        self.type_list = QListWidget()
        for element_type in available_types:
            if element_type == "Pipe":
                continue
            item = QListWidgetItem(element_type)
            item.setFlags(
                item.flags() | Qt.ItemFlag.ItemIsUserCheckable
            )
            item.setCheckState(Qt.CheckState.Unchecked)
            self.type_list.addItem(item)

        group_layout.addWidget(self.type_list, 1)
        root.addWidget(group, 1)

        self.include_stop = QCheckBox(
            "Incluir o elemento de parada no SelectionSet"
        )
        self.include_stop.setChecked(True)

        self.stop_on_first = QCheckBox(
            "Encerrar toda a expansão ao encontrar o primeiro elemento de parada"
        )
        self.stop_on_first.setChecked(False)
        self.stop_on_first.setToolTip(
            "Desmarcado: cada ramificação para individualmente, enquanto "
            "as demais continuam."
        )

        root.addWidget(self.include_stop)
        root.addWidget(self.stop_on_first)

        note = QLabel(
            "Upstream/Downstream continuam sendo definidos apenas pela "
            "orientação topológica StartNode → Pipe → StopNode; "
            "não são usados resultados hidráulicos."
        )
        note.setWordWrap(True)
        root.addWidget(note)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        self.btn_reservoir_tank.clicked.connect(
            lambda: self._check_named({
                "Reservoir",
                "Tank",
                "Conventional Tank",
            })
        )
        self.btn_valves.clicked.connect(
            lambda: self._check_named({
                "TCV",
                "FCV",
                "PRV",
                "PBV",
                "Check Valve",
                "Air Valve",
            })
        )
        self.btn_pumps.clicked.connect(
            lambda: self._check_named({
                "Standard Pump",
                "Variable Speed Pump Battery",
            })
        )
        self.btn_clear.clicked.connect(self._clear_checks)

    def _check_named(self, names):
        for i in range(self.type_list.count()):
            item = self.type_list.item(i)
            if item.text() in names:
                item.setCheckState(Qt.CheckState.Checked)

    def _clear_checks(self):
        for i in range(self.type_list.count()):
            self.type_list.item(i).setCheckState(
                Qt.CheckState.Unchecked
            )

    def selected_stop_types(self):
        values = []
        for i in range(self.type_list.count()):
            item = self.type_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                values.append(item.text())
        return values

    def values(self):
        return {
            "levels": self.levels.value(),
            "direction": self.direction.currentData(),
            "stop_types": self.selected_stop_types(),
            "include_stop": self.include_stop.isChecked(),
            "stop_on_first": self.stop_on_first.isChecked(),
        }

    def accept(self):
        if not self.selected_stop_types():
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(
                self,
                "Critério de parada",
                "Marque pelo menos um tipo de elemento para interromper "
                "a expansão.",
            )
            return

        super().accept()
