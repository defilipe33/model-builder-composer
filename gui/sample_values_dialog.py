from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
)


class SampleValuesDialog(QDialog):
    def __init__(self, field, values, parent=None):
        super().__init__(parent)
        self.selected_value = None

        self.setWindowTitle(f"Valores — {field}")
        self.resize(720, 560)
        self.setMinimumSize(420, 320)

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                f"Valores encontrados para {field}.\n"
                "Duplo clique em um valor ou selecione e clique em Confirmar."
            )
        )

        self.list = QListWidget()
        self.list.setUniformItemSizes(True)
        self.list.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.list.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        for value in values:
            self.list.addItem(str(value))
        layout.addWidget(self.list, 1)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        self.confirm_btn = QPushButton("Confirmar")
        self.cancel_btn = QPushButton("Cancelar")
        buttons.addWidget(self.confirm_btn)
        buttons.addWidget(self.cancel_btn)
        layout.addLayout(buttons)

        self.confirm_btn.clicked.connect(self.confirm)
        self.cancel_btn.clicked.connect(self.reject)
        self.list.itemDoubleClicked.connect(
            lambda _: self.confirm()
        )

        if self.list.count():
            self.list.setCurrentRow(0)

    def confirm(self):
        item = self.list.currentItem()
        if item is None:
            return
        self.selected_value = item.text()
        self.accept()
