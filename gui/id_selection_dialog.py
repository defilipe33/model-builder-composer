import re

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QTextEdit,
    QDialogButtonBox,
    QMessageBox,
)


class IdSelectionDialog(QDialog):
    def __init__(self, backend, element_type, parent=None):
        super().__init__(parent)
        self.backend = backend
        self.element_type = element_type
        self.setWindowTitle(f"Selecionar IDs — {element_type}")
        self.resize(520, 360)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "Cole IDs separados por espaço, vírgula, ponto e vírgula ou quebra de linha.\n"
            "Se houver qualquer texto inválido, nenhum ID será processado."
        ))

        self.text = QTextEdit()
        layout.addWidget(self.text, 1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.process)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def process(self):
        raw = self.text.toPlainText().strip()
        if not raw:
            QMessageBox.warning(self, "IDs", "Informe ao menos um ID.")
            return

        tokens = [x for x in re.split(r"[\s,;]+", raw) if x]
        invalid = [x for x in tokens if not x.isdigit()]

        if invalid:
            QMessageBox.warning(
                self,
                "IDs inválidos",
                "IDs inválidos:\n  "
                + "\n  ".join(invalid)
                + "\n\nOs demais IDs válidos não foram processados.",
            )
            return

        report = self.backend.select_ids(
            self.element_type,
            [int(x) for x in tokens],
        )

        lines = [
            f"Solicitados: {report['requested']}",
            f"Selecionados agora: {report['selected_now']}",
            f"Já selecionados: {report['already_selected']}",
            f"Não encontrados: {len(report['not_found'])}",
            f"Deletados: {len(report['deleted'])}",
        ]

        if report["not_found"]:
            lines += ["", "Não encontrados:"]
            lines += [f"  {x}" for x in report["not_found"]]

        if report["deleted"]:
            lines += ["", "Deletados:"]
            lines += [f"  {x}" for x in report["deleted"]]

        QMessageBox.information(self, "Resultado da seleção", "\n".join(lines))
        self.accept()
