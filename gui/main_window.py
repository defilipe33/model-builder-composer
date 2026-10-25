from pathlib import Path
from contextlib import contextmanager

from PySide6.QtCore import Qt, QSignalBlocker, QEvent
from PySide6.QtGui import QKeySequence, QShortcut, QGuiApplication, QAction
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFileDialog,
    QComboBox,
    QListWidget,
    QListWidgetItem,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QSpinBox,
    QMessageBox,
    QGroupBox,
    QPlainTextEdit,
    QCheckBox,
    QSplitter,
    QToolBar,
    QProgressBar,
    QApplication,
    QSizePolicy,
    QStackedWidget,
    QFrame,
    QToolButton,
    QMenu,
)

from gui.backend import AppBackend
from gui.column_dialog import ColumnConfigDialog
from gui.id_selection_dialog import IdSelectionDialog
from gui.table_columns_dialog import TableColumnsDialog
from gui.shapefile_fields_dialog import ShapefileFieldsDialog
from gui.filter_models import FilterDefinition
from gui.selection_set_dialog import WaterGemsSelectionSetDialog
from gui.advanced_filter import AdvancedFilterWidget
from gui.map_view import NetworkMapWidget
from gui.topology_dialog import TopologyExpansionDialog
from gui.topology_stop_dialog import TopologyStopDialog
from gui.connected_component_dialog import ConnectedComponentDialog
from gui.network_diagnostics_dialog import NetworkDiagnosticsDialog
from gui.island_inspector_dialog import IslandInspectorDialog
from gui.symbology_dialog import SymbologyDialog


OPERATORS = [
    ("=", "eq"),
    ("≠", "ne"),
    ("contém", "contains"),
    ("começa com", "startswith"),
    ("termina com", "endswith"),
    (">", "gt"),
    ("≥", "gte"),
    ("<", "lt"),
    ("≤", "lte"),
]


