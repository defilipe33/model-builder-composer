from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QListWidget, QVBoxLayout


class NetworkDiagnosticsDialog(QDialog):
    def __init__(self, diagnostics, parent=None):
        super().__init__(parent)
        self.diagnostics = diagnostics
        self.setWindowTitle("Diagnóstico de qualidade da rede")
        self.resize(580, 420)
        root = QVBoxLayout(self)
        root.addWidget(QLabel("Selecione uma verificação para adicionar seus itens ao SelectionSet."))
        self.list = QListWidget()
        for name, pairs in diagnostics.items():
            self.list.addItem(f"{name} — {len(pairs)} item(ns)")
        self.list.setCurrentRow(0)
        root.addWidget(self.list, 1)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        self.select_btn = buttons.addButton("Selecionar itens", QDialogButtonBox.ButtonRole.AcceptRole)
        self.select_btn.clicked.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def selected_pairs(self):
        names = list(self.diagnostics)
        row = self.list.currentRow()
        return [] if row < 0 else list(self.diagnostics[names[row]])
