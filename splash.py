import sys
import os
from PyQt5.QtWidgets import (
    QApplication,
    QSplashScreen,
    QProgressBar,
    QLabel,
    QGraphicsDropShadowEffect,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSizePolicy,
)
from PyQt5.QtGui import QPixmap, QColor, QPainter, QLinearGradient, QBrush, QFont
from PyQt5.QtCore import (
    Qt,
    QTimer,
    QPropertyAnimation,
    QEasingCurve,
    QRect,
    QObject,
    pyqtProperty,
)
# Import of VentanaPrincipal is done lazily inside finish() to avoid import cycles


def iniciar_app():
    print("[DEBUG] iniciar_app() started")
    # --- Manual speed control (edit these values in milliseconds to speed/slow the splash) ---
    # BAR_ANIM_DURATION: duration of the progress bar animation (ms)
    # FADE_IN_MS / FADE_OUT_MS: fade in/out durations (ms)
    # DOTS_INTERVAL_MS: interval between dot updates in the "Cargando..." text (ms)
    # FINISH_DELAY_MS: delay after bar finishes before triggering finish (ms)
    BAR_ANIM_DURATION = 9000  # duration of progress bar animation in ms (15000ms = 15s)
    FADE_IN_MS = 1000
    FADE_OUT_MS = 800
    DOTS_INTERVAL_MS = 600
    FINISH_DELAY_MS = 700
    SPLASH_CLOSE_DELAY_MS = 700
    app = QApplication(sys.argv)

    # Crear un pixmap para el splash y pintar un gradiente (control total del tamaño)
    width, height = 720, 360
    pixmap = QPixmap(width, height)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    grad = QLinearGradient(0, 0, width, height)
    # Palette: deeper teal -> mid blue -> soft cyan for a modern look
    grad.setColorAt(0.0, QColor("#052f4f"))
    grad.setColorAt(0.6, QColor("#0e4b66"))
    grad.setColorAt(1.0, QColor("#2b7a8f"))
    painter.fillRect(0, 0, width, height, QBrush(grad))
    card_margin = 40
    card_rect = QRect(card_margin, card_margin, width - card_margin * 2, height - card_margin * 2)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor(255, 255, 255, 28))
    painter.drawRoundedRect(card_rect, 14, 14)
    painter.end()

    splash = QSplashScreen(pixmap)
    splash.setWindowFlag(Qt.FramelessWindowHint)
    splash.setAttribute(Qt.WA_TranslucentBackground, True)

    # Colocar widgets sobre el splash usando un contenedor transparente y layouts
    assets_dir = os.path.join(os.path.dirname(__file__), "assets")
    logo_path_png = os.path.join(assets_dir, "logov1.png")
    logo_pix = QPixmap()
    if os.path.exists(logo_path_png):
        logo_pix.load(logo_path_png)

    # Contenedor transparente que ocupa todo el splash; usaremos layouts para centrar
    container = QWidget(splash)
    container.setAttribute(Qt.WA_TranslucentBackground, True)
    container.setGeometry(0, 0, width, height)

    vbox = QVBoxLayout(container)
    vbox.setContentsMargins(40, 24, 40, 24)
    vbox.setSpacing(10)
    vbox.setAlignment(Qt.AlignCenter)

    # Logo
    logo_label = QLabel()
    logo_label.setParent(container)
    logo_label.setAlignment(Qt.AlignCenter)
    # Slightly larger logo for better aesthetics
    logo_max_w = int(width * 0.32)
    logo_max_h = int(height * 0.32)
    if not logo_pix.isNull():
        logo_scaled = logo_pix.scaled(logo_max_w, logo_max_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        logo_label.setPixmap(logo_scaled)
    else:
        logo_label.setText("")
    logo_shadow = QGraphicsDropShadowEffect()
    logo_shadow.setBlurRadius(18)
    logo_shadow.setOffset(0, 6)
    logo_shadow.setColor(QColor(0, 0, 0, 120))
    logo_label.setGraphicsEffect(logo_shadow)
    vbox.addWidget(logo_label, alignment=Qt.AlignHCenter)

    # Título y subtítulo
    title = QLabel("ComCAD V1")
    title.setParent(container)
    title.setStyleSheet("color: white;")
    tfont = QFont("Segoe UI", 22, QFont.Bold)
    title.setFont(tfont)
    title.setAlignment(Qt.AlignCenter)
    vbox.addWidget(title, alignment=Qt.AlignHCenter)

    subtitle = QLabel("Interfaz de gestión CAD")
    subtitle.setParent(container)
    subtitle.setStyleSheet("color: rgba(255,255,255,0.9);")
    sfont = QFont("Segoe UI", 10)
    subtitle.setFont(sfont)
    subtitle.setAlignment(Qt.AlignCenter)
    vbox.addWidget(subtitle, alignment=Qt.AlignHCenter)

    vbox.addStretch(1)

    # Barra de progreso con porcentaje al lado
    progress = QProgressBar()
    progress.setParent(container)
    progress.setRange(0, 100)
    progress.setValue(0)
    progress.setTextVisible(False)
    progress_h = 12
    progress_w = int(width * 0.62)
    progress.setFixedSize(progress_w, progress_h)
    progress.setStyleSheet(
        "QProgressBar {"
        " background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(255,255,255,0.03), stop:1 rgba(0,0,0,0.06));"
        " border: 1px solid rgba(255,255,255,0.06);"
        " border-radius: 12px;"
        " padding: 2px;"
        "}"
        "QProgressBar::chunk {"
        " border-radius: 12px;"
        " background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6ec1ff, stop:0.5 #a6d8ff, stop:1 #ffffff);"
        " margin: 0px;"
        "}"
    )
    progress_shadow = QGraphicsDropShadowEffect()
    progress_shadow.setBlurRadius(12)
    progress_shadow.setOffset(0, 4)
    progress_shadow.setColor(QColor(0, 0, 0, 100))
    progress.setGraphicsEffect(progress_shadow)

    percent = QLabel("0%")
    percent.setParent(container)
    # Hacer la etiqueta más compacta: misma altura que la barra y fondo transparente
    percent.setFont(QFont("Segoe UI", 9, QFont.Bold))
    percent.setStyleSheet(
        "color: white;"
        " background: transparent;"
        " border-radius: 8px;"
        " padding: 0px 6px;"
    )
    percent.setFixedSize(56, progress_h)
    percent.setAlignment(Qt.AlignCenter)

    hbar = QHBoxLayout()
    hbar.setSpacing(12)
    hbar.setAlignment(Qt.AlignCenter)
    hbar.addWidget(progress, 0, Qt.AlignVCenter)
    hbar.addWidget(percent, 0, Qt.AlignVCenter)
    vbox.addLayout(hbar)

    # Texto de carga debajo de la barra
    loading = QLabel("Cargando")
    loading.setParent(container)
    loading.setStyleSheet("color: rgba(255,255,255,0.9);")
    loading.setFont(QFont("Segoe UI", 9))
    loading.setAlignment(Qt.AlignCenter)
    vbox.addWidget(loading, alignment=Qt.AlignHCenter)

    vbox.addSpacing(6)

    # Fade-in suave
    splash.show()
    print("[DEBUG] splash shown")
    fade = QPropertyAnimation(splash, b"windowOpacity")
    fade.setDuration(FADE_IN_MS)
    fade.setStartValue(0.0)
    fade.setEndValue(1.0)
    fade.setEasingCurve(QEasingCurve.InOutCubic)
    fade.start()
    # Keep a reference so Python GC won't delete the animation
    splash._fade = fade

    # Animación de puntos en el texto de carga
    dot_count = {"n": 0}
    def animate_dots():
        dot_count["n"] = (dot_count["n"] + 1) % 4
        loading.setText("Cargando" + "." * dot_count["n"])
    dots_timer = QTimer()
    dots_timer.timeout.connect(animate_dots)
    dots_timer.start(DOTS_INTERVAL_MS)

    # Animación suave de la barra usando QPropertyAnimation
    class ProgressAnim(QObject):
        def __init__(self, bar, percent_label):
            super().__init__()
            self._value = 0
            self.bar = bar
            self.percent_label = percent_label
        def getValue(self):
            return self._value
        def setValue(self, v):
            self._value = v
            self.bar.setValue(int(v))
            self.percent_label.setText(f"{int(v)}%")
        value = pyqtProperty(float, fget=getValue, fset=setValue)

    anim_obj = ProgressAnim(progress, percent)
    bar_anim = QPropertyAnimation(anim_obj, b"value")
    # Duración controlada por BAR_ANIM_DURATION
    bar_anim.setDuration(BAR_ANIM_DURATION)
    bar_anim.setStartValue(0)
    bar_anim.setEndValue(100)
    bar_anim.setEasingCurve(QEasingCurve.OutCubic)
    bar_anim.start()
    print("[DEBUG] bar_anim started")
    # Keep reference to avoid GC stopping the animation
    splash._bar_anim = bar_anim

    def finish():
        print("[DEBUG] Lanzando VentanaPrincipal...")
        try:
            # Import here to avoid circular imports at module level
            from main import VentanaPrincipal
            ventana = VentanaPrincipal()
            ventana.show()
            print("[DEBUG] VentanaPrincipal mostrada.")
        except Exception as e:
            print(f"[ERROR] No se pudo lanzar VentanaPrincipal: {e}")
            # If the main window fails, just close the splash gracefully
            ventana = None

        fade_out = QPropertyAnimation(splash, b"windowOpacity")
        fade_out.setDuration(FADE_OUT_MS)
        fade_out.setStartValue(1.0)
        fade_out.setEndValue(0.0)
        fade_out.setEasingCurve(QEasingCurve.InOutCubic)
        fade_out.start()
        splash._fade_out = fade_out

        def close_or_finish(win):
            if win:
                splash.finish(win)
            else:
                splash.close()

        QTimer.singleShot(SPLASH_CLOSE_DELAY_MS, lambda: close_or_finish(ventana))

    # Cuando la animación termina, cerrar el splash (con pequeño retraso)
    bar_anim.finished.connect(lambda: QTimer.singleShot(FINISH_DELAY_MS, finish))
    bar_anim.finished.connect(lambda: print("[DEBUG] bar_anim finished"))

    sys.exit(app.exec_())


if __name__ == "__main__":
    iniciar_app()