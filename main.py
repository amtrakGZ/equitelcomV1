import sys
import os
from enum import Enum, auto

from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QLabel,
    QWidget,
    QPushButton,
    QVBoxLayout,
    QToolBar,
    QAction,
    QStyle,
    QMessageBox,
    QStatusBar,
    QGraphicsView,
    QGraphicsScene,
    QDockWidget,
    QSizePolicy,
    QGraphicsLineItem,
    QGraphicsEllipseItem,
)
from PyQt5.QtGui import (
    QFont,
    QColor,
    QPainter,
    QPen,
    QCursor,
    QPixmap,
    QLinearGradient,
)
from PyQt5.QtCore import (
    Qt,
    QPointF,
    QRectF,
    pyqtSignal,
    QTimer,
    QLineF,
)


# ================== Configuración Colores / Recursos ================== #
RESOURCE_LOGO = "assets/logov1.png"
COLOR_BG_WORKAREA = QColor("#161b1f")
COLOR_GRID_MINOR = QColor(55, 70, 78)
COLOR_GRID_MAJOR = QColor(74, 105, 116)
COLOR_SNAP = QColor(0, 200, 255)
COLOR_CROSSHAIR = QColor(200, 210, 215, 190)


class SnapMode(Enum):
    NONE = auto()
    GRID = auto()


