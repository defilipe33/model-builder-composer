from PySide6.QtCore import Qt, Signal, QPointF, QRectF
from PySide6.QtGui import (
    QPainter,
    QPainterPath,
    QPen,
    QBrush,
    QColor,
    QPolygonF,
    QAction,
)
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QGraphicsView,
    QGraphicsScene,
    QGraphicsPathItem,
    QGraphicsEllipseItem,
    QGraphicsRectItem,
    QGraphicsPolygonItem,
    QGraphicsItem,
    QGraphicsLineItem,
    QGraphicsPathItem,
    QFrame,
    QGridLayout,
    QToolButton,
    QCheckBox,
    QDoubleSpinBox,
    QComboBox,
    QToolButton,
    QMenu,
)


class NetworkMapScene(QGraphicsScene):
    pass


class StayOpenCheckMenu(QMenu):
    """
    Checkable actions stay open after clicking.
    Clicking outside the menu still closes it normally.
    Non-checkable actions use standard QMenu behavior.
    """

    def mouseReleaseEvent(self, event):
        action = self.actionAt(event.position().toPoint())

        if action is not None and action.isCheckable():
            action.trigger()
            event.accept()
            return

        super().mouseReleaseEvent(event)


class NetworkMapView(QGraphicsView):
    elementClicked = Signal(str, int, str)   # type, id, inspect/add/remove
    spatialSelection = Signal(list, str)     # [(type,id), ...], replace/add/remove
    viewportResized = Signal()

    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)

        self.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        self.setTransformationAnchor(
            QGraphicsView.ViewportAnchor.AnchorUnderMouse
        )
        self.setResizeAnchor(
            QGraphicsView.ViewportAnchor.AnchorViewCenter
        )

        self.selection_mode = "rectangle"
        self._middle_pan_active = False
        self._middle_pan_position = None

        self._rect_origin = None
        self._rubber_item = None

        self._polygon_points = []
        self._polygon_item = None

        self.set_mode("rectangle")

    def set_mode(self, mode):
        self.selection_mode = mode
        if mode == "pan":
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            self.viewport().setCursor(Qt.CursorShape.OpenHandCursor)
        else:
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            self.viewport().setCursor(Qt.CursorShape.CrossCursor)

        if mode != "polygon":
            self.cancel_polygon()

    def _restore_cursor(self):
        cursor = (
            Qt.CursorShape.OpenHandCursor
            if self.selection_mode == "pan"
            else Qt.CursorShape.CrossCursor
        )
        self.viewport().setCursor(cursor)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.viewportResized.emit()

    def wheelEvent(self, event):
        factor = 1.18 if event.angleDelta().y() > 0 else 1 / 1.18
        self.scale(factor, factor)

    @staticmethod
    def modifier_action(modifiers, default="replace"):
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            return "add"
        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            return "remove"
        return default

    def _element_at(self, scene_pos):
        for item in self.scene().items(scene_pos):
            element_type = item.data(0)
            element_id = item.data(1)
            if element_type and element_id is not None:
                return str(element_type), int(element_id)
        return None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            self._middle_pan_active = True
            self._middle_pan_position = event.position()
            self.viewport().setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return

        scene_pos = self.mapToScene(event.position().toPoint())

        if self.selection_mode == "pan":
            hit = self._element_at(scene_pos)

            if hit is not None and event.button() == Qt.MouseButton.LeftButton:
                modifiers = event.modifiers()
                if modifiers & Qt.KeyboardModifier.ControlModifier:
                    action = "add"
                elif modifiers & Qt.KeyboardModifier.ShiftModifier:
                    action = "remove"
                else:
                    action = "inspect"

                self.elementClicked.emit(
                    hit[0], hit[1], action
                )

                if action != "inspect":
                    event.accept()
                    return

            super().mousePressEvent(event)
            return

        if self.selection_mode == "rectangle":
            if event.button() == Qt.MouseButton.LeftButton:
                self._rect_origin = scene_pos
                if self._rubber_item is not None:
                    self.scene().removeItem(self._rubber_item)
                self._rubber_item = QGraphicsRectItem()
                pen = QPen(QColor(90, 180, 255))
                pen.setCosmetic(True)
                pen.setWidthF(1.5)
                self._rubber_item.setPen(pen)
                self._rubber_item.setBrush(
                    QBrush(QColor(90, 180, 255, 35))
                )
                self._rubber_item.setZValue(1000)
                self.scene().addItem(self._rubber_item)
                event.accept()
                return

        if self.selection_mode == "polygon":
            if event.button() == Qt.MouseButton.LeftButton:
                self._polygon_points.append(scene_pos)
                self._update_polygon_preview()
                event.accept()
                return

            if event.button() == Qt.MouseButton.RightButton:
                self.finish_polygon(event.modifiers())
                event.accept()
                return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._middle_pan_active and self._middle_pan_position is not None:
            delta = event.position() - self._middle_pan_position
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - round(delta.x())
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - round(delta.y())
            )
            self._middle_pan_position = event.position()
            event.accept()
            return

        if (
            self.selection_mode == "rectangle"
            and self._rect_origin is not None
            and self._rubber_item is not None
        ):
            scene_pos = self.mapToScene(event.position().toPoint())
            rect = QRectF(
                self._rect_origin,
                scene_pos,
            ).normalized()
            self._rubber_item.setRect(rect)
            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if (
            self._middle_pan_active
            and event.button() == Qt.MouseButton.MiddleButton
        ):
            self._middle_pan_active = False
            self._middle_pan_position = None
            self._restore_cursor()
            event.accept()
            return

        if (
            self.selection_mode == "rectangle"
            and self._rect_origin is not None
            and self._rubber_item is not None
            and event.button() == Qt.MouseButton.LeftButton
        ):
            rect = self._rubber_item.rect()
            action = self.modifier_action(event.modifiers())

            pairs = self._pairs_from_items(
                self.scene().items(
                    rect,
                    Qt.ItemSelectionMode.IntersectsItemShape,
                )
            )

            self.scene().removeItem(self._rubber_item)
            self._rubber_item = None
            self._rect_origin = None

            if pairs:
                self.spatialSelection.emit(pairs, action)

            event.accept()
            return

        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if (
            self.selection_mode == "polygon"
            and event.button() == Qt.MouseButton.LeftButton
        ):
            scene_pos = self.mapToScene(event.position().toPoint())
            if not self._polygon_points or self._polygon_points[-1] != scene_pos:
                self._polygon_points.append(scene_pos)
            self.finish_polygon(event.modifiers())
            event.accept()
            return

        super().mouseDoubleClickEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.cancel_polygon()
            if self._rubber_item is not None:
                self.scene().removeItem(self._rubber_item)
                self._rubber_item = None
                self._rect_origin = None
            event.accept()
            return

        if (
            self.selection_mode == "polygon"
            and event.key() in {Qt.Key.Key_Return, Qt.Key.Key_Enter}
        ):
            self.finish_polygon(event.modifiers())
            event.accept()
            return

        super().keyPressEvent(event)

    def _update_polygon_preview(self):
        if self._polygon_item is not None:
            self.scene().removeItem(self._polygon_item)

        if not self._polygon_points:
            self._polygon_item = None
            return

        polygon = QPolygonF(self._polygon_points)
        self._polygon_item = QGraphicsPolygonItem(polygon)

        pen = QPen(QColor(90, 180, 255))
        pen.setCosmetic(True)
        pen.setWidthF(1.5)

        self._polygon_item.setPen(pen)
        self._polygon_item.setBrush(
            QBrush(QColor(90, 180, 255, 35))
        )
        self._polygon_item.setZValue(1000)
        self.scene().addItem(self._polygon_item)

    def finish_polygon(self, modifiers):
        if len(self._polygon_points) < 3:
            self.cancel_polygon()
            return

        polygon = QPolygonF(self._polygon_points)
        path = QPainterPath()
        path.addPolygon(polygon)
        path.closeSubpath()

        pairs = self._pairs_from_items(
            self.scene().items(
                path,
                Qt.ItemSelectionMode.IntersectsItemShape,
            )
        )

        action = self.modifier_action(modifiers)
        self.cancel_polygon()

        if pairs:
            self.spatialSelection.emit(pairs, action)

    def cancel_polygon(self):
        self._polygon_points = []
        if self._polygon_item is not None:
            try:
                self.scene().removeItem(self._polygon_item)
            except Exception:
                pass
        self._polygon_item = None

    @staticmethod
    def _pairs_from_items(items):
        seen = set()
        result = []

        for item in items:
            if not item.isVisible():
                continue

            element_type = item.data(0)
            element_id = item.data(1)

            if not element_type or element_id is None:
                continue

            pair = (str(element_type), int(element_id))
            if pair not in seen:
                seen.add(pair)
                result.append(pair)

        return result

    def visible_model_extent(self):
        rect = self.mapToScene(self.viewport().rect()).boundingRect()

        # Scene Y is inverted relative to WaterGEMS model Y.
        minx = rect.left()
        maxx = rect.right()
        miny = -rect.bottom()
        maxy = -rect.top()

        return (minx, miny, maxx, maxy)

    def zoom_in(self):
        self.scale(1.25, 1.25)

    def zoom_out(self):
        self.scale(0.8, 0.8)

    def zoom_extents(self):
        visible = [item for item in self.scene().items() if item.isVisible()]
        if not visible:
            return

        rect = QRectF()
        for item in visible:
            rect = rect.united(item.sceneBoundingRect())

        if not rect.isNull():
            self.fitInView(
                rect.adjusted(-10, -10, 10, 10),
                Qt.AspectRatioMode.KeepAspectRatio,
            )



