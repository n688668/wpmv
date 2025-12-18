import sys
import os
import time

try:
    from PyQt6.QtWidgets import (QApplication, QMainWindow, QFileDialog, QWidget, QVBoxLayout,
                                 QHBoxLayout, QPushButton, QLabel, QSlider, QStyle, QGraphicsView,
                                 QGraphicsScene, QGraphicsPixmapItem, QStackedWidget, QComboBox,
                                 QFrame)
    from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
    from PyQt6.QtMultimediaWidgets import QGraphicsVideoItem
    from PyQt6.QtCore import Qt, QUrl, QTimer, QRectF, QEvent, QStandardPaths, pyqtSignal, QPoint, QSize
    from PyQt6.QtGui import (QPixmap, QPalette, QColor, QWheelEvent, QKeyEvent, QPainter,
                             QMovie, QKeySequence, QImage, QAction, QIcon, QPen, QBrush, QPolygonF)
    from PyQt6.QtPrintSupport import QPrinter, QPrintDialog
except ImportError:
    print("Vui lòng cài đặt đầy đủ: pip install PyQt6 PyQt6-Qt6 PyQt6-QtMultimedia")
    sys.exit(1)

class ClickableSlider(QSlider):
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            new_value = self.minimum() + ((self.maximum() - self.minimum()) * event.position().x()) / self.width()
            self.setValue(int(new_value))
            self.sliderMoved.emit(self.value())
            event.accept()
        super().mousePressEvent(event)

class CustomGraphicsView(QGraphicsView):
    clicked = pyqtSignal()

    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setBackgroundBrush(QColor(30, 30, 30))
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._mouse_press_pos = QPoint()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._mouse_press_pos = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if (event.position().toPoint() - self._mouse_press_pos).manhattanLength() < 5:
                self.clicked.emit()
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event: QWheelEvent):
        zoom_in_factor = 1.25
        zoom_out_factor = 1 / zoom_in_factor
        zoom_factor = zoom_in_factor if event.angleDelta().y() > 0 else zoom_out_factor
        self.scale(zoom_factor, zoom_factor)

class ClickableLabel(QLabel):
    clicked = pyqtSignal()
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

