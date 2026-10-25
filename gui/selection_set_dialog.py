from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QPushButton,
    QMessageBox,
)


class WaterGemsSelectionSetDialog(QDialog):
    def __init__(self, backend, parent=None):
        super().__init__(parent)
        self.backend = backend

        self.setWindowTitle("Selection Sets do WaterGEMS")
        self.resize(760, 520)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(
            "A lista abaixo carrega apenas metadados. "
            "Os membros são lidos somente quando você usar um Selection Set."
        ))

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(
            ["Nome", "ID", "Elementos", "Nome resolvido"]
        )
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self.table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        self.table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents
        )
        self.table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.ResizeToContents
        )
        layout.addWidget(self.table, 1)

        buttons = QHBoxLayout()
        self.add_btn = QPushButton("Adicionar à seleção atual")
        self.replace_btn = QPushButton("Substituir seleção atual")
        self.close_btn = QPushButton("Fechar")

        buttons.addWidget(self.add_btn)
        buttons.addWidget(self.replace_btn)
        buttons.addStretch(1)
        buttons.addWidget(self.close_btn)
        layout.addLayout(buttons)

        self.add_btn.clicked.connect(lambda: self.load_selected("add"))
        self.replace_btn.clicked.connect(lambda: self.load_selected("replace"))
        self.close_btn.clicked.connect(self.accept)

        self.populate()

    def populate(self):
        sets = self.backend.watergems_selection_sets()
        self.table.setRowCount(len(sets))

        for row_idx, item in enumerate(sets):
            name = QTableWidgetItem(item["name"])
            name.setData(Qt.ItemDataRole.UserRole, item["id"])
            self.table.setItem(row_idx, 0, name)
            self.table.setItem(row_idx, 1, QTableWidgetItem(str(item["id"])))
            self.table.setItem(row_idx, 2, QTableWidgetItem(str(item["count"])))
            self.table.setItem(
                row_idx,
                3,
                QTableWidgetItem("Sim" if item["name_resolved"] else "Não"),
            )

        if not sets:
            self.add_btn.setEnabled(False)
            self.replace_btn.setEnabled(False)

    def selected_id(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def load_selected(self, mode):
        selection_set_id = self.selected_id()
        if selection_set_id is None:
            QMessageBox.warning(
                self, "Selection Set", "Selecione um Selection Set."
            )
            return

        if mode == "replace":
            answer = QMessageBox.question(
                self,
                "Substituir seleção",
                "A seleção atual será apagada e substituída pelo Selection Set "
                "do WaterGEMS. Deseja continuar?",
            )
            if answer != QMessageBox.StandardButton.Yes:
                return

        try:
            window = self.window()
            if hasattr(window, "busy"):
                with window.busy(
                    "Carregando Selection Set do WaterGEMS..."
                ):
                    report = self.backend.load_watergems_selection_set(
                        selection_set_id, mode=mode
                    )
            else:
                report = self.backend.load_watergems_selection_set(
                    selection_set_id, mode=mode
                )
        except Exception as exc:
            QMessageBox.critical(self, "Erro", str(exc))
            return

        lines = [
            f"Adicionados: {report['added']}",
            f"Já estavam selecionados (mantidos uma única vez): "
            f"{report['already_selected']}",
        ]

        if report["grouped_counts"]:
            lines.append("")
            lines.append("Por tipo:")
            for element_type, count in report["grouped_counts"].items():
                lines.append(f"  {element_type}: {count}")

        if report["unsupported"]:
            lines.append("")
            lines.append(
                f"IDs vivos de tipos ainda não suportados: "
                f"{len(report['unsupported'])}"
            )

        QMessageBox.information(
            self, "Selection Set carregado", "\n".join(lines)
        )
        self.accept()