VALVE_TYPES = {
    "TCV",
    "FCV",
    "PRV",
    "PBV",
    "Check Valve",
    "Air Valve",
}

DEFAULT_TYPE_SYMBOLS = {
    "Junction": "circle",
    "Reservoir": "square",
    "Tank": "triangle",
    "Conventional Tank": "triangle",
    "Hydrant": "star",
    "Air Valve": "diamond",
    "TCV": "diamond",
    "FCV": "diamond",
    "PRV": "diamond",
    "PBV": "diamond",
    "Check Valve": "diamond",
    "Standard Pump": "cross",
    "Variable Speed Pump Battery": "cross",
    "Customer Meter": "circle",
}

DEFAULT_SYMBOLOGY_SETTINGS = {
    "mode": "by_type",
    "all_point_symbol": "circle",
    "group_valves": False,
    "valve_symbol": "diamond",
    "overrides": {},
}


class MapLegendOverlay(QFrame):
    sizeChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self._collapsed = False

        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(
            "QFrame { background: rgba(32, 32, 32, 220); "
            "border: 1px solid rgba(220,220,220,120); "
            "border-radius: 4px; } "
            "QLabel { color: rgb(235,235,235); background: transparent; "
            "border: none; } "
            "QToolButton { color: rgb(235,235,235); "
            "background: rgba(50,50,50,220); "
            "border: 1px solid rgba(220,220,220,100); "
            "border-radius: 3px; padding: 2px 5px; }"
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(6, 5, 6, 5)
        root.setSpacing(3)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)

        self.title = QLabel("Legenda")
        font = self.title.font()
        font.setBold(True)
        self.title.setFont(font)

        self.toggle_btn = QToolButton()
        self.toggle_btn.setText("−")
        self.toggle_btn.setToolTip("Recolher legenda")
        self.toggle_btn.clicked.connect(self.toggle_collapsed)

        header.addWidget(self.title)
        header.addStretch(1)
        header.addWidget(self.toggle_btn)

        root.addLayout(header)

        self.content = QWidget(self)
        self.grid = QGridLayout(self.content)
        self.grid.setContentsMargins(2, 2, 2, 2)
        self.grid.setHorizontalSpacing(7)
        self.grid.setVerticalSpacing(3)
        root.addWidget(self.content)

    def set_rows(self, rows):
        while self.grid.count():
            item = self.grid.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        for row, (symbol_text, label) in enumerate(rows):
            icon = QLabel(symbol_text)
            icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon.setMinimumWidth(22)
            self.grid.addWidget(icon, row, 0)
            self.grid.addWidget(QLabel(label), row, 1)

        self.adjustSize()
        self.sizeChanged.emit()

    def toggle_collapsed(self):
        self.set_collapsed(not self._collapsed)

    def set_collapsed(self, collapsed):
        self._collapsed = bool(collapsed)

        self.content.setVisible(not self._collapsed)
        self.title.setVisible(not self._collapsed)

        if self._collapsed:
            self.toggle_btn.setText("Legenda")
            self.toggle_btn.setToolTip("Expandir legenda")
        else:
            self.toggle_btn.setText("−")
            self.toggle_btn.setToolTip("Recolher legenda")

        self.adjustSize()
        self.sizeChanged.emit()

    def is_collapsed(self):
        return self._collapsed


