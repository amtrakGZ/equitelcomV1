import sys
import os
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QLabel,
    QWidget,
    QFrame,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QToolBar,
    QAction,
    QStyle,
    QMessageBox,
    QStatusBar,
    QGraphicsView,
    QGraphicsScene,
    QGraphicsDropShadowEffect,
)
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtCore import Qt


class VentanaPrincipal(QMainWindow):
    """
    Ventana principal estructurada para ComCAD V1.

    Panel izquierdo: acciones y herramientas.
    Centro: QGraphicsView (para cargar DWG/PDF) con una tarjeta (card) placeholder.
    Panel derecho: inspector / propiedades (placeholder).
    Barra inferior: status bar con coordenadas / contador / archivo.
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("ComCAD V1_Equitelcom")
        self.setMinimumSize(1000, 700)
        self.resize(1400, 900)

        # Cargar stylesheet si existe
        self._cargar_stylesheet()

        # Toolbar
        self._crear_toolbar()

        # Crear layout principal con splitter
        self._crear_layout_principal()

        # Status bar
        self._crear_statusbar()

    # ------------------ Secciones de construcción UI ------------------ #
    def _cargar_stylesheet(self):
        try:
            base = os.path.dirname(os.path.abspath(__file__))
            css_path = os.path.join(base, "styles.css")
            if os.path.isfile(css_path):
                with open(css_path, "r", encoding="utf-8") as f:
                    self.setStyleSheet(f.read())
        except Exception:
            # Silencioso: si falla no es crítico
            pass

    def _crear_toolbar(self):
        toolbar = QToolBar("Main")
        toolbar.setMovable(False)
        self.addToolBar(Qt.TopToolBarArea, toolbar)

        act_abrir = QAction(self.style().standardIcon(QStyle.SP_DialogOpenButton), "Abrir", self)
        act_nuevo = QAction(self.style().standardIcon(QStyle.SP_FileIcon), "Nuevo", self)
        act_guardar = QAction(self.style().standardIcon(QStyle.SP_DialogSaveButton), "Guardar", self)

        # Placeholder de acciones
        act_abrir.triggered.connect(lambda: self.statusBar().showMessage("Abrir (pendiente)", 3000))
        act_nuevo.triggered.connect(lambda: self.statusBar().showMessage("Nuevo (pendiente)", 3000))
        act_guardar.triggered.connect(lambda: self.statusBar().showMessage("Guardar (pendiente)", 3000))

        toolbar.addAction(act_abrir)
        toolbar.addAction(act_nuevo)
        toolbar.addAction(act_guardar)

    def _crear_layout_principal(self):
        main_widget = QWidget(self)
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(8, 8, 8, 8)

        splitter = QSplitter(Qt.Horizontal)

        # Panel izquierdo
        left_frame = self._crear_panel_izquierdo()

        # Centro
        center_frame = self._crear_panel_central()

        # Panel derecho
        right_frame = self._crear_panel_derecho()

        splitter.addWidget(left_frame)
        splitter.addWidget(center_frame)
        splitter.addWidget(right_frame)

        # Que el panel central se expanda
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)

        main_layout.addWidget(splitter)
        self.setCentralWidget(main_widget)

    def _crear_panel_izquierdo(self):
        frame = QFrame()
        frame.setObjectName("leftPanel")
        frame.setFixedWidth(200)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        self.btn_open = QPushButton("Abrir plano")
        self.btn_insert = QPushButton("Insertar símbolo")
        self.btn_draw = QPushButton("Dibujar canalización")
        self.btn_report = QPushButton("Generar reporte")

        botones = (self.btn_open, self.btn_insert, self.btn_draw, self.btn_report)
        for b in botones:
            b.setMinimumHeight(44)
            layout.addWidget(b)

        layout.addStretch()

        # Íconos y señales
        self.btn_open.setIcon(self.style().standardIcon(QStyle.SP_DialogOpenButton))
        self.btn_insert.setIcon(self.style().standardIcon(QStyle.SP_BrowserReload))
        self.btn_draw.setIcon(self.style().standardIcon(QStyle.SP_ArrowRight))
        self.btn_report.setIcon(self.style().standardIcon(QStyle.SP_FileDialogDetailedView))

        self.btn_open.clicked.connect(self._on_open)
        self.btn_insert.clicked.connect(self._on_insert)
        self.btn_draw.clicked.connect(self._on_draw)
        self.btn_report.clicked.connect(self._on_report)

        return frame

    def _crear_panel_central(self):
        frame = QFrame()
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        # Card superior
        card = QWidget()
        card.setObjectName("card")
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(12, 12, 12, 12)

        lbl_title = QLabel("ComCAD V1")
        font = QFont()
        font.setPointSize(20)
        font.setBold(True)
        lbl_title.setFont(font)

        lbl_sub = QLabel("Área principal - carga de planos y edición")

        card_layout.addWidget(lbl_title)
        card_layout.addStretch()
        card_layout.addWidget(lbl_sub)

        # Sombra
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(18)
        shadow.setOffset(0, 6)
        shadow.setColor(QColor(0, 0, 0, 55))
        card.setGraphicsEffect(shadow)

        # GraphicsView
        self.graphics_view = QGraphicsView()
        self.graphics_view.setObjectName("graphicsView")
        self.graphics_view.setStyleSheet("background: #ffffff; border: 1px solid #ddd;")

        self.scene = QGraphicsScene(self)
        self.graphics_view.setScene(self.scene)

        layout.addWidget(card)
        layout.addWidget(self.graphics_view, 1)

        return frame

    def _crear_panel_derecho(self):
        frame = QFrame()
        frame.setObjectName("rightPanel")
        frame.setFixedWidth(300)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        layout.addWidget(QLabel("Inspector / Propiedades"))
        layout.addStretch()

        return frame

    def _crear_statusbar(self):
        status = QStatusBar(self)
        self.setStatusBar(status)
        self.coords_label = QLabel("Coordenadas: -, -")
        self.items_label = QLabel("Elementos: 0")
        self.file_label = QLabel("Archivo: ninguno")
        status.addWidget(self.coords_label)
        status.addPermanentWidget(self.items_label)
        status.addPermanentWidget(self.file_label)

    # ------------------ Handlers (placeholders) ------------------ #
    def _on_open(self):
        self.statusBar().showMessage("Abrir plano (pendiente)", 3000)

    def _on_insert(self):
        self.statusBar().showMessage("Insertar símbolo (pendiente)", 3000)

    def _on_draw(self):
        self.statusBar().showMessage("Dibujar canalización (pendiente)", 3000)

    def _on_report(self):
        self.statusBar().showMessage("Generar reporte (pendiente)", 3000)

    # ------------------ Eventos ------------------ #
    def closeEvent(self, event):
        dlg = QMessageBox(self)
        dlg.setWindowTitle("Confirmar cierre")
        dlg.setText("¿Está seguro de que desea cerrar la ventana?")
        dlg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        yes_btn = dlg.button(QMessageBox.Yes)
        if yes_btn:
            yes_btn.setText("Sí")
        no_btn = dlg.button(QMessageBox.No)
        if no_btn:
            no_btn.setText("No")

        ret = dlg.exec_()
        if ret == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ventana = VentanaPrincipal()
    ventana.show()
    sys.exit(app.exec_())