# ================== Vista de Dibujo Optimizada ================== #
class DrawingView(QGraphicsView):
    """
    Optimizada:
    - SmartViewportUpdate (no repintar todo cada movimiento)
    - Sin viewport().update() en mouse move
    - Crosshair y snap marker como QGraphicsItems (redraw parcial)
    """

    mouseMoved = pyqtSignal(float, float, bool, float, float)  # x_snapped, y_snapped, snapped, raw_x, raw_y

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setRenderHints(
            QPainter.Antialiasing
            | QPainter.SmoothPixmapTransform
            | QPainter.TextAntialiasing
        )
        self.setViewportUpdateMode(QGraphicsView.SmartViewportUpdate)
        self.setDragMode(QGraphicsView.NoDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self.setBackgroundBrush(COLOR_BG_WORKAREA)
        self.setMouseTracking(True)
        self.setCursor(QCursor(Qt.CrossCursor))

        # Grid
        self.grid_minor = 25
        self.grid_major_factor = 5
        self.grid_color_minor = COLOR_GRID_MINOR
        self.grid_color_major = COLOR_GRID_MAJOR

        # Snaps
        self.snap_enabled = True
        self.snap_mode = SnapMode.GRID
        self.snap_tolerance_pixels = 14
        self._snap_point = None

        # Crosshair state
        self._show_crosshair = True
        self._crosshair_pos = QPointF(0, 0)

        # Crosshair items (dos líneas)
        self._h_line_item = QGraphicsLineItem()
        self._v_line_item = QGraphicsLineItem()
        pen_cross = QPen(COLOR_CROSSHAIR, 0)
        self._h_line_item.setPen(pen_cross)
        self._v_line_item.setPen(pen_cross)
        self._h_line_item.setZValue(10_000)
        self._v_line_item.setZValue(10_000)

        # Snap marker item
        self._snap_item = QGraphicsEllipseItem(-6, -6, 12, 12)
        pen_snap = QPen(COLOR_SNAP, 2)
        self._snap_item.setPen(pen_snap)
        self._snap_item.setBrush(COLOR_SNAP)
        self._snap_item.setZValue(10_001)
        self._snap_item.setVisible(False)

        # Logo overlay (QLabel sobre viewport)
        self._logo_label = None
        QTimer.singleShot(0, self._init_logo_overlay)

    # -------------- Scene assignment override para añadir items crosshair/snap -------------- #
    def setScene(self, scene: QGraphicsScene):
        super().setScene(scene)
        if scene:
            # Añadimos los items especiales a la escena una sola vez
            scene.addItem(self._h_line_item)
            scene.addItem(self._v_line_item)
            scene.addItem(self._snap_item)

    # -------------- Logo overlay -------------- #
    def _init_logo_overlay(self):
        if self._logo_label:
            return
        parent = self.viewport()
        self._logo_label = QLabel(parent)
        logo_path = self._resolve_logo_path()
        if os.path.isfile(logo_path):
            pm = QPixmap(logo_path)
            if not pm.isNull():
                scaled = pm.scaledToWidth(180, Qt.SmoothTransformation)
                self._logo_label.setPixmap(scaled)
        self._logo_label.setStyleSheet("background: transparent;")
        self._logo_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._reposition_logo()

    def _resolve_logo_path(self):
        base = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base, RESOURCE_LOGO)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reposition_logo()
        self._update_crosshair_lines()

    def _reposition_logo(self):
        if self._logo_label:
            self._logo_label.move(14, 14)

    # -------------- Grid (drawBackground optimizado) -------------- #
    def drawBackground(self, painter: QPainter, rect: QRectF):
        # Importante: NO llamamos a super().drawBackground para evitar repintado extra
        painter.fillRect(rect, COLOR_BG_WORKAREA)

        start_x = int(rect.left()) - (int(rect.left()) % self.grid_minor)
        start_y = int(rect.top()) - (int(rect.top()) % self.grid_minor)

        pen_minor = QPen(self.grid_color_minor, 0)
        pen_major = QPen(self.grid_color_major, 0)

        # Verticales
        x = start_x
        idx = 0
        right = rect.right()
        bottom = rect.bottom()
        top = rect.top()
        while x <= right:
            painter.setPen(pen_major if (idx % self.grid_major_factor) == 0 else pen_minor)
            painter.drawLine(QLineF(x, top, x, bottom))
            x += self.grid_minor
            idx += 1

        # Horizontales
        y = start_y
        idy = 0
        left = rect.left()
        while y <= bottom:
            painter.setPen(pen_major if (idy % self.grid_major_factor) == 0 else pen_minor)
            painter.drawLine(QLineF(left, y, right, y))
            y += self.grid_minor
            idy += 1

    # -------------- Crosshair / Snap item updates -------------- #
    def _update_crosshair_lines(self):
        if not self._show_crosshair or self.scene() is None:
            self._h_line_item.setVisible(False)
            self._v_line_item.setVisible(False)
            return

        # Determinar límites visibles en coordenadas de escena
        view_rect = self.viewport().rect()
        top_left = self.mapToScene(view_rect.topLeft())
        bottom_right = self.mapToScene(view_rect.bottomRight())

        x = self._crosshair_pos.x()
        y = self._crosshair_pos.y()

        self._h_line_item.setLine(QLineF(top_left.x(), y, bottom_right.x(), y))
        self._v_line_item.setLine(QLineF(x, top_left.y(), x, bottom_right.y()))
        self._h_line_item.setVisible(True)
        self._v_line_item.setVisible(True)

    def _update_snap_item(self):
        if self._snap_point and self.snap_enabled:
            self._snap_item.setPos(self._snap_point)
            self._snap_item.setVisible(True)
        else:
            self._snap_item.setVisible(False)

    # -------------- Eventos del ratón / zoom -------------- #
    def mouseMoveEvent(self, event):
        scene_pos = self.mapToScene(event.pos())
        raw_x, raw_y = scene_pos.x(), scene_pos.y()

        snapped = False
        snap_point = None

        if self.snap_enabled and self.snap_mode == SnapMode.GRID:
            snap_point = self._grid_snap(scene_pos)
            if snap_point is not None:
                view_snap = self.mapFromScene(snap_point)
                dist = (view_snap - event.pos())
                # Distancia manhattan (suficiente y más barata que sqrt)
                if dist.manhattanLength() <= self.snap_tolerance_pixels:
                    snapped = True
                else:
                    snap_point = None

        if snapped:
            self._snap_point = snap_point
            self._crosshair_pos = snap_point
            x_out, y_out = snap_point.x(), snap_point.y()
        else:
            self._snap_point = None
            self._crosshair_pos = scene_pos
            x_out, y_out = raw_x, raw_y

        self._update_crosshair_lines()
        self._update_snap_item()
        self.mouseMoved.emit(x_out, y_out, snapped, raw_x, raw_y)

        # NOTA: No llamamos a viewport().update() -> evita repintado completo
        super().mouseMoveEvent(event)

    def wheelEvent(self, event):
        factor = 1.15 if event.angleDelta().y() > 0 else (1 / 1.15)
        self.scale(factor, factor)
        self._update_crosshair_lines()
        super().wheelEvent(event)

    def toggle_crosshair(self, value: bool):
        self._show_crosshair = value
        self._update_crosshair_lines()

    def set_snap_enabled(self, enabled: bool):
        self.snap_enabled = enabled
        if not enabled:
            self._snap_point = None
        self._update_snap_item()

    def set_snap_mode(self, mode: SnapMode):
        self.snap_mode = mode
        self._update_snap_item()

    # -------------- Snapping -------------- #
    def _grid_snap(self, point: QPointF) -> QPointF:
        gx = round(point.x() / self.grid_minor) * self.grid_minor
        gy = round(point.y() / self.grid_minor) * self.grid_minor
        return QPointF(gx, gy)