class NetworkMapWidget(QWidget):
    elementClicked = Signal(str, int, str)
    spatialSelection = Signal(list, str)
    refreshRequested = Signal()
    ensureSelectionVisibleRequested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.scene = NetworkMapScene(self)
        self.view = NetworkMapView(self.scene, self)

        self.items_by_key = {}
        self.selected_keys = set()

        self.selected_width_px = 4.0
        self.normal_width_px = 1.0

        self.show_selected_only = False
        self.show_inactive = True
        self.visible_types = set()
        self.diagnostic_overlays = []
        self.zero_length_tolerance_ft = 0.003280839895  # 1 mm
        self.symbology_settings = dict(DEFAULT_SYMBOLOGY_SETTINGS)
        self.symbology_settings['overrides'] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        controls1 = QHBoxLayout()

        self.refresh_btn = QPushButton("Atualizar mapa")
        self.zoom_extents_btn = QPushButton("Zoom Extents")
        self.zoom_selection_btn = QPushButton("Zoom Selection")
        self.zoom_in_btn = QPushButton("Zoom +")
        self.zoom_out_btn = QPushButton("Zoom −")

        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Selecionar por retângulo", "rectangle")
        self.mode_combo.addItem("Selecionar por polígono", "polygon")

        controls1.addWidget(self.refresh_btn)
        controls1.addWidget(self.zoom_extents_btn)
        controls1.addWidget(self.zoom_selection_btn)
        controls1.addWidget(self.zoom_in_btn)
        controls1.addWidget(self.zoom_out_btn)
        controls1.addWidget(QLabel("Modo:"))
        controls1.addWidget(self.mode_combo)
        controls1.addStretch(1)

        root.addLayout(controls1)

        controls2 = QHBoxLayout()

        self.layers_btn = QToolButton()
        self.layers_btn.setText("Camadas")
        self.layers_btn.setPopupMode(
            QToolButton.ToolButtonPopupMode.InstantPopup
        )
        self.layers_menu = StayOpenCheckMenu(self.layers_btn)
        self.layers_btn.setMenu(self.layers_menu)

        self.show_inactive_cb = QCheckBox("Mostrar inativos")
        self.show_inactive_cb.setChecked(True)

        self.selected_only_cb = QCheckBox("Mostrar apenas selecionados")

        self.width_spin = QDoubleSpinBox()
        self.width_spin.setRange(1.5, 10.0)
        self.width_spin.setSingleStep(0.5)
        self.width_spin.setDecimals(1)
        self.width_spin.setValue(self.selected_width_px)
        self.width_spin.setSuffix(" px")

        self.info = QLabel("Mapa ainda não carregado.")

        controls2.addWidget(self.layers_btn)
        controls2.addWidget(self.show_inactive_cb)
        controls2.addWidget(self.selected_only_cb)
        controls2.addWidget(QLabel("Selecionado:"))
        controls2.addWidget(self.width_spin)
        controls2.addWidget(self.info, 1)

        root.addLayout(controls2)
        root.addWidget(self.view, 1)

        self.legend = MapLegendOverlay(self)
        self.legend.sizeChanged.connect(self.position_legend)
        self.view.viewportResized.connect(self.position_legend)
        self.legend.raise_()

        self.view.elementClicked.connect(self.elementClicked)
        self.view.spatialSelection.connect(self.spatialSelection)

        self.refresh_btn.clicked.connect(self.refreshRequested)
        self.zoom_extents_btn.clicked.connect(self.view.zoom_extents)
        self.zoom_selection_btn.clicked.connect(self._zoom_selection_requested)
        self.zoom_in_btn.clicked.connect(self.view.zoom_in)
        self.zoom_out_btn.clicked.connect(self.view.zoom_out)

        self.mode_combo.currentIndexChanged.connect(
            lambda: self.view.set_mode(
                self.mode_combo.currentData()
            )
        )

        self.selected_only_cb.toggled.connect(self.set_selected_only)
        self.show_inactive_cb.toggled.connect(self.set_show_inactive)
        self.width_spin.valueChanged.connect(self.set_selected_width)

    def _zoom_selection_requested(self):
        self.ensureSelectionVisibleRequested.emit()
        self.zoom_selection()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.position_legend()

    def set_available_types(self, element_types):
        old_visible = set(self.visible_types)

        self.layers_menu.clear()
        self.visible_types = set(element_types)

        for element_type in element_types:
            action = QAction(element_type, self.layers_menu)
            action.setCheckable(True)
            action.setChecked(
                element_type in old_visible
                if old_visible
                else True
            )
            action.toggled.connect(
                lambda checked, t=element_type:
                    self.set_layer_visible(t, checked)
            )
            self.layers_menu.addAction(action)

        if old_visible:
            self.visible_types = {
                t for t in element_types
                if t in old_visible
            }

    def set_layer_visible(self, element_type, visible):
        if visible:
            self.visible_types.add(element_type)
        else:
            self.visible_types.discard(element_type)
        self.apply_visibility()

    @staticmethod
    def polyline_length(geometry):
        if not isinstance(geometry, list) or len(geometry) < 2:
            return None

        total = 0.0
        for p1, p2 in zip(geometry[:-1], geometry[1:]):
            dx = float(p2[0]) - float(p1[0])
            dy = float(p2[1]) - float(p1[1])
            total += (dx * dx + dy * dy) ** 0.5
        return total

    def is_zero_length_pipe(self, geometry):
        length = self.polyline_length(geometry)
        return (
            length is not None
            and length <= self.zero_length_tolerance_ft
        )

    def make_zero_pipe_marker(self, x, y, selected):
        # Fixed-size screen symbol: circle + X.
        radius = 7.0
        item = QGraphicsEllipseItem(
            -radius, -radius, radius * 2, radius * 2
        )
        item.setPos(float(x), -float(y))
        item.setFlag(
            QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations,
            True,
        )

        pen = QPen(
            QColor(235, 60, 60)
            if selected
            else QColor(255, 185, 70)
        )
        pen.setCosmetic(True)
        pen.setWidthF(2.2 if selected else 1.8)
        item.setPen(pen)
        item.setBrush(QBrush(Qt.BrushStyle.NoBrush))

        cross_pen = QPen(pen)
        cross_pen.setWidthF(1.8)
        l1 = QGraphicsLineItem(
            -4.0, -4.0, 4.0, 4.0, item
        )
        l2 = QGraphicsLineItem(
            -4.0, 4.0, 4.0, -4.0, item
        )
        l1.setPen(cross_pen)
        l2.setPen(cross_pen)

        item.setData(3, "zero_length_pipe")
        return item

    def clear_diagnostic_overlays(self):
        for item in self.diagnostic_overlays:
            try:
                self.scene.removeItem(item)
            except Exception:
                pass
        self.diagnostic_overlays = []

    def rebuild_coincident_node_overlays(self):
        self.clear_diagnostic_overlays()

        buckets = {}
        for key, item in self.items_by_key.items():
            if key[0] == "Pipe":
                continue

            point = item.data(4)
            if not (
                isinstance(point, tuple)
                and len(point) == 2
            ):
                continue

            # 1 mm bucket in internal feet, enough for diagnostic display.
            tol = self.zero_length_tolerance_ft
            bucket = (
                round(float(point[0]) / tol),
                round(float(point[1]) / tol),
            )
            buckets.setdefault(bucket, []).append((key, point))

        for entries in buckets.values():
            if len(entries) < 2:
                continue

            x, y = entries[0][1]
            radius = 10.0
            overlay = QGraphicsEllipseItem(
                -radius, -radius, radius * 2, radius * 2
            )
            overlay.setPos(float(x), -float(y))
            overlay.setFlag(
                QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations,
                True,
            )

            pen = QPen(QColor(255, 205, 80))
            pen.setCosmetic(True)
            pen.setWidthF(2.0)
            pen.setStyle(Qt.PenStyle.DashLine)
            overlay.setPen(pen)
            overlay.setBrush(QBrush(Qt.BrushStyle.NoBrush))
            overlay.setZValue(8)

            labels = ", ".join(
                f"{t} {i}" for (t, i), _ in entries[:8]
            )
            if len(entries) > 8:
                labels += f", +{len(entries) - 8}"

            overlay.setToolTip(
                f"{len(entries)} nós coincidentes\n{labels}"
            )
            overlay.setData(3, "coincident_nodes")
            self.scene.addItem(overlay)
            self.diagnostic_overlays.append(overlay)

    def default_symbology_settings(self):
        return {
            "mode": DEFAULT_SYMBOLOGY_SETTINGS["mode"],
            "all_point_symbol": DEFAULT_SYMBOLOGY_SETTINGS[
                "all_point_symbol"
            ],
            "group_valves": DEFAULT_SYMBOLOGY_SETTINGS["group_valves"],
            "valve_symbol": DEFAULT_SYMBOLOGY_SETTINGS["valve_symbol"],
            "overrides": {},
        }

    def set_symbology_settings(self, settings):
        self.symbology_settings = {
            "mode": settings.get("mode", "by_type"),
            "all_point_symbol": settings.get(
                "all_point_symbol", "circle"
            ),
            "group_valves": bool(
                settings.get("group_valves", False)
            ),
            "valve_symbol": settings.get(
                "valve_symbol", "diamond"
            ),
            "overrides": dict(settings.get("overrides", {})),
        }

        self.rebuild_point_symbols()

    def reset_symbology(self):
        self.set_symbology_settings(
            self.default_symbology_settings()
        )

    def symbol_for_type(self, element_type):
        overrides = self.symbology_settings.get("overrides", {})

        if element_type in overrides:
            return overrides[element_type]

        if self.symbology_settings.get("mode") == "all_points":
            return self.symbology_settings.get(
                "all_point_symbol", "circle"
            )

        if (
            self.symbology_settings.get("group_valves")
            and element_type in VALVE_TYPES
        ):
            return self.symbology_settings.get(
                "valve_symbol", "diamond"
            )

        return DEFAULT_TYPE_SYMBOLS.get(element_type, "circle")

    @staticmethod
    def symbol_text(symbol):
        return {
            "circle": "●",
            "square": "■",
            "diamond": "◆",
            "triangle": "▲",
            "cross": "+",
            "x": "×",
            "star": "★",
        }.get(symbol, "●")

    def make_point_symbol(
        self,
        element_type,
        x,
        y,
        selected,
        is_active,
        element_id,
    ):
        symbol = self.symbol_for_type(element_type)
        size = 7.0

        pen = self.make_pen(selected)
        brush = QBrush(
            QColor(235, 60, 60)
            if selected
            else QColor(220, 220, 220)
        )

        if symbol == "circle":
            item = QGraphicsEllipseItem(
                -size / 2, -size / 2, size, size
            )
            item.setBrush(brush)

        elif symbol == "square":
            item = QGraphicsRectItem(
                -size / 2, -size / 2, size, size
            )
            item.setBrush(brush)

        elif symbol in {"diamond", "triangle", "star"}:
            path = QPainterPath()

            if symbol == "diamond":
                path.moveTo(0, -size / 1.4)
                path.lineTo(size / 1.4, 0)
                path.lineTo(0, size / 1.4)
                path.lineTo(-size / 1.4, 0)
                path.closeSubpath()

            elif symbol == "triangle":
                path.moveTo(0, -size / 1.25)
                path.lineTo(size / 1.15, size / 1.35)
                path.lineTo(-size / 1.15, size / 1.35)
                path.closeSubpath()

            else:
                import math
                outer = size / 1.1
                inner = size / 2.5
                for i in range(10):
                    angle = -math.pi / 2 + i * math.pi / 5
                    radius = outer if i % 2 == 0 else inner
                    px = math.cos(angle) * radius
                    py = math.sin(angle) * radius
                    if i == 0:
                        path.moveTo(px, py)
                    else:
                        path.lineTo(px, py)
                path.closeSubpath()

            item = QGraphicsPathItem(path)
            item.setBrush(brush)

        else:
            path = QPainterPath()
            extent = size / 1.15

            if symbol == "cross":
                path.moveTo(-extent, 0)
                path.lineTo(extent, 0)
                path.moveTo(0, -extent)
                path.lineTo(0, extent)
            else:
                path.moveTo(-extent, -extent)
                path.lineTo(extent, extent)
                path.moveTo(-extent, extent)
                path.lineTo(extent, -extent)

            item = QGraphicsPathItem(path)
            item.setBrush(QBrush(Qt.BrushStyle.NoBrush))

        item.setPen(pen)
        item.setPos(float(x), -float(y))
        item.setFlag(
            QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations,
            True,
        )
        item.setData(0, element_type)
        item.setData(1, int(element_id))
        item.setData(2, is_active)
        item.setData(4, (float(x), float(y)))
        item.setData(5, symbol)
        return item

    def rebuild_point_symbols(self):
        replacements = []

        for key, old_item in list(self.items_by_key.items()):
            if key[0] == "Pipe":
                continue

            point = old_item.data(4)
            if not (
                isinstance(point, tuple)
                and len(point) == 2
            ):
                continue

            selected = key in self.selected_keys
            is_active = old_item.data(2)
            tooltip = old_item.toolTip()

            new_item = self.make_point_symbol(
                key[0],
                point[0],
                point[1],
                selected,
                is_active,
                key[1],
            )
            new_item.setToolTip(tooltip)
            new_item.setZValue(4 if selected else 2)

            replacements.append((key, old_item, new_item))

        for key, old_item, new_item in replacements:
            self.scene.removeItem(old_item)
            self.scene.addItem(new_item)
            self.items_by_key[key] = new_item

        self.rebuild_coincident_node_overlays()
        self.update_legend()
        self.apply_visibility()

    def legend_rows(self):
        element_types = sorted({
            key[0] for key in self.items_by_key
            if key[0] != "Pipe"
        })

        rows = [("━", "Pipe")]

        if self.symbology_settings.get("mode") == "all_points":
            rows.append(
                (
                    self.symbol_text(
                        self.symbology_settings.get(
                            "all_point_symbol", "circle"
                        )
                    ),
                    "Elementos pontuais",
                )
            )
        else:
            grouped = {}
            for element_type in element_types:
                symbol = self.symbol_for_type(element_type)
                grouped.setdefault(symbol, []).append(element_type)

            for symbol, types in grouped.items():
                label = ", ".join(types)
                rows.append((self.symbol_text(symbol), label))

        rows.append(("⊗", "Pipe com comprimento ≈ 0"))
        rows.append(("◌", "Nós coincidentes"))
        return rows

    def update_legend(self):
        self.legend.set_rows(self.legend_rows())
        self.position_legend()
        self.legend.show()
        self.legend.raise_()

    def position_legend(self):
        if not hasattr(self, "legend"):
            return

        margin = 12
        self.legend.adjustSize()

        view_rect = self.view.geometry()

        # The legend's bottom-right corner is the fixed anchor.  Recalculate
        # both coordinates after any content or viewport size change so an
        # expanded legend grows left/up, while the compact button returns to
        # this exact map corner.
        x = view_rect.x() + view_rect.width() - self.legend.width() - margin
        y = view_rect.y() + view_rect.height() - self.legend.height() - margin

        self.legend.move(x, y)
        self.legend.raise_()

    def make_pen(self, selected):
        pen = QPen(
            QColor(235, 60, 60)
            if selected
            else QColor(210, 210, 210)
        )
        pen.setCosmetic(True)
        pen.setWidthF(
            self.selected_width_px
            if selected
            else self.normal_width_px
        )
        return pen

    def set_selected_width(self, value):
        self.selected_width_px = float(value)
        self.update_selection(self.selected_keys)

    def set_selected_only(self, enabled):
        self.show_selected_only = bool(enabled)
        self.apply_visibility()

    def set_show_inactive(self, enabled):
        self.show_inactive = bool(enabled)
        self.apply_visibility()

    def apply_visibility(self):
        for key, item in self.items_by_key.items():
            element_type = key[0]
            is_active = item.data(2)

            visible = element_type in self.visible_types

            if self.show_selected_only:
                visible = visible and key in self.selected_keys

            if not self.show_inactive:
                visible = visible and is_active is not False

            item.setVisible(visible)

    def clear_map(self):
        self.scene.clear()
        self.items_by_key.clear()
        self.diagnostic_overlays = []
        self.selected_keys = set()
        self.info.setText("Mapa ainda não carregado.")

    def load_geometries(
        self,
        geometries,
        selected_keys=None,
        zoom_extents=True,
        clear_existing=True,
    ):
        if clear_existing:
            self.scene.clear()
            self.items_by_key.clear()

        self.scene.setBackgroundBrush(
            QBrush(QColor(48, 48, 48))
        )

        self.selected_keys = set(selected_keys or [])

        count = 0

        for entry in geometries:
            element_type = entry["type"]
            element_id = int(entry["id"])
            geometry = entry["geometry"]
            is_active = entry.get("is_active")

            key = (element_type, element_id)

            if not clear_existing and key in self.items_by_key:
                continue

            selected = key in self.selected_keys

            graphics_item = None

            if (
                element_type == "Pipe"
                and isinstance(geometry, list)
                and len(geometry) >= 2
            ):
                if self.is_zero_length_pipe(geometry):
                    x0, y0 = geometry[0]
                    graphics_item = self.make_zero_pipe_marker(
                        x0, y0, selected
                    )
                    graphics_item.setZValue(9 if selected else 7)
                else:
                    path = QPainterPath()
                    x0, y0 = geometry[0]
                    path.moveTo(float(x0), -float(y0))

                    for x, y in geometry[1:]:
                        path.lineTo(float(x), -float(y))

                    graphics_item = QGraphicsPathItem(path)
                    graphics_item.setPen(self.make_pen(selected))
                    graphics_item.setZValue(4 if selected else 0)

            elif (
                isinstance(geometry, tuple)
                and len(geometry) == 2
            ):
                x, y = geometry
                graphics_item = self.make_point_symbol(
                    element_type,
                    x,
                    y,
                    selected,
                    is_active,
                    element_id,
                )
                graphics_item.setZValue(4 if selected else 2)

            if graphics_item is None:
                continue

            graphics_item.setData(0, element_type)
            graphics_item.setData(1, element_id)
            graphics_item.setData(2, is_active)
            if isinstance(geometry, tuple) and len(geometry) == 2:
                graphics_item.setData(
                    4,
                    (float(geometry[0]), float(geometry[1])),
                )

            active_text = (
                "Ativo"
                if is_active is True
                else "Inativo"
                if is_active is False
                else "Atividade indefinida"
            )
            diagnostic_text = ""
            if (
                element_type == "Pipe"
                and isinstance(geometry, list)
                and self.is_zero_length_pipe(geometry)
            ):
                length_ft = self.polyline_length(geometry) or 0.0
                length_m = length_ft * 0.3048
                diagnostic_text = (
                    f"\nDIAGNÓSTICO: comprimento geométrico ≈ zero "
                    f"({length_m:.6g} m)"
                )

            graphics_item.setToolTip(
                f"{element_type} — ID {element_id} — {active_text}"
                f"{diagnostic_text}"
            )

            self.scene.addItem(graphics_item)
            self.items_by_key[key] = graphics_item
            count += 1

        self.rebuild_coincident_node_overlays()
        self.update_legend()
        self.info.setText(f"{len(self.items_by_key)} geometrias carregadas")
        self.apply_visibility()
        if zoom_extents:
            self.view.zoom_extents()

    def append_geometries(self, geometries, selected_keys=None):
        self.load_geometries(
            geometries,
            selected_keys=selected_keys,
            zoom_extents=False,
            clear_existing=False,
        )

    def update_selection(self, selected_keys):
        self.selected_keys = set(selected_keys or [])

        for key, item in self.items_by_key.items():
            selected = key in self.selected_keys
            diagnostic_kind = item.data(3)

            if diagnostic_kind == "zero_length_pipe":
                pen = QPen(
                    QColor(235, 60, 60)
                    if selected
                    else QColor(255, 185, 70)
                )
                pen.setCosmetic(True)
                pen.setWidthF(2.6 if selected else 1.8)
                item.setPen(pen)

                for child in item.childItems():
                    if hasattr(child, "setPen"):
                        child_pen = QPen(pen)
                        child_pen.setWidthF(2.0)
                        child.setPen(child_pen)

                item.setZValue(9 if selected else 7)
                continue

            item.setPen(self.make_pen(selected))

            if key[0] != "Pipe":
                if hasattr(item, "setBrush"):
                    item.setBrush(
                        QBrush(
                            QColor(235, 60, 60)
                            if selected
                            else QColor(220, 220, 220)
                        )
                    )
                item.setZValue(4 if selected else 2)
            else:
                item.setZValue(4 if selected else 0)

        self.apply_visibility()

    def zoom_selection(self):
        selected_items = [
            item
            for key, item in self.items_by_key.items()
            if key in self.selected_keys
        ]

        if not selected_items:
            return False

        # Selection must remain discoverable even if a layer or the inactive
        # toggle currently hides it. Reveal selected items for the zoom.
        for item in selected_items:
            item.setVisible(True)

        rect = QRectF()
        for item in selected_items:
            rect = rect.united(item.sceneBoundingRect())

        if not rect.isNull():
            self.view.fitInView(
                rect.adjusted(-10, -10, 10, 10),
                Qt.AspectRatioMode.KeepAspectRatio,
            )
            return True

        return False
