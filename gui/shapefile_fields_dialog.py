from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from modelbuilder.column_config import (
    suggested_shapefile_field_names,
    validate_shapefile_field_names,
)


class ShapefileFieldsDialog(QDialog):
    """Let the user choose concise, valid DBF field names per element type."""

    def __init__(self, column_config, element_types, parent=None):
        super().__init__(parent)
        self.column_config = column_config
        self.element_types = list(element_types)
        self.columns_by_type = {}
        self.inputs = {}

        self.setWindowTitle("Campos Shapefile")
        self.resize(800, 560)
        root = QVBoxLayout(self)

        note = QLabel(
            "Os campos abaixo são definidos em Colunas de exportação. "
            "Remova ou adicione campos lá para atualizar esta lista. Cada "
            "nome Shapefile aceita até 10 caracteres. Para campos com prefixo "
            "(Physical., Geometry., UDX., Initial. etc.), a sugestão usa os "
            "últimos 10 caracteres; nos demais, usa os primeiros 10."
        )
        note.setWordWrap(True)
        root.addWidget(note)

        top = QHBoxLayout()
        self.restore_btn = QPushButton("Restaurar sugestões")
        self.restore_btn.clicked.connect(self.restore_suggestions)
        top.addWidget(self.restore_btn)
        top.addStretch(1)
        root.addLayout(top)

        self.tabs = QTabWidget()
        root.addWidget(self.tabs, 1)
        for element_type in self.element_types:
            self._add_type_tab(element_type)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _add_type_tab(self, element_type):
        columns = self.column_config.get(element_type)
        self.columns_by_type[element_type] = columns
        names = self.column_config.shapefile_field_names(element_type, columns)

        table = QTableWidget(len(columns), 2)
        table.setHorizontalHeaderLabels(["Campo selecionado (nome completo)", "Nome no Shapefile"])
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)

        inputs = {}
        for row, column in enumerate(columns):
            full_name = QTableWidgetItem(column)
            full_name.setFlags(full_name.flags() & ~Qt.ItemFlag.ItemIsEditable)
            table.setItem(row, 0, full_name)
            edit = QLineEdit(names[column])
            edit.setMaxLength(10)
            edit.setMinimumWidth(145)
            edit.setToolTip("Máximo de 10 caracteres; letras, números e _. ")
            table.setCellWidget(row, 1, edit)
            inputs[column] = edit

        self.inputs[element_type] = inputs
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(table)
        self.tabs.addTab(page, element_type)

    def restore_suggestions(self):
        for element_type, columns in self.columns_by_type.items():
            suggestions = suggested_shapefile_field_names(columns)
            for column, value in suggestions.items():
                self.inputs[element_type][column].setText(value)

    def accept(self):
        values_by_type = {}
        for element_type, inputs in self.inputs.items():
            values = {column: edit.text().strip() for column, edit in inputs.items()}
            error = validate_shapefile_field_names(values)
            if error:
                QMessageBox.warning(self, "Campos Shapefile", error)
                return
            values_by_type[element_type] = values

        for element_type, values in values_by_type.items():
            self.column_config.set_shapefile_field_names(element_type, values)
        super().accept()
