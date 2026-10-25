import sys

try:
    from PySide6.QtWidgets import QApplication, QMessageBox
except ImportError as exc:
    print(
        "PySide6 não está instalado.\n"
        "Execute:\n"
        "  pip install -r requirements.txt\n"
        f"Detalhe: {exc}"
    )
    raise SystemExit(1)

from gui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Model Builder Composer (V3.9.15)")
    app.setOrganizationName("WaterGEMS Tool")
    app.setStyleSheet(
        """
        QTableWidget, QTableView {
            background-color: #343434;
            alternate-background-color: #444444;
            color: #f0f0f0;
            gridline-color: #555555;
            selection-background-color: #666666;
            selection-color: #ffffff;
        }
        QTableWidget::item, QTableView::item {
            background-color: #343434;
            color: #f0f0f0;
        }
        QTableWidget::item:alternate, QTableView::item:alternate {
            background-color: #444444;
        }
        QTableWidget::item:selected {
            background-color: #666666;
            color: #ffffff;
        }
        QHeaderView::section {
            background-color: #3e3e3e;
            color: #ffffff;
            border: 1px solid #222222;
            padding: 4px;
        }
        """
    )

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
