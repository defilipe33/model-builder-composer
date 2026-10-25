from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QFormLayout,
    QSpinBox,
    QComboBox,
    QDialogButtonBox,
    QLabel,
)


class TopologyExpansionDialog(QDialog):
    def __init__(self, parent=None, default_direction="both"):
        super().__init__(parent)

        self.setWindowTitle("Expansão topológica")
        self.resize(430, 240)

        layout = QVBoxLayout(self)

        layout.addWidget(
            QLabel(
                "A expansão parte de todos os elementos atualmente no "
                "SelectionSet e acrescenta os elementos encontrados."
            )
        )

        form = QFormLayout()

        self.levels = QSpinBox()
        self.levels.setRange(1, 100)
        self.levels.setValue(3)

        self.direction = QComboBox()
        self.direction.addItem("Conectados (ambas as direções)", "both")
        self.direction.addItem("Upstream", "upstream")
        self.direction.addItem("Downstream", "downstream")

        index = self.direction.findData(default_direction)
        if index >= 0:
            self.direction.setCurrentIndex(index)

        form.addRow("Níveis:", self.levels)
        form.addRow("Direção:", self.direction)

        layout.addLayout(form)

        layout.addWidget(
            QLabel(
                "Um nível corresponde a um passo no grafo: Pipe ↔ nó. "
                "Por isso, dois níveis normalmente atravessam um Pipe e "
                "chegam ao próximo Pipe/nó."
            )
        )

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def values(self):
        return self.levels.value(), self.direction.currentData()
