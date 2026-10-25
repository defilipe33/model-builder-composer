from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QListWidget, QVBoxLayout


class IslandInspectorDialog(QDialog):
    def __init__(self, report, parent=None):
        super().__init__(parent)
        self.report = report
        self.setWindowTitle("Inspector de ilhas")
        self.resize(660, 460)
        root = QVBoxLayout(self)
        root.addWidget(QLabel("Selecione uma componente para substituí-la no SelectionSet e visualizá-la no mapa."))
        self.list = QListWidget()
        for index, component in enumerate(report["components"], start=1):
            name = "Componente principal" if index == 1 else f"Ilha {index}"
            composition = ", ".join(f"{t}: {n}" for t, n in component["counts"].items())
            self.list.addItem(f"{name} — {component['size']} elementos ({composition})")
        self.list.setCurrentRow(0)
        root.addWidget(self.list, 1)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        self.select_btn = buttons.addButton("Selecionar e visualizar", QDialogButtonBox.ButtonRole.AcceptRole)
        self.select_btn.clicked.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def selected_pairs(self):
        row = self.list.currentRow()
        if row < 0:
            return []
        return list(self.report["components"][row].get("pairs", []))