class UniversalViewer(QMainWindow):
    def __init__(self):
        super().__init__()

        self.base_title = "WPMV Player"
        self.setWindowTitle(self.base_title)
        self.setGeometry(100, 100, 1100, 800)

        # --- THIẾT LẬP ICON ---
        self.set_app_icon()

        self.set_dark_theme()
        self.duration = 0
        self.current_file_path = ""
        self.playlist = []

        # --- GIAO DIỆN CHÍNH ---
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.stack = QStackedWidget()

        # Xem Ảnh / GIF
        self.image_scene = QGraphicsScene()
        self.image_view = CustomGraphicsView(self.image_scene)
        self.image_item = None
        self.movie = None
        self.image_view.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.stack.addWidget(self.image_view)

        # Xem Video/Nhạc
        self.video_container = QWidget()
        self.video_layout = QVBoxLayout(self.video_container)
        self.video_layout.setContentsMargins(0,0,0,0)
        self.video_scene = QGraphicsScene()
        self.video_view = CustomGraphicsView(self.video_scene)
        self.video_view.setStyleSheet("background-color: black;")
        self.video_view.clicked.connect(self.play_video)
        self.video_item = QGraphicsVideoItem()
        self.video_scene.addItem(self.video_item)
        self.music_label = QLabel("AUDIO MODE 🎵")
        self.music_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.music_label.setStyleSheet("background-color: #222; color: #aaa; font-size: 20px; font-weight: bold; padding: 20px;")
        self.music_label.hide()
        self.video_layout.addWidget(self.video_view)
        self.video_layout.addWidget(self.music_label)
        self.stack.addWidget(self.video_container)

        # Màn hình chờ
        self.placeholder = ClickableLabel(
            "WPMV PLAYER\n\n"
            "Nhấn 'O' hoặc click vào đây để mở file\n"
            "(Hỗ trợ Ảnh, GIF, Video, Audio)\n\n"
            "*** 2025 - dongt6140@gmail.com ***"
        )
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder.setStyleSheet("font-size: 18px; color: #888; border: 2px dashed #444; margin: 20px;")
        self.placeholder.setCursor(Qt.CursorShape.PointingHandCursor)
        self.placeholder.clicked.connect(self.open_file)
        self.stack.addWidget(self.placeholder)

        self.stack.setCurrentIndex(2)
        self.main_layout.addWidget(self.stack)

        # --- THANH ĐIỀU KHIỂN ---
        self.setup_controls()

        # Media Player
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.audio_output.setVolume(0.7)
        self.media_player.setAudioOutput(self.audio_output)
        self.media_player.setVideoOutput(self.video_item)
        self.media_player.playbackStateChanged.connect(self.media_state_changed)
        self.media_player.positionChanged.connect(self.position_changed)
        self.media_player.durationChanged.connect(self.duration_changed)
        self.media_player.errorOccurred.connect(self.handle_errors)

        if len(sys.argv) > 1:
            file_to_open = sys.argv[1]
            QTimer.singleShot(200, lambda: self.load_content(file_to_open))

    def set_app_icon(self):
        """Thiết lập biểu tượng cho ứng dụng"""
        icon_path = os.path.join(os.path.dirname(__file__), "icon.ico")

        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        else:
            # Tạo icon tạm thời bằng code nếu không có file icon.ico
            pixmap = QPixmap(256, 256)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            # Vẽ nền tròn xanh
            painter.setBrush(QBrush(QColor("#0078d7")))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(10, 10, 236, 236)

            # Vẽ hình tam giác Play trắng
            painter.setBrush(QBrush(Qt.GlobalColor.white))
            triangle = QPolygonF([
                QPoint(85, 70),
                QPoint(85, 186),
                QPoint(190, 128)
            ])
            painter.drawPolygon(triangle)
            painter.end()

            self.setWindowIcon(QIcon(pixmap))

    def setup_controls(self):
        self.controls_layout = QVBoxLayout()
        self.main_layout.addLayout(self.controls_layout)

        # MEDIA CONTROLS
        self.media_controls = QWidget()
        self.media_v_layout = QVBoxLayout(self.media_controls)
        self.media_v_layout.setContentsMargins(0, 0, 0, 0)
        self.slider_seek = ClickableSlider(Qt.Orientation.Horizontal)
        self.slider_seek.sliderMoved.connect(self.set_position)
        self.media_v_layout.addWidget(self.slider_seek)
        self.media_h_layout = QHBoxLayout()
        self.media_v_layout.addLayout(self.media_h_layout)

        def create_seek_btn(text, delta):
            btn = QPushButton(text)
            btn.setFixedWidth(40)
            btn.clicked.connect(lambda: self.seek_relative(delta))
            return btn

        self.btn_play = QPushButton()
        self.btn_play.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.btn_play.clicked.connect(self.play_video)
        self.btn_play.setFixedWidth(45)

        self.btn_screenshot = QPushButton()
        self.btn_screenshot.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView))
        self.btn_screenshot.clicked.connect(self.take_screenshot)
        self.btn_screenshot.setFixedWidth(35)

        self.btn_mute = QPushButton()
        self.btn_mute.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaVolume))
        self.btn_mute.clicked.connect(self.toggle_mute)
        self.btn_mute.setFixedWidth(35)

        self.slider_vol = QSlider(Qt.Orientation.Horizontal)
        self.slider_vol.setRange(0, 100)
        self.slider_vol.setValue(70)
        self.slider_vol.setFixedWidth(70)
        self.slider_vol.valueChanged.connect(self.set_volume)

        self.combo_speed = QComboBox()
        self.combo_speed.addItems(["x0.5", "x1.0", "x1.5", "x1.7", "x2.0"])
        self.combo_speed.setCurrentIndex(1)
        self.combo_speed.setFixedWidth(60)
        self.combo_speed.currentIndexChanged.connect(self.set_speed)

        self.media_h_layout.addWidget(create_seek_btn("-1m", -60000))
        self.media_h_layout.addWidget(create_seek_btn("-10s", -10000))
        self.media_h_layout.addWidget(self.btn_play)
        self.media_h_layout.addWidget(create_seek_btn("+10s", 10000))
        self.media_h_layout.addWidget(create_seek_btn("+1m", 60000))
        self.media_h_layout.addStretch()
        self.media_h_layout.addWidget(self.btn_screenshot)
        self.media_h_layout.addWidget(self.btn_mute)
        self.media_h_layout.addWidget(self.slider_vol)
        self.media_h_layout.addWidget(self.combo_speed)

        # IMAGE CONTROLS
        self.image_controls = QWidget()
        self.img_layout = QHBoxLayout(self.image_controls)
        self.img_layout.setContentsMargins(0, 0, 0, 0)

        btns = [
            ("Zoom +", lambda: self.zoom_content(1.25)),
            ("Zoom -", lambda: self.zoom_content(0.8)),
            ("Xoay Trái", lambda: self.rotate_content(-90)),
            ("Xoay Phải", lambda: self.rotate_content(90)),
            ("Lật Ngang", self.flip_horizontal),
            ("In Ảnh", self.open_print_dialog)
        ]
        for txt, cmd in btns:
            b = QPushButton(txt)
            b.clicked.connect(cmd)
            self.img_layout.addWidget(b)

        self.controls_layout.addWidget(self.media_controls)
        self.controls_layout.addWidget(self.image_controls)

        self.bottom_bar = QHBoxLayout()
        self.controls_layout.addLayout(self.bottom_bar)
        self.btn_open = QPushButton("Mở File (O)")
        self.btn_open.clicked.connect(self.open_file)
        self.btn_open.setStyleSheet("background-color: #0078d7; color: white; font-weight: bold; padding: 8px;")

        self.btn_prev = QPushButton("< Trước")
        self.btn_prev.clicked.connect(self.open_prev_file)
        self.btn_next = QPushButton("Sau >")
        self.btn_next.clicked.connect(self.open_next_file)

        self.bottom_bar.addWidget(self.btn_open, 2)
        self.bottom_bar.addWidget(self.btn_prev, 1)
        self.bottom_bar.addWidget(self.btn_next, 1)

        self.media_controls.hide()
        self.image_controls.hide()

    def take_screenshot(self):
        if self.stack.currentIndex() != 1: return
        try:
            pixmap = self.video_view.grab()
            save_path = os.path.join(os.path.dirname(self.current_file_path), f"cap_{int(time.time())}.jpg")
            pixmap.save(save_path, "JPG")
        except: pass

    def display_error(self, message):
        self.stack.setCurrentIndex(2)
        self.placeholder.setText(f"⚠️ LỖI: {message}")

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_O: self.open_file()
        elif event.key() == Qt.Key.Key_Space and self.stack.currentIndex() == 1: self.play_video()
        super().keyPressEvent(event)

    def set_dark_theme(self):
        p = QPalette()
        p.setColor(QPalette.ColorRole.Window, QColor(45, 45, 45))
        p.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
        p.setColor(QPalette.ColorRole.Button, QColor(60, 60, 60))
        p.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
        p.setColor(QPalette.ColorRole.Base, QColor(30, 30, 30))
        self.setPalette(p)

    def open_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Mở Media", "", "Files (*.png *.jpg *.gif *.mp4 *.mkv *.mp3 *.wav)")
        if path: self.load_content(path)

    def update_playlist(self, current_file):
        try:
            folder = os.path.dirname(current_file)
            self.current_file_path = os.path.normpath(current_file)
            exts = {'.png', '.jpg', '.jpeg', '.gif', '.mp4', '.avi', '.mkv', '.mp3', '.wav'}
            self.playlist = sorted([os.path.normpath(os.path.join(folder, f)) for f in os.listdir(folder)
                                   if os.path.splitext(f)[1].lower() in exts])
            self.setWindowTitle(f"{self.base_title} - {os.path.basename(current_file)}")
        except: pass

    def open_next_file(self):
        if not self.playlist: return
        idx = (self.playlist.index(self.current_file_path) + 1) % len(self.playlist)
        self.load_content(self.playlist[idx])

    def open_prev_file(self):
        if not self.playlist: return
        idx = (self.playlist.index(self.current_file_path) - 1) % len(self.playlist)
        self.load_content(self.playlist[idx])

    def load_content(self, file_path):
        if not os.path.exists(file_path): return
        ext = os.path.splitext(file_path)[1].lower()
        self.media_player.stop()
        self.image_scene.clear()
        if self.movie: self.movie.stop(); self.movie = None
        self.update_playlist(file_path)

        if ext in ['.png', '.jpg', '.jpeg', '.gif']: self.show_image_mode(file_path)
        else: self.show_media_mode(file_path)

    def show_image_mode(self, path):
        self.stack.setCurrentIndex(0)
        self.media_controls.hide(); self.image_controls.show()
        if path.lower().endswith('.gif'):
            lbl = QLabel()
            self.movie = QMovie(path)
            lbl.setMovie(self.movie)
            self.image_item = self.image_scene.addWidget(lbl)
            self.movie.start()
        else:
            pix = QPixmap(path)
            self.image_item = QGraphicsPixmapItem(pix)
            self.image_item.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
            self.image_scene.addItem(self.image_item)
        QTimer.singleShot(10, self.center_content)

    def center_content(self):
        view = self.image_view if self.stack.currentIndex() == 0 else self.video_view
        item = self.image_item if self.stack.currentIndex() == 0 else self.video_item
        if item: view.fitInView(item, Qt.AspectRatioMode.KeepAspectRatio)

    def zoom_content(self, f):
        view = self.image_view if self.stack.currentIndex() == 0 else self.video_view
        view.scale(f, f)

    def rotate_content(self, a):
        view = self.image_view if self.stack.currentIndex() == 0 else self.video_view
        view.rotate(float(a))

    def flip_horizontal(self):
        view = self.image_view if self.stack.currentIndex() == 0 else self.video_view
        view.scale(-1, 1)

    def open_print_dialog(self):
        printer = QPrinter()
        if QPrintDialog(printer, self).exec() == QPrintDialog.Accepted:
            p = QPainter(printer)
            pix = self.image_item.pixmap() if hasattr(self.image_item, 'pixmap') else QPixmap()
            p.drawPixmap(0, 0, pix.scaled(printer.pageRect(QPrinter.Unit.DevicePixel).size().toSize(), Qt.AspectRatioMode.KeepAspectRatio))
            p.end()

    def show_media_mode(self, path):
        self.stack.setCurrentIndex(1)
        self.image_controls.hide(); self.media_controls.show()
        is_audio = os.path.splitext(path)[1].lower() in ['.mp3', '.wav']
        if is_audio:
            self.video_view.hide(); self.music_label.show()
            self.music_label.setText(f"🎵 AUDIO:\n{os.path.basename(path)}")
        else:
            self.music_label.hide(); self.video_view.show()
            self.video_item.setSize(QSize(1280, 720))
        self.media_player.setSource(QUrl.fromLocalFile(path))
        self.media_player.play()
        QTimer.singleShot(100, self.center_content)

    def play_video(self):
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState: self.media_player.pause()
        else: self.media_player.play()

    def media_state_changed(self, s):
        icon = QStyle.StandardPixmap.SP_MediaPause if s == QMediaPlayer.PlaybackState.PlayingState else QStyle.StandardPixmap.SP_MediaPlay
        self.btn_play.setIcon(self.style().standardIcon(icon))

    def position_changed(self, p):
        if not self.slider_seek.isSliderDown(): self.slider_seek.setValue(p)

    def duration_changed(self, d):
        self.slider_seek.setRange(0, int(d))
        self.duration = d

    def set_position(self, p): self.media_player.setPosition(p)
    def seek_relative(self, d): self.media_player.setPosition(max(0, min(self.media_player.position() + d, self.duration)))
    def set_volume(self, v): self.audio_output.setVolume(v / 100.0)
    def toggle_mute(self):
        self.audio_output.setMuted(not self.audio_output.isMuted())
        icon = QStyle.StandardPixmap.SP_MediaVolumeMuted if self.audio_output.isMuted() else QStyle.StandardPixmap.SP_MediaVolume
        self.btn_mute.setIcon(self.style().standardIcon(icon))
    def set_speed(self): self.media_player.setPlaybackRate(float(self.combo_speed.currentText().replace("x", "")))
    def handle_errors(self, e, s):
        if e != QMediaPlayer.Error.NoError: self.display_error(s)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    # Tên ứng dụng cho hệ thống
    app.setApplicationName("WPMV Player")
    app.setStyle("Fusion")
    window = UniversalViewer()
    window.show()
    sys.exit(app.exec())