class MainWindow(QMainWindow):
    PAGE_SIZE = 200

    def __init__(self):
        super().__init__()

        self.backend = AppBackend()
        self.current_type = None
        self.current_offset = 0
        self.current_ids = []
        self.current_rows = []
        self.active_filter = None
        self.active_expression = ""
        self.table_columns_by_type = {}
        self.table_selected_only = False
        self.last_component_diagnosis = None
        self.last_network_diagnostics = None

        self.setWindowTitle("Model Builder Composer (V3.9.15)")

        self.build_ui()
        self.build_toolbar()
        self.build_status_progress()
        self.setup_shortcuts()
        self.apply_initial_geometry()
        self.set_model_enabled(False)
        self.statusBar().showMessage("Selecione um arquivo .wtg.sqlite.")

    # ---------------------------------------------------------
    # UI
    # ---------------------------------------------------------
    def apply_initial_geometry(self):
        """
        Start smaller than the monitor and centered. The user can maximize
        normally afterwards. Never force a fixed desktop resolution.
        """
        screen = self.screen() or QGuiApplication.primaryScreen()
        if screen is None:
            self.resize(1280, 760)
            return

        area = screen.availableGeometry()

        # 78% x 78%, capped at 1600x900 and with reasonable minimums.
        width = min(1600, max(980, int(area.width() * 0.78)))
        height = min(900, max(650, int(area.height() * 0.78)))

        # Never exceed the actual available work area.
        width = min(width, area.width())
        height = min(height, area.height())

        self.resize(width, height)
        frame = self.frameGeometry()
        frame.moveCenter(area.center())
        self.move(frame.topLeft())

    def build_ui(self):
        self.setMinimumSize(1240, 700)
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        top = QGridLayout()

        self.path_edit = QLineEdit()
        self.path_edit.setReadOnly(True)
        self.open_btn = QPushButton("Abrir .wtg.sqlite")

        self.scenario_combo = QComboBox()
        self.activate_btn = QPushButton("Carregar cenário")

        top.addWidget(QLabel("Modelo:"), 0, 0)
        top.addWidget(self.path_edit, 0, 1)
        top.addWidget(self.open_btn, 0, 2)

        top.addWidget(QLabel("Cenário:"), 1, 0)
        top.addWidget(self.scenario_combo, 1, 1)
        top.addWidget(self.activate_btn, 1, 2)

        root.addLayout(top)

        body = QSplitter(Qt.Orientation.Horizontal)
        body.setChildrenCollapsible(False)
        body.setHandleWidth(9)
        body.setOpaqueResize(True)
        root.addWidget(body, 1)

        # ---------- left ----------
        left_box = QGroupBox("Tipos e filtros")
        left_box.setMinimumWidth(470)
        left_layout = QVBoxLayout(left_box)

        self.type_list = QListWidget()
        left_layout.addWidget(self.type_list, 1)

        self.advanced_filter = AdvancedFilterWidget(self.backend)
        left_layout.addWidget(self.advanced_filter, 2)
        filter_separator = QFrame()
        filter_separator.setFrameShape(QFrame.Shape.HLine)
        filter_separator.setFrameShadow(QFrame.Shadow.Sunken)
        left_layout.addWidget(filter_separator)

        self.id_select_btn = QPushButton("Selecionar por IDs")
        self.wg_sets_btn = QPushButton("Selection Sets do WaterGEMS...")
        self.columns_btn = QPushButton("Colunas de exportação...")
        self.table_columns_btn = QPushButton("Colunas da tabela...")

        left_layout.addWidget(self.id_select_btn)
        left_layout.addWidget(self.wg_sets_btn)
        left_layout.addWidget(self.table_columns_btn)
        left_layout.addWidget(self.columns_btn)

        body.addWidget(left_box)

        # ---------- center ----------
        center_box = QGroupBox("Elementos")
        center_box.setMinimumWidth(520)
        center_layout = QVBoxLayout(center_box)

        nav = QHBoxLayout()

        self.prev_btn = QPushButton("◀ Anterior")
        self.next_btn = QPushButton("Próxima ▶")

        self.page_label = QLabel("0–0")
        self.result_label = QLabel("0 resultados")
        self.table_selected_only_cb = QCheckBox(
            "Mostrar apenas selecionados"
        )
        self.table_selected_only_cb.toggled.connect(
            self.table_selected_only_changed
        )

        self.page_size = QSpinBox()
        self.page_size.setRange(20, 1000)
        self.page_size.setValue(self.PAGE_SIZE)
        self.page_size.setSingleStep(20)

        nav.addWidget(self.prev_btn)
        nav.addWidget(self.next_btn)
        nav.addWidget(self.page_label)
        nav.addWidget(self.result_label)
        nav.addWidget(self.table_selected_only_cb)
        nav.addStretch(1)
        nav.addWidget(QLabel("Itens/página:"))
        nav.addWidget(self.page_size)

        center_layout.addLayout(nav)

        bulk = QGridLayout()
        self.mark_visual_btn = QPushButton("Marcar seleção visual")
        self.unmark_visual_btn = QPushButton("Desmarcar seleção visual")
        self.select_page_btn = QPushButton("Marcar página")
        self.deselect_page_btn = QPushButton("Desmarcar página")
        self.select_results_btn = QPushButton("Marcar resultados do filtro")
        self.deselect_results_btn = QPushButton("Desmarcar resultados do filtro")

        # Each operation and its inverse are stacked vertically.
        bulk.addWidget(self.mark_visual_btn, 0, 0)
        bulk.addWidget(self.unmark_visual_btn, 1, 0)

        bulk.addWidget(self.select_page_btn, 0, 1)
        bulk.addWidget(self.deselect_page_btn, 1, 1)

        bulk.addWidget(self.select_results_btn, 0, 2)
        bulk.addWidget(self.deselect_results_btn, 1, 2)

        bulk.setColumnStretch(0, 1)
        bulk.setColumnStretch(1, 1)
        bulk.setColumnStretch(2, 1)

        center_layout.addLayout(bulk)

        self.table = QTableWidget()
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.installEventFilter(self)

        self.map_widget = NetworkMapWidget()
        self.center_stack = QStackedWidget()
        self.center_stack.addWidget(self.table)
        self.center_stack.addWidget(self.map_widget)
        center_layout.addWidget(self.center_stack, 1)

        body.addWidget(center_box)

        # ---------- right ----------
        right_box = QGroupBox("SelectionSet")
        right_box.setMinimumWidth(170)
        right_layout = QVBoxLayout(right_box)

        self.summary = QPlainTextEdit()
        self.summary.setReadOnly(True)
        right_layout.addWidget(self.summary, 1)

        self.dependencies_btn = QPushButton("Adicionar dependências dos Pipes")
        self.associated_meters_btn = QPushButton(
            "Selecionar Customer Meters associados"
        )
        self.clear_btn = QPushButton("Limpar SelectionSet")
        self.export_btn = QPushButton("Exportar ModelBuilder...")
        self.shapefile_fields_btn = QPushButton("Campos Shapefile...")
        self.export_gis_btn = QPushButton("Exportar camadas GIS...")

        right_layout.addWidget(self.dependencies_btn)
        right_layout.addWidget(self.associated_meters_btn)
        right_layout.addWidget(self.clear_btn)
        right_layout.addWidget(self.export_btn)
        right_layout.addWidget(self.shapefile_fields_btn)
        right_layout.addWidget(self.export_gis_btn)

        body.addWidget(right_box)
        body.setCollapsible(0, False)
        body.setCollapsible(1, False)
        body.setCollapsible(2, False)
        body.setStretchFactor(0, 2)
        body.setStretchFactor(1, 3)
        body.setStretchFactor(2, 1)
        body.setSizes([470, 720, 190])

        # connections
        self.open_btn.clicked.connect(self.open_model)
        self.activate_btn.clicked.connect(self.activate_scenario)

        self.type_list.currentItemChanged.connect(self.type_changed)

        self.prev_btn.clicked.connect(self.previous_page)
        self.next_btn.clicked.connect(self.next_page)
        self.page_size.valueChanged.connect(self.reload_first_page)

        self.table.itemChanged.connect(self.table_item_changed)

        self.id_select_btn.clicked.connect(self.select_ids_dialog)
        self.advanced_filter.applyRequested.connect(self.apply_expression_filter)
        self.advanced_filter.clearRequested.connect(self.clear_expression_filter)
        self.wg_sets_btn.clicked.connect(self.watergems_selection_sets_dialog)
        self.columns_btn.clicked.connect(self.columns_dialog)
        self.table_columns_btn.clicked.connect(self.table_columns_dialog)


        self.mark_visual_btn.clicked.connect(lambda: self.set_visual_checks(True))
        self.unmark_visual_btn.clicked.connect(lambda: self.set_visual_checks(False))
        self.select_page_btn.clicked.connect(self.select_page)
        self.deselect_page_btn.clicked.connect(self.deselect_page)
        self.select_results_btn.clicked.connect(self.select_all_results)
        self.deselect_results_btn.clicked.connect(self.deselect_all_results)

        self.dependencies_btn.clicked.connect(self.add_dependencies)
        self.associated_meters_btn.clicked.connect(self.add_associated_customer_meters)
        self.clear_btn.clicked.connect(self.clear_selection)
        self.export_btn.clicked.connect(self.export_model)
        self.shapefile_fields_btn.clicked.connect(self.shapefile_fields_dialog)
        self.export_gis_btn.clicked.connect(self.export_gis_layers)
        self.map_widget.refreshRequested.connect(self.refresh_map)
        self.map_widget.elementClicked.connect(self.map_element_clicked)
        self.map_widget.spatialSelection.connect(self.map_spatial_selection)
        self.map_widget.ensureSelectionVisibleRequested.connect(
            self.ensure_selected_elements_in_map
        )

        # Route the visible map-panel button through the same robust path as
        # Toolbar > Mapa > Zoom Selection.
        try:
            self.map_widget.zoom_selection_btn.clicked.disconnect()
        except Exception:
            pass
        self.map_widget.zoom_selection_btn.clicked.connect(
            self.zoom_to_selection
        )

    def build_toolbar(self):
        toolbar = QToolBar("Ferramentas", self)
        toolbar.setObjectName("MainTools")
        toolbar.setMovable(True)
        toolbar.setFloatable(False)
        self.addToolBar(toolbar)

        self.action_open = QAction("Abrir", self)
        self.action_open.triggered.connect(self.open_model)
        toolbar.addAction(self.action_open)

        self.action_sets = QAction("Selection Sets", self)
        self.action_sets.triggered.connect(
            self.watergems_selection_sets_dialog
        )
        toolbar.addAction(self.action_sets)

        self.action_table_columns = QAction("Colunas tabela", self)
        self.action_table_columns.triggered.connect(
            self.table_columns_dialog
        )
        toolbar.addAction(self.action_table_columns)

        self.action_export_columns = QAction("Colunas exportação", self)
        self.action_export_columns.triggered.connect(
            self.columns_dialog
        )
        toolbar.addAction(self.action_export_columns)

        self.action_shapefile_fields = QAction("Campos Shapefile", self)
        self.action_shapefile_fields.triggered.connect(self.shapefile_fields_dialog)
        toolbar.addAction(self.action_shapefile_fields)

        self.action_write_column_profile = QAction("Gerar perfil TXT", self)
        self.action_write_column_profile.triggered.connect(
            self.write_column_profile
        )
        toolbar.addAction(self.action_write_column_profile)

        self.action_load_column_profile = QAction("Importar perfil TXT", self)
        self.action_load_column_profile.triggered.connect(
            self.load_column_profile
        )
        toolbar.addAction(self.action_load_column_profile)

        toolbar.addSeparator()
        toolbar.addWidget(QLabel(" Unidades: "))

        self.units_combo = QComboBox()
        self.units_combo.addItem("SI (m / mm)", "SI")
        self.units_combo.addItem("Americano (ft / in)", "US")
        self.units_combo.setCurrentIndex(0)
        self.units_combo.setMinimumWidth(145)
        self.units_combo.currentIndexChanged.connect(
            self.unit_system_changed
        )
        toolbar.addWidget(self.units_combo)

        toolbar.addSeparator()

        self.action_undo = QAction("Desfazer", self)
        self.action_undo.setShortcut(QKeySequence("Ctrl+Z"))
        self.action_undo.setToolTip("Desfazer última alteração da seleção")
        self.action_undo.triggered.connect(self.undo_last_selection)
        toolbar.addAction(self.action_undo)

        self.action_redo = QAction("Refazer", self)
        self.action_redo.setShortcut(QKeySequence("Ctrl+Y"))
        self.action_redo.setToolTip("Refazer alteração de seleção desfeita")
        self.action_redo.triggered.connect(self.redo_last_selection)
        toolbar.addAction(self.action_redo)

        toolbar.addSeparator()

        self.topology_btn = QToolButton(self)
        self.topology_btn.setText("Topologia")
        self.topology_btn.setPopupMode(
            QToolButton.ToolButtonPopupMode.InstantPopup
        )

        self.topology_menu = QMenu(self.topology_btn)
        self.topology_btn.setMenu(self.topology_menu)

        self.action_expand_one = QAction("Expandir 1 nível", self)
        self.action_expand_one.triggered.connect(
            lambda: self.run_topology_expansion(1, "both")
        )
        self.topology_menu.addAction(self.action_expand_one)

        self.action_expand_n = QAction("Expandir N níveis...", self)
        self.action_expand_n.triggered.connect(
            lambda: self.open_topology_dialog("both")
        )
        self.topology_menu.addAction(self.action_expand_n)

        self.topology_menu.addSeparator()

        self.action_upstream_one = QAction("Upstream — 1 nível", self)
        self.action_upstream_one.triggered.connect(
            lambda: self.run_topology_expansion(1, "upstream")
        )
        self.topology_menu.addAction(self.action_upstream_one)

        self.action_upstream_n = QAction("Upstream — N níveis...", self)
        self.action_upstream_n.triggered.connect(
            lambda: self.open_topology_dialog("upstream")
        )
        self.topology_menu.addAction(self.action_upstream_n)

        self.action_downstream_one = QAction("Downstream — 1 nível", self)
        self.action_downstream_one.triggered.connect(
            lambda: self.run_topology_expansion(1, "downstream")
        )
        self.topology_menu.addAction(self.action_downstream_one)

        self.action_downstream_n = QAction("Downstream — N níveis...", self)
        self.action_downstream_n.triggered.connect(
            lambda: self.open_topology_dialog("downstream")
        )
        self.topology_menu.addAction(self.action_downstream_n)

        self.topology_menu.addSeparator()

        self.action_expand_until = QAction(
            "Expandir até elemento de parada...", self
        )
        self.action_expand_until.triggered.connect(
            self.open_topology_stop_dialog
        )
        self.topology_menu.addAction(self.action_expand_until)

        self.topology_menu.addSeparator()

        self.action_connected_component = QAction(
            "Selecionar componente conectado...", self
        )
        self.action_connected_component.triggered.connect(
            self.open_connected_component_dialog
        )
        self.topology_menu.addAction(self.action_connected_component)

        self.action_diagnose_components = QAction(
            "Diagnosticar componentes desconectados", self
        )
        self.action_diagnose_components.triggered.connect(
            self.diagnose_connected_components
        )
        self.topology_menu.addAction(self.action_diagnose_components)

        self.action_inspect_islands = QAction("Inspecionar ilhas...", self)
        self.action_inspect_islands.setEnabled(False)
        self.action_inspect_islands.triggered.connect(self.inspect_islands)
        self.topology_menu.addAction(self.action_inspect_islands)

        self.action_network_diagnostics = QAction("Diagnóstico de qualidade da rede...", self)
        self.action_network_diagnostics.triggered.connect(self.open_network_diagnostics)
        self.topology_menu.addAction(self.action_network_diagnostics)
        self.action_view_network_diagnostics = QAction("Ver último diagnóstico de qualidade...", self)
        self.action_view_network_diagnostics.setEnabled(False)
        self.action_view_network_diagnostics.triggered.connect(self.view_network_diagnostics)
        self.topology_menu.addAction(self.action_view_network_diagnostics)
        self.action_export_network_diagnostics = QAction("Exportar último diagnóstico de qualidade...", self)
        self.action_export_network_diagnostics.setEnabled(False)
        self.action_export_network_diagnostics.triggered.connect(self.export_network_diagnostics)
        self.topology_menu.addAction(self.action_export_network_diagnostics)

        self.action_export_component_report = QAction(
            "Exportar último relatório de ilhas...", self
        )
        self.action_export_component_report.setEnabled(False)
        self.action_export_component_report.triggered.connect(
            self.export_connected_component_report
        )
        self.topology_menu.addAction(self.action_export_component_report)

        toolbar.addWidget(self.topology_btn)

        toolbar.addSeparator()

        self.action_export = QAction("Exportar", self)
        self.action_export.triggered.connect(self.export_model)
        toolbar.addAction(self.action_export)

        self.map_tools_btn = QToolButton(self)
        self.map_tools_btn.setText("Mapa")
        self.map_tools_btn.setPopupMode(
            QToolButton.ToolButtonPopupMode.InstantPopup
        )

        self.map_tools_menu = QMenu(self.map_tools_btn)
        self.map_tools_btn.setMenu(self.map_tools_menu)

        self.action_map = QAction("Mostrar mapa", self)
        self.action_map.setCheckable(True)
        self.action_map.toggled.connect(self.toggle_map)
        self.map_tools_menu.addAction(self.action_map)

        self.action_refresh_map = QAction("Atualizar mapa", self)
        self.action_refresh_map.triggered.connect(self.refresh_map)
        self.map_tools_menu.addAction(self.action_refresh_map)

        self.action_refresh_region = QAction(
            "Atualizar região visível", self
        )
        self.action_refresh_region.triggered.connect(
            self.refresh_visible_region
        )
        self.map_tools_menu.addAction(self.action_refresh_region)

        self.map_tools_menu.addSeparator()

        self.action_symbology = QAction("Simbologia...", self)
        self.action_symbology.triggered.connect(
            self.open_symbology_dialog
        )
        self.map_tools_menu.addAction(self.action_symbology)

        self.action_reset_symbology = QAction(
            "Restaurar simbologia padrão", self
        )
        self.action_reset_symbology.triggered.connect(
            self.reset_map_symbology
        )
        self.map_tools_menu.addAction(
            self.action_reset_symbology
        )

        self.map_tools_menu.addSeparator()

        self.action_zoom_extents = QAction("Zoom Extents", self)
        self.action_zoom_extents.triggered.connect(
            self.map_widget.view.zoom_extents
        )
        self.map_tools_menu.addAction(self.action_zoom_extents)

        self.action_zoom_selection = QAction("Zoom Selection", self)
        self.action_zoom_selection.triggered.connect(
            self.zoom_to_selection
        )
        self.map_tools_menu.addAction(self.action_zoom_selection)

        self.action_map_selection_diag = QAction(
            "Diagnosticar seleção no mapa", self
        )
        self.action_map_selection_diag.triggered.connect(
            self.diagnose_map_selection
        )
        self.map_tools_menu.addAction(self.action_map_selection_diag)

        self.map_tools_menu.addSeparator()

        self.action_map_pan = QAction("Modo: Pan / clique", self)
        self.action_map_pan.triggered.connect(
            lambda: self.set_map_mode("pan")
        )
        self.map_tools_menu.addAction(self.action_map_pan)

        self.action_map_rect = QAction(
            "Modo: Seleção por retângulo", self
        )
        self.action_map_rect.triggered.connect(
            lambda: self.set_map_mode("rectangle")
        )
        self.map_tools_menu.addAction(self.action_map_rect)

        self.action_map_poly = QAction(
            "Modo: Seleção por polígono", self
        )
        self.action_map_poly.triggered.connect(
            lambda: self.set_map_mode("polygon")
        )
        self.map_tools_menu.addAction(self.action_map_poly)

        toolbar.addWidget(self.map_tools_btn)

    def build_status_progress(self):
        self.status_progress = QProgressBar(self)
        self.status_progress.setTextVisible(False)
        self.status_progress.setFixedWidth(180)
        self.status_progress.setFixedHeight(14)
        self.status_progress.hide()
        self.statusBar().addPermanentWidget(self.status_progress)

    @contextmanager
    def busy(self, message="Processando..."):
        """
        Shows an indeterminate activity bar for operations whose exact progress
        cannot yet be measured honestly. This is preferable to inventing a %.
        """
        previous = self.statusBar().currentMessage()
        self.statusBar().showMessage(message)
        self.status_progress.setRange(0, 0)
        self.status_progress.show()
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        QApplication.processEvents()
        try:
            yield
        finally:
            QApplication.restoreOverrideCursor()
            self.status_progress.hide()
            self.status_progress.setRange(0, 100)
            self.status_progress.setValue(0)
            if previous:
                self.statusBar().showMessage(previous)
            QApplication.processEvents()

    def update_progress(self, done, total, stage):
        self.status_progress.setRange(0, max(1, total))
        self.status_progress.setValue(min(done, max(1, total)))
        self.status_progress.setTextVisible(True)
        self.statusBar().showMessage(f"{stage}: {done:,} de {total:,}".replace(",", "."))
        QApplication.processEvents()

    def unit_system_changed(self):
        system = self.units_combo.currentData()
        self.backend.set_unit_system(system)

        if self.current_type:
            # Display and samples change units; IDs/SelectionSet do not.
            try:
                with self.busy(
                    "Atualizando unidades da tabela..."
                ):
                    self.load_page()
            except Exception as exc:
                self.show_error("Unidades", exc)

    def setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+A"), self.table, activated=self.select_visual_page)
        QShortcut(QKeySequence("Ctrl+Shift+A"), self.table, activated=self.clear_visual_selection)
        QShortcut(QKeySequence("Space"), self.table, activated=self.toggle_visual_selection)

    # ---------------------------------------------------------
    # generic helpers
    # ---------------------------------------------------------
    def closeEvent(self, event):
        self.backend.close()
        super().closeEvent(event)

    def set_model_enabled(self, enabled):
        widgets = (
            self.activate_btn,
            self.type_list,
            self.id_select_btn,
            self.wg_sets_btn,
            self.columns_btn,
            self.table_columns_btn,
            self.prev_btn,
            self.next_btn,
            self.page_size,
            self.table,
            self.advanced_filter,
            self.dependencies_btn,
            self.associated_meters_btn,
            self.clear_btn,
            self.export_btn,
            self.shapefile_fields_btn,
            self.select_page_btn,
            self.deselect_page_btn,
            self.select_results_btn,
            self.deselect_results_btn,
        )

        for widget in widgets:
            widget.setEnabled(enabled)
        self.action_shapefile_fields.setEnabled(enabled)
        self.action_write_column_profile.setEnabled(enabled)
        self.action_load_column_profile.setEnabled(enabled)

    def show_error(self, title, exc):
        QMessageBox.critical(self, title, str(exc))

    def parse_filter_value(self, text):
        value = text.strip()

        low = value.casefold()
        if low == "true":
            return True
        if low == "false":
            return False
        if low in {"none", "null"}:
            return None

        try:
            return int(value)
        except ValueError:
            pass

        try:
            return float(value)
        except ValueError:
            return value


    def reset_scenario_ui(self):
        """
        Reinicia toda a UI dependente do cenário, mantendo arquivo e combo de cenários.
        """
        self.current_type = None
        self.current_offset = 0
        self.current_ids = []
        self.current_rows = []
        self.active_filter = None
        self.table_selected_only = False
        if hasattr(self, 'table_selected_only_cb'):
            self.table_selected_only_cb.setChecked(False)
        self.table_columns_by_type.clear()
        self.last_component_diagnosis = None
        self.last_network_diagnostics = None
        if hasattr(self, "action_export_component_report"):
            self.action_export_component_report.setEnabled(False)
        if hasattr(self, "action_inspect_islands"):
            self.action_inspect_islands.setEnabled(False)
        if hasattr(self, "action_export_network_diagnostics"):
            self.action_export_network_diagnostics.setEnabled(False)
        if hasattr(self, "action_view_network_diagnostics"):
            self.action_view_network_diagnostics.setEnabled(False)

        self.type_list.clear()

        self.table.clear()
        self.table.setRowCount(0)
        self.table.setColumnCount(0)

        self.page_label.setText("0–0")
        self.result_label.setText("0 resultados")
        self.summary.setPlainText("")
        if hasattr(self, 'map_widget'):
            self.map_widget.clear_map()

    def reset_all_ui(self):
        """
        Reinicia também o arquivo atualmente mostrado.
        """
        self.reset_scenario_ui()
        self.path_edit.clear()
        self.scenario_combo.clear()
        self.set_model_enabled(False)
        self.open_btn.setEnabled(True)

    # ---------------------------------------------------------
    # model/scenario
    # ---------------------------------------------------------
    def open_model(self):
        if self.backend.has_open_file():
            answer = QMessageBox.question(
                self,
                "Trocar arquivo",
                "Trocar o arquivo SQLite reiniciará cenário, filtros, colunas "
                "da tabela e toda a seleção atual. Deseja continuar?",
            )
            if answer != QMessageBox.StandardButton.Yes:
                return

        path, _ = QFileDialog.getOpenFileName(
            self,
            "Abrir banco WaterGEMS",
            "",
            "WaterGEMS SQLite (*.sqlite *.wtg.sqlite);;SQLite (*.sqlite);;Todos (*.*)",
        )

        if not path:
            return

        try:
            with self.busy("Abrindo banco WaterGEMS..."):
                scenarios = self.backend.open_file(path)
        except Exception as exc:
            self.show_error("Erro ao abrir modelo", exc)
            return

        self.reset_all_ui()
        self.path_edit.setText(path)
        self.scenario_combo.clear()

        active_index = 0

        for i, scenario in enumerate(scenarios):
            indent = "    " * scenario.depth
            marker = " [ATIVO]" if scenario.is_active else ""
            text = f"{indent}{scenario.display_name} — ID {scenario.id}{marker}"

            self.scenario_combo.addItem(text, scenario.id)

            if scenario.is_active:
                active_index = i

        self.scenario_combo.setCurrentIndex(active_index)
        self.activate_btn.setEnabled(True)

        self.statusBar().showMessage(
            "Arquivo aberto. Escolha o cenário e clique em Carregar cenário."
        )

    def activate_scenario(self):
        scenario_id = self.scenario_combo.currentData()

        if scenario_id is None:
            return

        if self.backend.has_active_scenario():
            current_id = self.backend.context.selected_scenario_id
            if int(current_id) == int(scenario_id):
                return

            answer = QMessageBox.question(
                self,
                "Trocar cenário",
                "Trocar o cenário apagará toda a seleção atual, filtros, página "
                "e configurações temporárias da tabela. O arquivo SQLite permanecerá "
                "aberto. Deseja continuar?",
            )
            if answer != QMessageBox.StandardButton.Yes:
                return

        try:
            with self.busy("Carregando cenário..."):
                self.backend.activate_scenario(scenario_id)
        except Exception as exc:
            self.show_error("Erro ao carregar cenário", exc)
            return

        self.reset_scenario_ui()

        total_count = sum(count for _, count in self.backend.available_types())
        all_item = QListWidgetItem(f"Todos os elementos  ({total_count:,})".replace(",", "."))
        all_item.setData(Qt.ItemDataRole.UserRole, "__ALL__")
        self.type_list.addItem(all_item)
        self.table_columns_by_type["__ALL__"] = ["Core.Type", "Core.ID", "Core.Label", "Core.IsActive"]

        for element_type, count in self.backend.available_types():
            item = QListWidgetItem(
                f"{element_type}  ({count:,})".replace(",", ".")
            )
            item.setData(Qt.ItemDataRole.UserRole, element_type)
            self.type_list.addItem(item)

            self.table_columns_by_type[element_type] = [
                "Core.ID",
                "Core.Label",
                "Core.IsActive",
            ]

        self.set_model_enabled(True)
        self.refresh_summary()
        self.update_undo_redo_actions()

        self.map_widget.set_available_types(
            [element_type for element_type, _ in self.backend.available_types()]
        )

        if self.type_list.count():
            self.type_list.setCurrentRow(0)

        self.statusBar().showMessage(
            f"Cenário {scenario_id} carregado. Nenhum elemento foi extraído em massa."
        )

    # ---------------------------------------------------------
    # type/filter
    # ---------------------------------------------------------

    def type_changed(self, current, previous):
        if current is None:
            return
        self.current_type = current.data(Qt.ItemDataRole.UserRole)
        self.current_offset = 0
        self.active_expression = ""
        groups = (
            self.backend.all_available_table_fields()
            if self.current_type == "__ALL__"
            else self.backend.available_table_fields(self.current_type)
        )
        self.advanced_filter.set_context(self.current_type, groups)
        self.refresh_ids()
        self.load_page()

    def apply_expression_filter(self, expression):
        if not self.current_type:
            return
        self.active_expression = expression.strip()
        self.current_offset = 0
        try:
            with self.busy("Aplicando filtro..."):
                self.refresh_ids()
                self.load_page()
        except Exception as exc:
            self.show_error("Erro no filtro", exc)

    def clear_expression_filter(self):
        self.active_expression = ""
        self.current_offset = 0
        if self.current_type:
            self.refresh_ids()
            self.load_page()

    def refresh_ids(self):
        if not self.current_type:
            self.current_ids = []
            return

        if self.current_type == "__ALL__":
            ids = self.backend.all_expression_rows(
                self.active_expression or None
            )

            if self.table_selected_only:
                selected = set(self.backend.selected_pairs())
                ids = [pair for pair in ids if pair in selected]

            self.current_ids = ids
            return

        if self.active_expression:
            ids = self.backend.expression_ids(
                self.current_type,
                self.active_expression,
            )
        else:
            ids = self.backend.model_repo.root_ids(
                self.current_type
            )

        if self.table_selected_only:
            selected_ids = self.backend.selection.selected.get(
                self.current_type,
                set(),
            )
            ids = [x for x in ids if int(x) in selected_ids]

        self.current_ids = ids

    # ---------------------------------------------------------
    # paging/table
    # ---------------------------------------------------------
    def reload_first_page(self):
        if not self.current_type:
            return

        self.current_offset = 0
        self.load_page()

    def load_page(self):
        if not self.current_type:
            return

        limit = self.page_size.value()

        columns = self.table_columns_by_type.get(
            self.current_type,
            ["Core.ID", "Core.Label", "Core.IsActive"],
        )

        try:
            if self.current_type == "__ALL__":
                rows = self.backend.all_table_page(
                    self.current_ids,
                    self.current_offset,
                    limit,
                    columns,
                )
            else:
                rows = self.backend.table_page(
                    self.current_type,
                    self.current_ids,
                    self.current_offset,
                    limit,
                    columns,
                )
        except Exception as exc:
            self.show_error("Erro ao carregar tabela", exc)
            return

        self.current_rows = rows

        all_headers = ["Selecionado"] + [
            self.backend.display_field_name(field)
            for field in columns
        ]

        blocker = QSignalBlocker(self.table)

        self.table.clear()
        self.table.setColumnCount(len(all_headers))
        self.table.setHorizontalHeaderLabels(all_headers)
        self.table.setRowCount(len(rows))

        for r, row in enumerate(rows):
            element_id = int(row["Core.ID"])
            row_type = row.get("Core.Type", self.current_type)

            check_item = QTableWidgetItem()
            check_item.setFlags(
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsUserCheckable
            )
            check_item.setCheckState(
                Qt.CheckState.Checked
                if self.backend.is_selected(row_type, element_id)
                else Qt.CheckState.Unchecked
            )
            check_item.setData(Qt.ItemDataRole.UserRole, element_id)
            check_item.setData(Qt.ItemDataRole.UserRole + 1, row_type)
            self.table.setItem(r, 0, check_item)

            for c, field in enumerate(columns, start=1):
                value = row.get(field)
                item = QTableWidgetItem("" if value is None else str(value))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(r, c, item)

        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setMinimumSectionSize(45)

        del blocker

        first = self.current_offset + 1 if rows else 0
        last = self.current_offset + len(rows)
        total = len(self.current_ids)

        self.page_label.setText(f"{first}–{last}")
        self.result_label.setText(f"{total} resultados")

        self.prev_btn.setEnabled(self.current_offset > 0)
        self.next_btn.setEnabled(
            self.current_offset + limit < total
        )

    def previous_page(self):
        limit = self.page_size.value()
        self.current_offset = max(0, self.current_offset - limit)
        self.load_page()

    def next_page(self):
        limit = self.page_size.value()

        if self.current_offset + limit < len(self.current_ids):
            self.current_offset += limit
            self.load_page()

    def table_item_changed(self, item):
        if item.column() != 0 or not self.current_type:
            return

        element_id = item.data(Qt.ItemDataRole.UserRole)
        row_type = item.data(Qt.ItemDataRole.UserRole + 1) or self.current_type

        if element_id is None:
            return

        try:
            if item.checkState() == Qt.CheckState.Checked:
                self.backend.select_ids(
                    row_type,
                    [int(element_id)],
                )
            else:
                self.backend.deselect_ids(
                    row_type,
                    [int(element_id)],
                )

        except Exception as exc:
            self.show_error("Erro ao alterar seleção", exc)
            self.load_page()
            return

        self.refresh_summary()
        self.refresh_map_selection_only()

    # ---------------------------------------------------------
    
    # ---------------------------------------------------------

    def eventFilter(self, obj, event):
        if (
            obj is self.table
            and event.type() == QEvent.Type.KeyPress
            and event.key() == Qt.Key.Key_Space
        ):
            self.toggle_visual_selection()
            return True
        return super().eventFilter(obj, event)

    def selected_visual_rows(self):
        return sorted({
            index.row()
            for index in self.table.selectionModel().selectedRows()
        })

    def select_visual_page(self):
        self.table.selectAll()

    def clear_visual_selection(self):
        self.table.clearSelection()

    def set_visual_checks(self, checked):
        rows = self.selected_visual_rows()
        state = (
            Qt.CheckState.Checked
            if checked
            else Qt.CheckState.Unchecked
        )
        for row in rows:
            item = self.table.item(row, 0)
            if item is not None:
                item.setCheckState(state)

    def toggle_visual_selection(self):
        rows = self.selected_visual_rows()
        if not rows:
            return
        all_checked = all(
            self.table.item(row, 0).checkState() == Qt.CheckState.Checked
            for row in rows
        )
        self.set_visual_checks(not all_checked)

    # ---------------------------------------------------------
    # bulk selection
    # ---------------------------------------------------------

    def page_pairs(self):
        return [
            (row.get("Core.Type", self.current_type), int(row["Core.ID"]))
            for row in self.current_rows
        ]

    def _set_pairs(self, pairs, checked):
        grouped = {}
        for element_type, element_id in pairs:
            grouped.setdefault(element_type, []).append(element_id)
        for element_type, ids in grouped.items():
            if checked:
                self.backend.select_many(element_type, ids)
            else:
                self.backend.deselect_many(element_type, ids)

    def select_page(self):
        self._set_pairs(self.page_pairs(), True)
        self.load_page()
        self.after_selection_changed(reload_selected_only=False)

    def deselect_page(self):
        self._set_pairs(self.page_pairs(), False)
        self.load_page()
        self.after_selection_changed(reload_selected_only=False)

    def select_all_results(self):
        pairs = (
            self.current_ids
            if self.current_type == "__ALL__"
            else [(self.current_type, x) for x in self.current_ids]
        )
        if not pairs:
            return
        answer = QMessageBox.question(
            self,
            "Marcar resultados",
            f"Adicionar {len(pairs)} elementos ao SelectionSet?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self._set_pairs(pairs, True)
        self.load_page()
        self.after_selection_changed(reload_selected_only=False)

    def deselect_all_results(self):
        pairs = (
            self.current_ids
            if self.current_type == "__ALL__"
            else [(self.current_type, x) for x in self.current_ids]
        )
        if not pairs:
            return
        answer = QMessageBox.question(
            self,
            "Desmarcar resultados",
            f"Remover estes {len(pairs)} elementos do SelectionSet?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self._set_pairs(pairs, False)
        self.load_page()
        self.refresh_summary()

    def open_symbology_dialog(self):
        available_types = [
            element_type
            for element_type, _ in self.backend.available_types()
        ]

        dlg = SymbologyDialog(
            available_types,
            self.map_widget.symbology_settings,
            self.map_widget.default_symbology_settings(),
            parent=self,
        )

        if not dlg.exec():
            return

        self.map_widget.set_symbology_settings(
            dlg.values()
        )

    def reset_map_symbology(self):
        self.map_widget.reset_symbology()
        self.statusBar().showMessage(
            "Simbologia do mapa restaurada ao padrão."
        )

    def set_map_mode(self, mode):
        index = self.map_widget.mode_combo.findData(mode)
        if index >= 0:
            self.map_widget.mode_combo.setCurrentIndex(index)

    def sync_table_checkboxes(self):
        """
        SelectionSet is the source of truth. This method makes the visible
        checkbox state reflect it without rebuilding the page.
        """
        if not self.current_type:
            return

        blocker = QSignalBlocker(self.table)
        try:
            for row in range(self.table.rowCount()):
                item = self.table.item(row, 0)
                if item is None:
                    continue

                element_id = item.data(Qt.ItemDataRole.UserRole)
                row_type = (
                    item.data(Qt.ItemDataRole.UserRole + 1)
                    or self.current_type
                )

                checked = self.backend.is_selected(
                    row_type, int(element_id)
                )
                item.setCheckState(
                    Qt.CheckState.Checked
                    if checked
                    else Qt.CheckState.Unchecked
                )
        finally:
            del blocker

    def after_selection_changed(self, reload_selected_only=True):
        """
        Central synchronization point after any SelectionSet mutation.
        """
        self.refresh_summary()
        self.refresh_map_selection_only()

        if (
            reload_selected_only
            and self.table_selected_only
            and self.current_type
        ):
            self.current_offset = 0
            self.refresh_ids()
            self.load_page()
        else:
            self.sync_table_checkboxes()

        self.update_undo_redo_actions()

    def update_undo_redo_actions(self):
        if hasattr(self, "action_undo"):
            self.action_undo.setEnabled(
                self.backend.can_undo_selection()
            )
        if hasattr(self, "action_redo"):
            self.action_redo.setEnabled(
                self.backend.can_redo_selection()
            )

    def undo_last_selection(self):
        if not self.backend.undo_selection():
            QMessageBox.information(
                self,
                "Desfazer",
                "Não há uma alteração de seleção para desfazer.",
            )
            return

        self.after_selection_changed()
        self.statusBar().showMessage(
            "Última alteração da seleção desfeita."
        )

    def redo_last_selection(self):
        if not self.backend.redo_selection():
            QMessageBox.information(
                self,
                "Refazer",
                "Não há uma alteração de seleção para refazer.",
            )
            return

        self.after_selection_changed()
        self.statusBar().showMessage(
            "Alteração de seleção refeita."
        )

    def table_selected_only_changed(self, enabled):
        self.table_selected_only = bool(enabled)
        self.current_offset = 0

        if self.current_type:
            self.refresh_ids()
            self.load_page()

    def open_connected_component_dialog(self):
        if (
            self.backend.selection is None
            or self.backend.selection.count() == 0
        ):
            QMessageBox.information(
                self,
                "Componente conectado",
                "Selecione ao menos um elemento antes de percorrer a rede.",
            )
            return

        available_types = [
            element_type
            for element_type, _ in self.backend.available_types()
        ]
        dialog = ConnectedComponentDialog(available_types, parent=self)
        if not dialog.exec():
            return
        self.run_connected_component(**dialog.values())

    def run_connected_component(
        self,
        allowed_types,
        stop_types,
        include_stop,
        inactive_as_boundary,
    ):
        try:
            with self.busy("Localizando componente conectado..."):
                result = self.backend.select_connected_component(
                    allowed_types=allowed_types,
                    stop_types=stop_types,
                    include_stop=include_stop,
                    inactive_as_boundary=inactive_as_boundary,
                    max_new=50000,
                    max_visited=100000,
                )
        except Exception as exc:
            self.show_error("Componente conectado", exc)
            return

        self.after_selection_changed()
        if self.center_stack.currentWidget() is self.map_widget:
            self.refresh_map()

        lines = [
            f"Novos elementos adicionados: {len(result['added_pairs'])}",
            f"Elementos visitados: {result['visited_count']}",
            f"Elementos no componente: {len(result['component_pairs'])}",
            "",
            "Componente por tipo:",
        ]
        for element_type, count in result["counts"].items():
            lines.append(f"  {element_type}: {count}")

        if stop_types:
            lines += [
                "",
                "Fronteiras: " + ", ".join(stop_types),
                "Fronteiras encontradas: "
                + str(len(result["boundary_hits"])),
            ]

        if inactive_as_boundary:
            lines += [
                "",
                "Inativos tratados como extremidades: "
                + str(len(result["inactive_hits"])),
            ]

        if result["truncated"]:
            reason = {
                "max_new": "limite de 50.000 novos elementos",
                "max_visited": "limite de 100.000 elementos visitados",
            }.get(result["reason"], "limite de segurança")
            lines += [
                "",
                "A busca foi interrompida ao atingir o " + reason + ".",
            ]

        QMessageBox.information(
            self, "Componente conectado", "\n".join(lines)
        )

    def diagnose_connected_components(self):
        try:
            estimate = self.backend.connected_component_diagnosis_estimate()
        except Exception as exc:
            self.show_error("Componentes desconectados", exc)
            return

        total = estimate["total_elements"]
        seconds = estimate["estimated_seconds"]
        if seconds < 60:
            duration = f"cerca de {seconds} segundos"
        else:
            duration = f"cerca de {(seconds + 59) // 60} minuto(s)"

        answer = QMessageBox.question(
            self,
            "Analisar componentes desconectados",
            "Esta análise verificará aproximadamente "
            f"{total:,}".replace(",", ".")
            + " elementos da rede.\n\n"
            + "Estimativa aproximada: " + duration + ". "
            + "O tempo real depende do tamanho e da complexidade do banco.\n\n"
            + "Deseja iniciar a análise completa?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            with self.busy("Diagnosticando componentes desconectados..."):
                result = self.backend.diagnose_connected_components(
                    max_visited=None,
                    max_components=None,
                    progress_callback=self.update_progress,
                )
        except Exception as exc:
            self.show_error("Componentes desconectados", exc)
            return

        components = result["components"]
        self.last_component_diagnosis = result
        self.action_export_component_report.setEnabled(True)
        self.action_inspect_islands.setEnabled(True)
        lines = [
            f"Componentes identificados: {len(components)}",
            f"Elementos visitados: {result['visited_count']}",
            "",
        ]

        if not components:
            lines.append("Nenhum elemento de rede foi encontrado.")
        else:
            for index, component in enumerate(components[:20], start=1):
                detail = ", ".join(
                    f"{element_type}: {count}"
                    for element_type, count in component["counts"].items()
                )
                label = "Componente principal" if index == 1 else f"Ilha {index}"
                lines.append(
                    f"{label}: {component['size']} elementos"
                    + (f" ({detail})" if detail else "")
                )

            if len(components) > 20:
                lines += [
                    "",
                    f"Mais {len(components) - 20} componente(s) não exibido(s).",
                ]

        if result["truncated"]:
            reason = {
                "max_visited": "limite informado de elementos visitados",
                "max_new": "limite informado de elementos processados",
                "max_components": "limite informado de componentes",
            }.get(result["reason"], "limite de segurança")
            lines += [
                "",
                "Diagnóstico parcial: atingido " + reason + ".",
                f"Elementos ainda não analisados: {result['unscanned_count']}.",
            ]

        QMessageBox.information(
            self, "Componentes desconectados", "\n".join(lines)
        )

    def export_connected_component_report(self):
        if not self.last_component_diagnosis:
            QMessageBox.information(
                self,
                "Exportar relatório de ilhas",
                "Execute o diagnóstico de componentes antes de exportar.",
            )
            return

        choice = QMessageBox(self)
        choice.setWindowTitle("Campos do relatório")
        choice.setText("Escolha o nível de detalhamento do Excel.")
        choice.setInformativeText(
            "Essencial exporta Tipo, ID e Label — recomendado para redes "
            "grandes. Todos os campos inclui geometria, conectividade, "
            "propriedades e UDX, podendo levar consideravelmente mais tempo."
        )
        essential_btn = choice.addButton(
            "Essencial (recomendado)", QMessageBox.ButtonRole.AcceptRole
        )
        all_fields_btn = choice.addButton(
            "Todos os campos", QMessageBox.ButtonRole.ActionRole
        )
        choice.addButton(QMessageBox.StandardButton.Cancel)
        choice.exec()
        if choice.clickedButton() not in {essential_btn, all_fields_btn}:
            return
        include_all_fields = choice.clickedButton() is all_fields_btn

        default = Path.home() / "componentes_desconectados.xlsx"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar relatório de componentes",
            str(default),
            "Excel (*.xlsx)",
        )
        if not path:
            return
        if not path.lower().endswith(".xlsx"):
            path += ".xlsx"

        total = sum(
            len(component.get("pairs", []))
            for component in self.last_component_diagnosis["components"]
        )

        def progress(done, maximum, stage):
            self.status_progress.setRange(0, max(1, maximum))
            self.status_progress.setValue(min(done, maximum))
            self.status_progress.setTextVisible(True)
            self.statusBar().showMessage(
                f"{stage}: {min(done, maximum):,} de {maximum:,} elementos".replace(
                    ",", "."
                )
            )
            QApplication.processEvents()

        try:
            with self.busy("Exportando relatório de componentes..."):
                self.status_progress.setRange(0, max(1, total * 2))
                self.status_progress.setValue(0)
                self.status_progress.setTextVisible(True)
                self.backend.export_connected_component_report(
                    self.last_component_diagnosis,
                    path,
                    include_all_fields=include_all_fields,
                    progress_callback=progress,
                )
        except Exception as exc:
            self.show_error("Exportar relatório de ilhas", exc)
            return
        finally:
            self.status_progress.setTextVisible(False)

        QMessageBox.information(
            self,
            "Relatório exportado",
            "O relatório foi salvo com uma aba Resumo e uma aba para cada "
            "componente identificado.\n"
            + ("Detalhamento: todos os campos.\n\n" if include_all_fields
               else "Detalhamento: campos essenciais.\n\n")
            + str(path),
        )

    def inspect_islands(self):
        if not self.last_component_diagnosis:
            QMessageBox.information(self, "Inspector de ilhas", "Execute o diagnóstico de componentes antes de inspecionar.")
            return
        dialog = IslandInspectorDialog(self.last_component_diagnosis, self)
        if not dialog.exec():
            return
        pairs = dialog.selected_pairs()
        if not pairs:
            return
        try:
            self.backend.apply_pair_selection(pairs, "replace")
            self.after_selection_changed()
            self.action_map.setChecked(True)
            self.refresh_map()
            self.zoom_to_selection()
        except Exception as exc:
            self.show_error("Inspector de ilhas", exc)

    def open_network_diagnostics(self):
        try:
            with self.busy("Executando diagnóstico de qualidade da rede..."):
                diagnostics = self.backend.network_quality_diagnostics(self.update_progress)
        except Exception as exc:
            self.show_error("Diagnóstico de qualidade da rede", exc)
            return

        self.last_network_diagnostics = diagnostics
        self.action_export_network_diagnostics.setEnabled(True)
        self.action_view_network_diagnostics.setEnabled(True)

        self.view_network_diagnostics()

    def view_network_diagnostics(self):
        if not self.last_network_diagnostics:
            QMessageBox.information(
                self,
                "Diagnóstico de qualidade da rede",
                "Ainda não há um diagnóstico nesta sessão. Execute a varredura uma vez.",
            )
            return

        dialog = NetworkDiagnosticsDialog(self.last_network_diagnostics, self)
        if not dialog.exec():
            return
        pairs = dialog.selected_pairs()
        if not pairs:
            QMessageBox.information(
                self, "Diagnóstico de qualidade da rede", "Não há itens nesta verificação."
            )
            return
        try:
            self.backend.apply_pair_selection(pairs, "replace")
            self.after_selection_changed()
            if self.center_stack.currentWidget() is self.map_widget:
                self.refresh_map()
                self.zoom_to_selection()
        except Exception as exc:
            self.show_error("Diagnóstico de qualidade da rede", exc)

    def export_network_diagnostics(self):
        if not self.last_network_diagnostics:
            return
        default = Path.home() / "diagnostico_qualidade_rede.xlsx"
        path, _ = QFileDialog.getSaveFileName(self, "Exportar diagnóstico de qualidade", str(default), "Excel (*.xlsx)")
        if not path:
            return
        if not path.lower().endswith(".xlsx"):
            path += ".xlsx"
        try:
            with self.busy("Exportando diagnóstico de qualidade..."):
                self.backend.export_network_quality_diagnostics(self.last_network_diagnostics, path, self.update_progress)
        except Exception as exc:
            self.show_error("Exportar diagnóstico de qualidade", exc)

    def open_topology_stop_dialog(self):
        if (
            self.backend.selection is None
            or self.backend.selection.count() == 0
        ):
            QMessageBox.information(
                self,
                "Expansão topológica",
                "Selecione ao menos um elemento antes de expandir.",
            )
            return

        available_types = [
            element_type
            for element_type, _ in self.backend.available_types()
        ]

        dlg = TopologyStopDialog(
            available_types,
            parent=self,
            default_direction="upstream",
        )

        if not dlg.exec():
            return

        self.run_topology_stop_expansion(**dlg.values())

    def run_topology_stop_expansion(
        self,
        levels,
        direction,
        stop_types,
        include_stop,
        stop_on_first,
    ):
        direction_label = {
            "both": "Conectados",
            "upstream": "Upstream topológico",
            "downstream": "Downstream topológico",
        }.get(direction, direction)

        try:
            with self.busy(
                f"Expandindo {direction_label} até critério de parada..."
            ):
                result = self.backend.expand_selection(
                    levels=levels,
                    direction=direction,
                    max_new=50000,
                    max_visited=100000,
                    stop_types=stop_types,
                    include_stop=include_stop,
                    stop_on_first=stop_on_first,
                )
        except Exception as exc:
            self.show_error("Expansão topológica", exc)
            return

        self.after_selection_changed()

        if self.center_stack.currentWidget() is self.map_widget:
            self.refresh_map()

        lines = [
            f"Direção: {direction_label}",
            f"Máximo de níveis: {levels}",
            "Tipos de parada: " + ", ".join(stop_types),
            f"Incluir elemento de parada: {'Sim' if include_stop else 'Não'}",
            "",
            f"Novos elementos adicionados: {len(result['added_pairs'])}",
            f"Elementos visitados: {result['visited_count']}",
            f"Elementos de parada encontrados: {len(result['stop_hits'])}",
        ]

        if result["added_counts"]:
            lines += ["", "Adicionados por tipo:"]
            for element_type, count in result["added_counts"].items():
                lines.append(f"  {element_type}: {count}")

        if result["stop_counts"]:
            lines += ["", "Paradas encontradas por tipo:"]
            for element_type, count in result["stop_counts"].items():
                lines.append(f"  {element_type}: {count}")

        if result["stopped_on_first"]:
            lines += [
                "",
                "A expansão foi encerrada ao encontrar o primeiro "
                "elemento de parada.",
            ]

        if result["truncated"]:
            reason = {
                "max_new": "limite de 50.000 novos elementos",
                "max_visited": "limite de 100.000 elementos visitados",
            }.get(result["reason"], "limite de segurança")

            lines += [
                "",
                f"A expansão foi interrompida ao atingir o {reason}.",
                "Use uma seleção inicial menor ou critérios de parada "
                "mais restritivos.",
            ]

        if not result["stop_hits"] and not result["truncated"]:
            lines += [
                "",
                "Nenhum dos tipos de parada foi encontrado dentro "
                "do limite de níveis informado.",
            ]

        QMessageBox.information(
            self,
            "Expansão topológica com parada",
            "\n".join(lines),
        )

    def open_topology_dialog(self, default_direction="both"):
        if (
            self.backend.selection is None
            or self.backend.selection.count() == 0
        ):
            QMessageBox.information(
                self,
                "Expansão topológica",
                "Selecione ao menos um elemento antes de expandir.",
            )
            return

        dlg = TopologyExpansionDialog(
            self,
            default_direction=default_direction,
        )

        if not dlg.exec():
            return

        levels, direction = dlg.values()
        self.run_topology_expansion(levels, direction)

    def run_topology_expansion(self, levels, direction):
        if (
            self.backend.selection is None
            or self.backend.selection.count() == 0
        ):
            QMessageBox.information(
                self,
                "Expansão topológica",
                "Selecione ao menos um elemento antes de expandir.",
            )
            return

        direction_label = {
            "both": "Conectados",
            "upstream": "Upstream",
            "downstream": "Downstream",
        }.get(direction, direction)

        try:
            with self.busy(
                f"Expandindo topologia — {direction_label}, "
                f"{levels} nível(is)..."
            ):
                result = self.backend.expand_selection(
                    levels=levels,
                    direction=direction,
                    max_new=50000,
                    max_visited=100000,
                )
        except Exception as exc:
            self.show_error("Expansão topológica", exc)
            return

        # SelectionSet is now authoritative.
        if hasattr(self, "after_selection_changed"):
            self.after_selection_changed()
        else:
            self.refresh_summary()
            self.refresh_map_selection_only()
            self.load_page()

        # Include all newly selected items in map context immediately.
        if self.center_stack.currentWidget() is self.map_widget:
            self.refresh_map()

        lines = [
            f"Direção: {direction_label}",
            f"Níveis: {levels}",
            f"Novos elementos: {len(result['added_pairs'])}",
            "",
        ]

        if result["added_counts"]:
            lines.append("Adicionados por tipo:")
            for element_type, count in result["added_counts"].items():
                lines.append(f"  {element_type}: {count}")
        else:
            lines.append("Nenhum novo elemento foi encontrado.")

        if result["truncated"]:
            reason = {
                "max_new": "limite de 50.000 novos elementos",
                "max_visited": "limite de 100.000 elementos visitados",
            }.get(result["reason"], "limite de segurança")
            lines += [
                "",
                f"A expansão foi interrompida ao atingir o {reason}.",
                "Use menos níveis ou uma seleção inicial menor para continuar.",
            ]

        QMessageBox.information(
            self,
            "Expansão topológica",
            "\n".join(lines),
        )

    # ---------------------------------------------------------
    # map
    # ---------------------------------------------------------
    def toggle_map(self, enabled):
        if enabled:
            self.center_stack.setCurrentWidget(self.map_widget)
            if not self.map_widget.items_by_key:
                self.refresh_map()
        else:
            self.center_stack.setCurrentWidget(self.table)

    def _map_context_pairs(self, max_context=12000):
        """
        Map context = evenly sampled current results + current page + full
        SelectionSet. This avoids generating hundreds of thousands of
        QGraphicsItems while still preserving context around selected items.
        """
        pairs = []

        if self.current_type == "__ALL__":
            source = list(self.current_ids)
        elif self.current_type:
            source = [
                (self.current_type, int(x))
                for x in self.current_ids
            ]
        else:
            source = []

        if len(source) <= max_context:
            pairs.extend(source)
        elif source:
            step = len(source) / float(max_context)
            for i in range(max_context):
                pairs.append(source[int(i * step)])

        # Always include the current table page.
        for row in self.current_rows:
            pair = (
                row.get("Core.Type", self.current_type),
                int(row["Core.ID"]),
            )
            pairs.append(pair)

        # Always include every selected element.
        pairs.extend(self.backend.selected_pairs())

        # Preserve order, eliminate duplicates.
        seen = set()
        unique = []
        for pair in pairs:
            if pair[0] and pair not in seen:
                seen.add(pair)
                unique.append(pair)

        return unique

    def _current_result_pairs(self):
        if self.current_type == "__ALL__":
            return list(self.current_ids)

        if self.current_type:
            return [
                (self.current_type, int(x))
                for x in self.current_ids
            ]

        return []

    def refresh_visible_region(self):
        if not self.backend.has_active_scenario():
            return

        # Ensure the map is actually visible before interpreting its viewport.
        if self.center_stack.currentWidget() is not self.map_widget:
            self.action_map.setChecked(True)

        candidates = self._current_result_pairs()
        if not candidates:
            self.map_widget.clear_map()
            return

        extent = self.map_widget.view.visible_model_extent()

        try:
            with self.busy("Atualizando região visível do mapa..."):
                result = self.backend.map_geometries_in_extent(
                    candidates,
                    extent,
                    max_checks=40000,
                    max_results=25000,
                    max_seconds=10.0,
                )
        except Exception as exc:
            self.show_error("Mapa", exc)
            return

        if result["truncated"]:
            reason_text = {
                "max_checks": "o limite seguro de elementos examinados",
                "max_results": "o limite seguro de elementos exibidos",
                "max_seconds": "o tempo máximo de processamento",
            }.get(result["reason"], "um limite de segurança")

            QMessageBox.information(
                self,
                "Região muito densa",
                "Não foi possível concluir a atualização regional porque "
                f"foi atingido {reason_text}.\n\n"
                "Aproxime mais o zoom ou aplique um filtro para reduzir "
                "a quantidade de elementos e tente novamente.",
            )
            return

        # Always keep selected elements visible even if outside the region,
        # mirroring the normal map behavior.
        selected_pairs = self.backend.selected_pairs()
        known = {
            (row["type"], int(row["id"]))
            for row in result["rows"]
        }
        missing_selected = [
            pair for pair in selected_pairs
            if pair not in known
        ]

        if missing_selected:
            result["rows"].extend(
                self.backend.map_geometries(missing_selected)
            )

        self.map_widget.load_geometries(
            result["rows"],
            selected_pairs,
            zoom_extents=False,
        )

        self.statusBar().showMessage(
            f"Região atualizada: {len(result['rows'])} geometrias; "
            f"{result['checked']} elementos examinados."
        )

    def refresh_map(self):
        if not self.backend.has_active_scenario():
            return

        pairs = self._map_context_pairs()
        if not pairs:
            self.map_widget.clear_map()
            return

        try:
            with self.busy(
                f"Carregando contexto do mapa ({len(pairs)} elementos)..."
            ):
                map_report = self.backend.map_geometries_report(pairs)
        except Exception as exc:
            self.show_error("Mapa", exc)
            return

        selected_pairs = self.backend.selected_pairs()

        self.map_widget.load_geometries(
            map_report["rows"],
            selected_pairs,
        )

        # Explicitly re-check SelectionSet after the sampled context load.
        report = self.ensure_selected_elements_in_map(
            show_feedback=False
        )

        fallback_count = len(map_report.get("fallback", []))
        missing_count = len(report["missing"])

        message = (
            f"Mapa atualizado: {len(self.map_widget.items_by_key)} "
            "geometrias."
        )
        if fallback_count:
            message += (
                f" {fallback_count} Pipe(s) desenhado(s) pelo fallback "
                "StartNode–StopNode."
            )
        if missing_count:
            message += (
                f" {missing_count} selecionado(s) sem geometria resolvida."
            )

        self.statusBar().showMessage(message)

        if missing_count:
            self.show_map_geometry_missing(report["missing"])

    def ensure_selected_elements_in_map(self, show_feedback=False):
        """
        Guarantees that every selected element with resolvable geometry is
        loaded into the map. Returns a diagnostic report.
        """
        if not self.backend.has_active_scenario():
            return {
                "requested": 0,
                "loaded_now": 0,
                "already_loaded": 0,
                "missing": [],
            }

        selected_pairs = self.backend.selected_pairs()
        if not selected_pairs:
            return {
                "requested": 0,
                "loaded_now": 0,
                "already_loaded": 0,
                "missing": [],
            }

        loaded_before = set(self.map_widget.items_by_key.keys())
        missing_from_map = [
            pair for pair in selected_pairs
            if pair not in loaded_before
        ]

        geometry_missing = []
        fallback_pairs = []
        loaded_now = 0

        if missing_from_map:
            try:
                with self.busy(
                    f"Carregando {len(missing_from_map)} elemento(s) "
                    "selecionado(s) no mapa..."
                ):
                    report = self.backend.map_geometries_report(
                        missing_from_map
                    )
            except Exception as exc:
                self.show_error("Mapa", exc)
                return {
                    "requested": len(selected_pairs),
                    "loaded_now": 0,
                    "already_loaded": len(loaded_before & set(selected_pairs)),
                    "missing": missing_from_map,
                }

            geometry_missing = report["missing"]
            fallback_pairs = report.get("fallback", [])
            loaded_now = report["loaded"]

            if report["rows"]:
                self.map_widget.append_geometries(
                    report["rows"],
                    selected_keys=selected_pairs,
                )

        self.map_widget.update_selection(selected_pairs)

        result = {
            "requested": len(selected_pairs),
            "loaded_now": loaded_now,
            "already_loaded": len(
                loaded_before & set(selected_pairs)
            ),
            "missing": geometry_missing,
            "fallback": fallback_pairs,
        }

        if show_feedback and geometry_missing:
            self.show_map_geometry_missing(geometry_missing)

        return result

    def show_map_geometry_missing(self, missing_pairs):
        preview = list(missing_pairs)[:15]

        lines = [
            "Alguns elementos selecionados não puderam ser posicionados "
            "no mapa no cenário atual.",
            "",
            f"Sem geometria resolvida: {len(missing_pairs)}",
            "",
            "Primeiros IDs:",
        ]
        lines.extend(
            f"  {element_type}: {element_id}"
            for element_type, element_id in preview
        )

        if len(missing_pairs) > len(preview):
            lines.append(
                f"  ... +{len(missing_pairs) - len(preview)}"
            )

        lines += [
            "",
            "Para Pipes, o programa também tentou o fallback por "
            "StartNode/StopNode.",
        ]

        QMessageBox.warning(
            self,
            "Geometria não encontrada",
            "\n".join(lines),
        )

    def diagnose_map_selection(self):
        selected = self.backend.selected_pairs()

        if not selected:
            QMessageBox.information(
                self,
                "Diagnóstico do mapa",
                "Não há elementos no SelectionSet.",
            )
            return

        try:
            with self.busy(
                f"Diagnosticando {len(selected)} selecionado(s)..."
            ):
                report = self.backend.map_geometries_report(selected)
                details = self.backend.map_geometry_diagnostics(selected)
        except Exception as exc:
            self.show_error("Diagnóstico do mapa", exc)
            return

        already_on_scene = set(self.map_widget.items_by_key)

        lines = [
            f"SelectionSet: {len(selected)}",
            f"Geometria resolvida: {report['loaded']}",
            f"Já presentes na cena: "
            f"{len(set(selected) & already_on_scene)}",
            f"Fallback StartNode–StopNode: "
            f"{len(report.get('fallback', []))}",
            f"Sem geometria: {len(report['missing'])}",
        ]

        # For small selections show the inheritance trace. This is especially
        # useful when debugging one Pipe/Junction.
        if len(details) <= 5:
            for detail in details:
                lines += [
                    "",
                    f"{detail['type']}: {detail['id']}",
                    f"Tabela: {detail['table']}",
                ]

                if detail["geometry_found"]:
                    lines.append(
                        "Geometria herdada de Alternative "
                        f"{detail['alternative_id']} "
                        f"(Scenario {detail['scenario_id']})"
                    )
                else:
                    lines.append(
                        "Nenhuma HMIGeometry válida encontrada na cadeia."
                    )

                for attempt in detail["attempts"][:12]:
                    alt = attempt.get("alternative_id")
                    scn = attempt.get("scenario_id")

                    if not attempt.get("has_row"):
                        status = "sem linha"
                    elif not attempt.get("has_blob"):
                        status = "linha encontrada, HMIGeometry NULL"
                    elif attempt.get("decode_error"):
                        status = "WKB inválido"
                    else:
                        status = "WKB válido"

                    lines.append(
                        f"  Scenario {scn} / Alt {alt}: {status}"
                    )

        if report.get("fallback"):
            lines += ["", "Fallback visual:"]
            lines.extend(
                f"  {t}: {i}"
                for t, i in report["fallback"][:15]
            )

        if report["missing"]:
            lines += ["", "Sem geometria final:"]
            lines.extend(
                f"  {t}: {i}"
                for t, i in report["missing"][:15]
            )

        QMessageBox.information(
            self,
            "Diagnóstico do mapa",
            "\n".join(lines),
        )

    def zoom_to_selection(self):
        selected = self.backend.selected_pairs()
        if not selected:
            QMessageBox.information(
                self,
                "Zoom Selection",
                "Não há elementos selecionados.",
            )
            return

        report = self.ensure_selected_elements_in_map(
            show_feedback=True
        )

        if not self.map_widget.zoom_selection():
            QMessageBox.warning(
                self,
                "Zoom Selection",
                "Nenhum dos elementos selecionados possui geometria "
                "disponível no mapa para este cenário.",
            )
            return

        self.statusBar().showMessage(
            f"Zoom Selection: {len(selected)} elemento(s) selecionado(s); "
            f"{len(report['missing'])} sem geometria resolvida."
        )

    def refresh_map_selection_only(self):
        if not hasattr(self, "map_widget"):
            return

        selected_pairs = self.backend.selected_pairs()

        # If the map has already been initialized, selections made from the
        # table/filter/WaterGEMS Selection Set/topology are added incrementally.
        if self.map_widget.items_by_key:
            self.ensure_selected_elements_in_map()

        self.map_widget.update_selection(selected_pairs)

    def map_element_clicked(self, element_type, element_id, action):
        if action == "add":
            self.backend.apply_pair_selection(
                [(element_type, element_id)],
                "add",
            )
            self.after_selection_changed()
            return

        if action == "remove":
            self.backend.apply_pair_selection(
                [(element_type, element_id)],
                "remove",
            )
            self.after_selection_changed()
            return

        self.statusBar().showMessage(
            f"{element_type} — ID {element_id}"
        )

    def map_spatial_selection(self, pairs, action):
        if not pairs:
            return

        try:
            with self.busy(
                f"Aplicando seleção espacial ({len(pairs)} elementos)..."
            ):
                self.backend.apply_pair_selection(pairs, action)
        except Exception as exc:
            self.show_error("Seleção espacial", exc)
            return

        self.after_selection_changed()

    # ---------------------------------------------------------
    # dialogs/actions
    # ---------------------------------------------------------
    def select_ids_dialog(self):
        if not self.current_type:
            return
        if self.current_type == "__ALL__":
            QMessageBox.information(self, "Selecionar por IDs", "Escolha um tipo específico para selecionar por IDs.")
            return

        dlg = IdSelectionDialog(
            self.backend,
            self.current_type,
            self,
        )

        if dlg.exec():
            self.load_page()
            self.after_selection_changed(reload_selected_only=False)


    def watergems_selection_sets_dialog(self):
        if not self.backend.has_active_scenario():
            return

        dlg = WaterGemsSelectionSetDialog(self.backend, self)
        if dlg.exec():
            self.load_page()
            self.refresh_summary()

    def columns_dialog(self):
        if not self.current_type:
            return
        if self.current_type == "__ALL__":
            QMessageBox.information(self, "Colunas de exportação", "Escolha um tipo específico para configurar a exportação.")
            return

        dlg = ColumnConfigDialog(
            self.backend,
            initial_type=self.current_type,
            parent=self,
        )

        dlg.exec()

    def write_column_profile(self):
        scope = self.choose_column_profile_scope(
            "Gerar perfil de colunas",
            "Quais colunas habilitadas devem definir TRUE no perfil TXT?",
        )
        if scope is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Gerar perfil de colunas",
            "perfil_colunas_model_builder.txt",
            "Perfil de colunas (*.txt)",
        )
        if not path:
            return
        try:
            if scope == "export":
                enabled = None
            else:
                table_enabled = self.backend.profile_columns_from_table(
                    self.table_columns_by_type
                )
                if scope == "table":
                    enabled = table_enabled
                else:
                    export_enabled = {
                        column
                        for element_type, _ in self.backend.available_types()
                        for column in self.backend.column_config.get(element_type)
                    }
                    enabled = table_enabled | export_enabled
            count = self.backend.column_config.write_txt_profile(path, enabled)
        except Exception as exc:
            self.show_error("Erro ao gerar perfil TXT", exc)
            return
        self.statusBar().showMessage(
            f"Perfil TXT gerado com {count} colunas: {path}"
        )

    def load_column_profile(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Importar perfil de colunas",
            "",
            "Perfil de colunas (*.txt)",
        )
        if not path:
            return
        scope = self.choose_column_profile_scope(
            "Importar perfil de colunas",
            "Onde as colunas TRUE/FALSE deste perfil devem ser aplicadas?",
        )
        if scope is None:
            return
        try:
            result = self.backend.column_config.load_txt_profile(
                path,
                apply_to_export=scope in {"export", "both"},
            )
        except Exception as exc:
            self.show_error("Erro ao importar perfil TXT", exc)
            return

        if scope in {"table", "both"}:
            for element_type, _ in self.backend.available_types():
                self.table_columns_by_type[element_type] = (
                    self.backend.table_columns_from_column_profile(
                        element_type,
                        result["enabled_columns"],
                    )
                )
            self.table_columns_by_type["__ALL__"] = (
                self.backend.table_columns_from_column_profile(
                    "__ALL__",
                    result["enabled_columns"],
                )
            )
        self.current_offset = 0
        self.load_page()

        message = (
            f"Perfil aplicado: {result['applied']} colunas reconhecidas."
        )
        if result["unknown"]:
            preview = ", ".join(result["unknown"][:8])
            suffix = "..." if len(result["unknown"]) > 8 else ""
            message += (
                f"\n\nColunas não encontradas neste modelo ({len(result['unknown'])}): "
                f"{preview}{suffix}\nElas foram ignoradas."
            )
        QMessageBox.information(self, "Perfil de colunas", message)

    def choose_column_profile_scope(self, title, text):
        dialog = QMessageBox(self)
        dialog.setWindowTitle(title)
        dialog.setText(text)
        dialog.setInformativeText(
            "Os nomes de exibição e de Shapefile são sempre lidos do TXT."
        )
        table_button = dialog.addButton(
            "Somente tabela", QMessageBox.ButtonRole.ActionRole
        )
        export_button = dialog.addButton(
            "Somente exportação", QMessageBox.ButtonRole.ActionRole
        )
        both_button = dialog.addButton(
            "Tabela e exportação", QMessageBox.ButtonRole.ActionRole
        )
        dialog.addButton(QMessageBox.StandardButton.Cancel)
        dialog.exec()
        clicked = dialog.clickedButton()
        if clicked is table_button:
            return "table"
        if clicked is export_button:
            return "export"
        if clicked is both_button:
            return "both"
        return None

    def shapefile_fields_dialog(self):
        if self.backend.selection is None or self.backend.selection.count() == 0:
            QMessageBox.information(
                self,
                "Campos Shapefile",
                "Selecione ao menos um elemento antes de configurar os campos.",
            )
            return

        element_types = [
            element_type
            for element_type, ids in self.backend.selection.selected.items()
            if ids
        ]
        if not element_types:
            return

        dlg = ShapefileFieldsDialog(
            self.backend.column_config,
            element_types,
            parent=self,
        )
        if dlg.exec():
            self.statusBar().showMessage(
                "Nomes dos campos Shapefile atualizados."
            )

    def table_columns_dialog(self):
        if not self.current_type:
            return

        current = self.table_columns_by_type.get(
            self.current_type,
            ["Core.ID", "Core.Label", "Core.IsActive"],
        )

        dlg = TableColumnsDialog(
            self.backend,
            self.current_type,
            current,
            self,
        )

        if dlg.exec():
            self.table_columns_by_type[self.current_type] = dlg.selected_columns
            self.current_offset = 0
            self.load_page()

    def add_dependencies(self):
        try:
            with self.busy("Resolvendo dependências dos Pipes..."):
                added = self.backend.add_dependencies()
        except Exception as exc:
            self.show_error("Erro nas dependências", exc)
            return

        QMessageBox.information(
            self,
            "Dependências",
            f"Dependências adicionadas: {added}",
        )

        self.load_page()
        self.after_selection_changed(reload_selected_only=False)

    def add_associated_customer_meters(self):
        try:
            with self.busy("Localizando Customer Meters associados..."):
                result = self.backend.add_associated_customer_meters()
        except Exception as exc:
            self.show_error("Erro ao localizar Customer Meters", exc)
            return

        QMessageBox.information(
            self,
            "Customer Meters associados",
            "Customer Meters encontrados: {matched}\n"
            "Adicionados ao SelectionSet: {added}\n"
            "Já selecionados: {already_selected}".format(**result),
        )
        self.load_page()
        self.after_selection_changed(reload_selected_only=False)

    def clear_selection(self):
        if self.backend.selection is None:
            return

        answer = QMessageBox.question(
            self,
            "Limpar SelectionSet",
            "Remover todos os elementos selecionados?",
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        self.backend.clear_selection()

        self.load_page()
        self.after_selection_changed(reload_selected_only=False)

    def refresh_summary(self):
        if self.backend.selection is None:
            self.summary.setPlainText("")
            return

        values = self.backend.summary()
        total = self.backend.selection.count()

        lines = [f"Total: {total}", ""]

        if not values:
            lines.append("Nenhum elemento selecionado.")
        else:
            for element_type, count in values.items():
                lines.append(f"{element_type}: {count}")

        self.summary.setPlainText("\n".join(lines))

    def export_model(self):
        if (
            self.backend.selection is None
            or self.backend.selection.count() == 0
        ):
            QMessageBox.warning(
                self,
                "Exportar",
                "A seleção está vazia.",
            )
            return

        default = self.backend.source_path.with_name(
            f"{self.backend.source_path.stem}"
            f"_modelbuilder_scenario_"
            f"{self.backend.context.selected_scenario_id}.xlsx"
        )

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar ModelBuilder",
            str(default),
            "Excel (*.xlsx)",
        )

        if not path:
            return

        self.statusBar().showMessage(
            "Exportando somente os IDs selecionados..."
        )

        try:
            with self.busy("Exportando ModelBuilder..."):
                output = self.backend.export(path, progress_callback=self.update_progress)
        except Exception as exc:
            self.show_error("Erro ao exportar", exc)
            self.statusBar().showMessage("Falha na exportação.")
            return

        QMessageBox.information(
            self,
            "Exportação concluída",
            f"Arquivo criado:\n{output}",
        )

        self.statusBar().showMessage(
            f"Exportado: {output}"
        )

    def export_gis_layers(self):
        if (
            self.backend.selection is None
            or self.backend.selection.count() == 0
        ):
            QMessageBox.warning(
                self,
                "Exportar camadas GIS",
                "A seleção está vazia.",
            )
            return

        parent = QFileDialog.getExistingDirectory(
            self,
            "Escolha a pasta-base para as camadas GIS",
            str(self.backend.source_path.parent),
        )
        if not parent:
            return

        output_dir = Path(parent) / (
            f"{self.backend.source_path.stem}_gis_scenario_"
            f"{self.backend.context.selected_scenario_id}"
        )
        if output_dir.exists():
            QMessageBox.warning(
                self,
                "Exportar camadas GIS",
                "Já existe uma pasta com este nome na pasta-base escolhida. "
                "Escolha outra pasta-base ou renomeie/remova a exportação anterior.",
            )
            return

        self.statusBar().showMessage("Exportando camadas GIS selecionadas...")
        try:
            with self.busy("Exportando camadas GIS..."):
                output = self.backend.export_gis_layers(
                    output_dir,
                    progress_callback=self.update_progress,
                )
        except Exception as exc:
            self.show_error("Erro ao exportar camadas GIS", exc)
            self.statusBar().showMessage("Falha na exportação GIS.")
            return

        QMessageBox.information(
            self,
            "Camadas GIS exportadas",
            "Pasta criada:\n"
            f"{output}\n\n"
            "Importe primeiro as camadas de pontos e, em seguida, Pipes.shp "
            "com conectividade espacial.",
        )
        self.statusBar().showMessage(f"Camadas GIS exportadas: {output}")
