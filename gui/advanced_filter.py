from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QPlainTextEdit,
    QMessageBox,
    QSplitter,
    QSizePolicy,
)

from gui.sample_values_dialog import SampleValuesDialog


class AdvancedFilterWidget(QWidget):
    applyRequested = Signal(str)
    clearRequested = Signal()

    def __init__(self, backend, parent=None):
        super().__init__(parent)
        self.backend = backend
        self.element_type = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        self.split = QSplitter(Qt.Orientation.Horizontal)
        self.split.setChildrenCollapsible(False)
        self.split.setHandleWidth(9)
        self.split.setOpaqueResize(True)

        # ----- fields -----
        left = QWidget()
        left.setMinimumWidth(150)
        left.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.addWidget(QLabel("Campos (duplo clique adiciona):"))

        self.fields = QListWidget()
        self.fields.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.fields.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        ll.addWidget(self.fields, 1)

        sample_buttons = QGridLayout()
        self.partial_btn = QPushButton("Amostra parcial")
        self.all_btn = QPushButton("Valores únicos (todos)")
        sample_buttons.addWidget(self.partial_btn, 0, 0)
        sample_buttons.addWidget(self.all_btn, 1, 0)
        ll.addLayout(sample_buttons)

        # ----- expression editor -----
        right = QWidget()
        right.setMinimumWidth(300)
        right.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.addWidget(QLabel("Expressão:"))

        self.editor = QPlainTextEdit()
        self.editor.setMinimumWidth(280)
        self.editor.setMinimumHeight(120)
        self.editor.setPlaceholderText(
            "[Physical.Setor] = 'NORTE%' AND [Core.IsActive] = true"
        )
        rl.addWidget(self.editor, 1)

        # Fixed two-row grid: labels never get clipped by a single long row.
        ops = QGridLayout()
        tokens = [
            "=", "!=", ">", ">=", "<",
            "<=", "AND", "OR", "(", ")",
        ]
        for i, token in enumerate(tokens):
            row = i // 5
            col = i % 5
            btn = QPushButton(token)
            btn.setMinimumWidth(46)
            btn.clicked.connect(
                lambda _, t=token: self.insert_token(t)
            )
            ops.addWidget(btn, row, col)
        rl.addLayout(ops)

        actions = QHBoxLayout()
        self.apply_btn = QPushButton("Aplicar")
        self.clear_btn = QPushButton("Limpar")
        actions.addWidget(self.apply_btn)
        actions.addWidget(self.clear_btn)
        rl.addLayout(actions)

        self.split.addWidget(left)
        self.split.addWidget(right)
        self.split.setCollapsible(0, False)
        self.split.setCollapsible(1, False)
        self.split.setStretchFactor(0, 1)
        self.split.setStretchFactor(1, 1)

        # Only initial proportion. Users remain free to resize afterwards.
        self.split.setSizes([260, 430])

        root.addWidget(self.split)

        self.fields.itemDoubleClicked.connect(
            lambda item: self.insert_token(f"[{item.text()}]")
        )
        self.partial_btn.clicked.connect(
            lambda: self.show_samples(False)
        )
        self.all_btn.clicked.connect(
            lambda: self.show_samples(True)
        )
        self.apply_btn.clicked.connect(
            lambda: self.applyRequested.emit(
                self.editor.toPlainText()
            )
        )
        self.clear_btn.clicked.connect(self.clear_editor)


    def set_context(self, element_type, groups):
        self.element_type = element_type
        self.fields.clear()
        for group in ("core", "physical", "udx", "initial"):
            for field in groups.get(group, []):
                self.fields.addItem(field)

    def insert_token(self, token):
        cursor = self.editor.textCursor()
        if token in {"AND", "OR"}:
            token = f" {token} "
        elif token in {"=", "!=", ">", ">=", "<", "<="}:
            token = f" {token} "
        cursor.insertText(token)
        self.editor.setTextCursor(cursor)
        self.editor.setFocus()

    def clear_editor(self):
        self.editor.clear()
        self.clearRequested.emit()

    def show_samples(self, scan_all):
        item = self.fields.currentItem()
        if item is None:
            QMessageBox.warning(
                self, "Amostras", "Selecione uma coluna."
            )
            return

        field = item.text()

        if scan_all:
            answer = QMessageBox.question(
                self,
                "Valores únicos",
                "Examinar todos os elementos pode demorar. Continuar?",
            )
            if answer != QMessageBox.StandardButton.Yes:
                return

        try:
            window = self.window()
            if hasattr(window, "busy"):
                with window.busy(
                    "Lendo valores da coluna..."
                ):
                    values = self.backend.sample_values(
                        self.element_type,
                        field,
                        250 if not scan_all else 5000,
                        scan_all,
                    )
            else:
                values = self.backend.sample_values(
                    self.element_type,
                    field,
                    250 if not scan_all else 5000,
                    scan_all,
                )
        except Exception as exc:
            QMessageBox.critical(self, "Erro", str(exc))
            return

        if not values:
            QMessageBox.information(
                self, "Amostras", "Nenhum valor encontrado."
            )
            return

        dlg = SampleValuesDialog(
            self.backend.display_field_name(field), values, self
        )
        if dlg.exec() and dlg.selected_value is not None:
            value = dlg.selected_value.replace("'", "''")
            self.insert_token(f"'{value}'")
