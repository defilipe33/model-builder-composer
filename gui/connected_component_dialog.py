from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)


class ConnectedComponentDialog(QDialog):
    """Configuration for an undirected, topology-only component traversal."""

    def __init__(self, available_types, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Selecionar componente conectado")
        self.resize(560, 620)

        root = QVBoxLayout(self)
        intro = QLabel(
            "A busca parte do SelectionSet atual e percorre as conexões "
            "Pipe ↔ nó em ambas as direções. Por padrão, atravessa todos os "
            "tipos e seleciona toda a rede conectada."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        type_group = QGroupBox("Tipos permitidos na travessia")
        type_layout = QVBoxLayout(type_group)
        type_hint = QLabel(
            "Desmarcar um tipo impede que ele seja incluído e que a busca "
            "continue através dele."
        )
        type_hint.setWordWrap(True)
        type_layout.addWidget(type_hint)

        quick = QHBoxLayout()
        all_btn = QPushButton("Todos")
        none_btn = QPushButton("Nenhum")
        quick.addWidget(all_btn)
        quick.addWidget(none_btn)
        quick.addStretch(1)
        type_layout.addLayout(quick)

        self.type_list = QListWidget()
        for element_type in available_types:
            item = QListWidgetItem(element_type)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            self.type_list.addItem(item)
        type_layout.addWidget(self.type_list, 1)
        root.addWidget(type_group, 1)

        self.boundary_group = QGroupBox("Elementos de fronteira (opcional)")
        boundary_layout = QVBoxLayout(self.boundary_group)
        boundary_hint = QLabel(
            "Os tipos marcados são incluídos na seleção, mas a busca não "
            "continua além deles. Deixe todos desmarcados para percorrer a "
            "rede completa."
        )
        boundary_hint.setWordWrap(True)
        boundary_layout.addWidget(boundary_hint)

        self.boundary_list = QListWidget()
        for element_type in available_types:
            if element_type == "Pipe":
                continue
            item = QListWidgetItem(element_type)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            self.boundary_list.addItem(item)
        boundary_layout.addWidget(self.boundary_list, 1)
        root.addWidget(self.boundary_group, 1)

        self.include_boundary = QCheckBox(
            "Incluir elementos de fronteira no SelectionSet"
        )
        self.include_boundary.setChecked(True)
        root.addWidget(self.include_boundary)

        self.inactive_as_boundary = QCheckBox(
            "Não incluir elementos inativos; tratá-los como extremidades"
        )
        self.inactive_as_boundary.setChecked(False)
        self.inactive_as_boundary.setToolTip(
            "Quando a busca encontra um elemento explicitamente inativo, "
            "ela não o adiciona ao SelectionSet e não continua além dele."
        )
        root.addWidget(self.inactive_as_boundary)

        note = QLabel(
            "A ferramenta usa somente a topologia StartNode / StopNode; "
            "não usa sentido de fluxo hidráulico. Limites de 50.000 novos "
            "elementos e 100.000 visitados protegem a aplicação."
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

        all_btn.clicked.connect(lambda: self._set_allowed(True))
        none_btn.clicked.connect(lambda: self._set_allowed(False))

    def _set_allowed(self, checked):
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        for index in range(self.type_list.count()):
            self.type_list.item(index).setCheckState(state)

    @staticmethod
    def _checked_items(widget):
        return [
            widget.item(index).text()
            for index in range(widget.count())
            if widget.item(index).checkState() == Qt.CheckState.Checked
        ]

    def values(self):
        return {
            "allowed_types": self._checked_items(self.type_list),
            "stop_types": self._checked_items(self.boundary_list),
            "include_stop": self.include_boundary.isChecked(),
            "inactive_as_boundary": self.inactive_as_boundary.isChecked(),
        }

    def accept(self):
        if not self._checked_items(self.type_list):
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(
                self,
                "Componente conectado",
                "Marque ao menos um tipo permitido na travessia.",
            )
            return
        super().accept()