# ================== Ventana Principal ================== #
class VentanaPrincipal(QMainWindow):
    """
    Versión optimizada:
    - Menos repaints: SmartViewportUpdate
    - Sin full redraw por crosshair
    - Items en escena para crosshair & snap
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("ComCAD V1_Equitelcom")
        self.setMinimumSize(1100, 720)
        self.resize(1400, 860)

        self._cargar_stylesheet()
        self._crear_centro()
        self._crear_docks()
        self._crear_toolbar()
        self._crear_statusbar()
        self._conectar_signals()

    # -------- Estilos -------- #
    def _cargar_stylesheet(self):
        base = os.path.dirname(os.path.abspath(__file__))
        css_path = os.path.join(base, "styles.css")
        if os.path.isfile(css_path):
            try:
                with open(css_path, "r", encoding="utf-8") as f:
                    self.setStyleSheet(f.read())
            except Exception:
                self.setStyleSheet("QMainWindow { background:#0d4d63; }")
        else:
            self.setStyleSheet("QMainWindow { background:#0d4d63; }")

    # -------- Centro -------- #
    def _crear_centro(self):
        self.scene = QGraphicsScene(self)
        # Reducimos área inicial (puedes ampliarla bajo demanda)
        self.scene.setSceneRect(-3000, -3000, 6000, 6000)

        self.graphics_view = DrawingView()
        self.graphics_view.setScene(self.scene)
        self.graphics_view.setObjectName("graphicsView")
        self.setCentralWidget(self.graphics_view)
        self.graphics_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    # -------- Docks -------- #
    def _crear_docks(self):
        # Izquierdo
        self.dock_left = QDockWidget("Herramientas", self)
        self.dock_left.setObjectName("dockLeft")
        self.dock_left.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.dock_left.setFeatures(QDockWidget.AllDockWidgetFeatures)

        left_container = QWidget()
        lay = QVBoxLayout(left_container)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(10)

        self.btn_open = QPushButton("Abrir plano")
        self.btn_insert = QPushButton("Insertar símbolo")
        self.btn_draw = QPushButton("Dibujar canalización")
        self.btn_report = QPushButton("Generar reporte")
        for b in (self.btn_open, self.btn_insert, self.btn_draw, self.btn_report):
            b.setMinimumHeight(40)
            lay.addWidget(b)
        lay.addStretch()
        self.dock_left.setWidget(left_container)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.dock_left)

        # Derecho
        self.dock_right = QDockWidget("Propiedades", self)
        self.dock_right.setObjectName("dockRight")
        self.dock_right.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.dock_right.setFeatures(QDockWidget.AllDockWidgetFeatures)

        right_container = QWidget()
        rlay = QVBoxLayout(right_container)
        rlay.setContentsMargins(10, 10, 10, 10)
        rlay.setSpacing(10)
        lbl_prop = QLabel("Inspector / Propiedades")
        f = QFont()
        f.setBold(True)
        lbl_prop.setFont(f)
        rlay.addWidget(lbl_prop)
        rlay.addStretch()
        self.dock_right.setWidget(right_container)
        self.addDockWidget(Qt.RightDockWidgetArea, self.dock_right)

    # -------- Toolbar -------- #
    def _crear_toolbar(self):
        tb = QToolBar("Principal")
        tb.setObjectName("mainToolbar")
        tb.setMovable(False)
        self.addToolBar(Qt.TopToolBarArea, tb)

        act_abrir = QAction(self.style().standardIcon(QStyle.SP_DialogOpenButton), "Abrir", self)
        act_nuevo = QAction(self.style().standardIcon(QStyle.SP_FileIcon), "Nuevo", self)
        act_guardar = QAction(self.style().standardIcon(QStyle.SP_DialogSaveButton), "Guardar", self)

        act_zoom_in = QAction("Zoom +", self)
        act_zoom_out = QAction("Zoom -", self)
        act_fit = QAction("Ajustar", self)

        act_crosshair = QAction("Crosshair", self)
        act_crosshair.setCheckable(True)
        act_crosshair.setChecked(True)

        act_snap_enable = QAction("Snap", self)
        act_snap_enable.setCheckable(True)
        act_snap_enable.setChecked(True)

        act_snap_grid = QAction("Grid Snap", self)
        act_snap_grid.setCheckable(True)
        act_snap_grid.setChecked(True)

        act_toggle_left = QAction("Panel Izq", self)
        act_toggle_left.setCheckable(True)
        act_toggle_left.setChecked(True)
        act_toggle_right = QAction("Panel Der", self)
        act_toggle_right.setCheckable(True)
        act_toggle_right.setChecked(True)

        for a in (act_abrir, act_nuevo, act_guardar):
            tb.addAction(a)
        tb.addSeparator()
        for a in (act_zoom_in, act_zoom_out, act_fit):
            tb.addAction(a)
        tb.addSeparator()
        tb.addAction(act_crosshair)
        tb.addSeparator()
        tb.addAction(act_snap_enable)
        tb.addAction(act_snap_grid)
        tb.addSeparator()
        tb.addAction(act_toggle_left)
        tb.addAction(act_toggle_right)

        # Referencias
        self.act_zoom_in = act_zoom_in
        self.act_zoom_out = act_zoom_out
        self.act_fit = act_fit
        self.act_crosshair = act_crosshair
        self.act_snap_enable = act_snap_enable
        self.act_snap_grid = act_snap_grid
        self.act_toggle_left = act_toggle_left
        self.act_toggle_right = act_toggle_right

        # Placeholders
        act_abrir.triggered.connect(lambda: self.statusBar().showMessage("Abrir plano (pendiente)", 3000))
        act_nuevo.triggered.connect(lambda: self.statusBar().showMessage("Nuevo (pendiente)", 3000))
        act_guardar.triggered.connect(lambda: self.statusBar().showMessage("Guardar (pendiente)", 3000))

    # -------- Status Bar -------- #
    def _crear_statusbar(self):
        status = QStatusBar(self)
        self.setStatusBar(status)
        self.coords_label = QLabel("X: 0.000  Y: 0.000 (snap)")
        self.raw_label = QLabel("Raw: 0.000, 0.000")
        self.items_label = QLabel("Elementos: 0")
        self.file_label = QLabel("Archivo: ninguno")
        status.addWidget(self.coords_label)
        status.addWidget(self.raw_label)
        status.addPermanentWidget(self.items_label)
        status.addPermanentWidget(self.file_label)

    # -------- Conexiones -------- #
    def _conectar_signals(self):
        self.graphics_view.mouseMoved.connect(self._on_mouse_moved)

        self.btn_open.clicked.connect(self._on_open)
        self.btn_insert.clicked.connect(self._on_insert)
        self.btn_draw.clicked.connect(self._on_draw)
        self.btn_report.clicked.connect(self._on_report)

        self.act_zoom_in.triggered.connect(lambda: self._zoom(1.15))
        self.act_zoom_out.triggered.connect(lambda: self._zoom(1 / 1.15))
        self.act_fit.triggered.connect(self._fit_to_content)
        self.act_crosshair.toggled.connect(self.graphics_view.toggle_crosshair)
        self.act_snap_enable.toggled.connect(self.graphics_view.set_snap_enabled)
        self.act_snap_grid.toggled.connect(self._on_snap_grid_toggled)
        self.act_toggle_left.toggled.connect(lambda c: self.dock_left.setVisible(c))
        self.act_toggle_right.toggled.connect(lambda c: self.dock_right.setVisible(c))

    # -------- Gradiente de la ventana (no impacta mouse move) -------- #
    def paintEvent(self, event):
        painter = QPainter(self)
        grad = QLinearGradient(0, 0, self.width(), self.height())
        grad.setColorAt(0.0, QColor("#0b3446"))
        grad.setColorAt(0.35, QColor("#0d4d63"))
        grad.setColorAt(1.0, QColor("#0e5d73"))
        painter.fillRect(self.rect(), grad)
        super().paintEvent(event)

    # -------- Funciones utilitarias -------- #
    def _zoom(self, factor: float):
        self.graphics_view.scale(factor, factor)
        self.graphics_view._update_crosshair_lines()

    def _fit_to_content(self):
        if self.scene.items():
            self.graphics_view.fitInView(self.scene.itemsBoundingRect(), Qt.KeepAspectRatio)
        else:
            self.graphics_view.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)
        self.graphics_view._update_crosshair_lines()

    def _on_snap_grid_toggled(self, checked: bool):
        self.graphics_view.set_snap_mode(SnapMode.GRID if checked else SnapMode.NONE)

    # -------- Placeholders acciones -------- #
    def _on_open(self):
        self.statusBar().showMessage("Abrir plano (pendiente)", 3000)

    def _on_insert(self):
        self.statusBar().showMessage("Insertar símbolo (pendiente)", 3000)

    def _on_draw(self):
        self.statusBar().showMessage("Dibujar canalización (pendiente)", 3000)

    def _on_report(self):
        self.statusBar().showMessage("Generar reporte (pendiente)", 3000)

    def _on_mouse_moved(self, x, y, snapped, raw_x, raw_y):
        if snapped:
            self.coords_label.setText(f"X: {x:,.3f}  Y: {y:,.3f} (snap)")
        else:
            self.coords_label.setText(f"X: {x:,.3f}  Y: {y:,.3f}")
        self.raw_label.setText(f"Raw: {raw_x:,.3f}, {raw_y:,.3f}")

    # -------- Diálogo de cierre -------- #
    def closeEvent(self, event):
        dlg = QMessageBox(self)
        dlg.setObjectName("closeConfirm")
        dlg.setWindowTitle("Confirmar cierre")
        dlg.setText("¿Desea cerrar ComCAD V1?")
        dlg.setInformativeText("Se perderán los cambios no guardados.")
        dlg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        dlg.setDefaultButton(QMessageBox.No)

        yes_btn = dlg.button(QMessageBox.Yes)
        no_btn = dlg.button(QMessageBox.No)
        if yes_btn:
            yes_btn.setText("Sí")
        if no_btn:
            no_btn.setText("No")

        dlg.setStyleSheet("""
        QMessageBox#closeConfirm {
            background-color: #103949;
            border: 1px solid #19a7d8;
            border-radius: 10px;
        }
        QMessageBox#closeConfirm QLabel {
            color: #eaf7fb;
            font-size: 14px;
        }
        QMessageBox#closeConfirm QPushButton {
            background: #0f6f90;
            color: #e8f8fc;
            border: 1px solid #1093c0;
            padding: 6px 14px;
            border-radius: 6px;
            min-width: 80px;
            font-weight: 600;
        }
        QMessageBox#closeConfirm QPushButton:hover {
            background: #129fd1;
        }
        QMessageBox#closeConfirm QPushButton:pressed {
            background: #0b5d78;
        }
        """)

        ret = dlg.exec_()
        if ret == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()


def main():
    app = QApplication(sys.argv)
    win = VentanaPrincipal()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
    