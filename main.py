import sys
import os
import time

# Thiết lập biến môi trường để giảm bớt các log không cần thiết của Qt nếu muốn
# os.environ["QT_LOGGING_RULES"] = "qt.multimedia.ffmpeg=false"

try:
    from PyQt6.QtWidgets import (QApplication, QMainWindow, QFileDialog, QWidget, QVBoxLayout,
                                 QHBoxLayout, QPushButton, QLabel, QSlider, QStyle, QGraphicsView,
                                 QGraphicsScene, QGraphicsPixmapItem, QStackedWidget, QComboBox,
                                 QFrame)
    from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
    from PyQt6.QtMultimediaWidgets import QGraphicsVideoItem
    from PyQt6.QtCore import Qt, QUrl, QTimer, QRectF, QEvent, QStandardPaths, pyqtSignal, QPoint
    from PyQt6.QtGui import QPixmap, QPalette, QColor, QWheelEvent, QKeyEvent, QPainter, QMovie, QKeySequence, QImage, QAction
    from PyQt6.QtPrintSupport import QPrinter, QPrintDialog
except ImportError:
    print("Vui lòng cài đặt đầy đủ: pip install PyQt6 PyQt6-Qt6 PyQt6-QtMultimedia")
    sys.exit(1)

class ClickableSlider(QSlider):
    """Thanh trượt tùy chỉnh cho phép nhảy tới vị trí click chuột ngay lập tức"""
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            new_value = self.minimum() + ((self.maximum() - self.minimum()) * event.position().x()) / self.width()
            self.setValue(int(new_value))
            self.sliderMoved.emit(self.value())
            event.accept()
        super().mousePressEvent(event)

class CustomGraphicsView(QGraphicsView):
    """Lớp tùy chỉnh QGraphicsView để xử lý sự kiện chuột chuyên cho xem ảnh và video"""
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
        if event.angleDelta().y() > 0:
            zoom_factor = zoom_in_factor
        else:
            zoom_factor = zoom_out_factor
        self.scale(zoom_factor, zoom_factor)

class ClickableLabel(QLabel):
    """Nhãn có thể click để thực hiện hành động"""
    clicked = pyqtSignal()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

class UniversalViewer(QMainWindow):
    def __init__(self):
        super().__init__()

        self.base_title = "WPMV"
        self.setWindowTitle(self.base_title)
        self.setGeometry(100, 100, 1100, 800)

        self.set_dark_theme()
        self.duration = 0
        self.current_file_path = ""
        self.playlist = []

        # --- GIAO DIỆN CHÍNH ---
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        self.stack = QStackedWidget()

        # Mode 1: Xem Ảnh / GIF
        self.image_scene = QGraphicsScene()
        self.image_view = CustomGraphicsView(self.image_scene)
        self.image_item = None
        self.movie = None

        self.image_view.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.stack.addWidget(self.image_view)

        # Mode 2: Xem Video/Nhạc
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
        self.music_label.setWordWrap(True)
        self.music_label.hide()

        self.video_layout.addWidget(self.video_view)
        self.video_layout.addWidget(self.music_label)
        self.stack.addWidget(self.video_container)

        # Mode 3: Màn hình chờ
        self.placeholder = ClickableLabel(
            "WPMV\n\n"
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
        self.controls_layout = QVBoxLayout()
        self.main_layout.addLayout(self.controls_layout)

        # MEDIA CONTROLS
        self.media_controls = QWidget()
        self.media_v_layout = QVBoxLayout(self.media_controls)
        self.media_v_layout.setContentsMargins(0, 0, 0, 0)
        self.media_v_layout.setSpacing(5)

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

        self.btn_seek_m1m = create_seek_btn("-1m", -60000)
        self.btn_seek_m30s = create_seek_btn("-30s", -30000)
        self.btn_seek_m10s = create_seek_btn("-10s", -10000)

        self.btn_play = QPushButton()
        self.btn_play.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.btn_play.clicked.connect(self.play_video)
        self.btn_play.setFixedWidth(45)

        self.btn_seek_p10s = create_seek_btn("+10s", 10000)
        self.btn_seek_p30s = create_seek_btn("+30s", 30000)
        self.btn_seek_p1m = create_seek_btn("+1m", 60000)

        self.btn_screenshot = QPushButton()
        self.btn_screenshot.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView))
        self.btn_screenshot.setToolTip("Chụp ảnh màn hình video")
        self.btn_screenshot.setFixedWidth(35)
        self.btn_screenshot.clicked.connect(self.take_screenshot)

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

        self.media_h_layout.addWidget(self.btn_seek_m1m)
        self.media_h_layout.addWidget(self.btn_seek_m30s)
        self.media_h_layout.addWidget(self.btn_seek_m10s)
        self.media_h_layout.addSpacing(5)
        self.media_h_layout.addWidget(self.btn_play)
        self.media_h_layout.addSpacing(5)
        self.media_h_layout.addWidget(self.btn_seek_p10s)
        self.media_h_layout.addWidget(self.btn_seek_p30s)
        self.media_h_layout.addWidget(self.btn_seek_p1m)
        self.media_h_layout.addStretch()
        self.media_h_layout.addWidget(self.btn_screenshot)
        self.media_h_layout.addWidget(self.btn_mute)
        self.media_h_layout.addWidget(self.slider_vol)
        self.media_h_layout.addWidget(self.combo_speed)

        # IMAGE CONTROLS
        self.image_controls = QWidget()
        self.img_layout = QHBoxLayout(self.image_controls)
        self.img_layout.setContentsMargins(0, 0, 0, 0)

        self.btn_zoom_in = QPushButton("Zoom +")
        self.btn_zoom_in.clicked.connect(lambda: self.zoom_content(1.25))
        self.btn_zoom_out = QPushButton("Zoom -")
        self.btn_zoom_out.clicked.connect(lambda: self.zoom_content(0.8))
        self.btn_rotate_l = QPushButton("Xoay Trái")
        self.btn_rotate_l.clicked.connect(lambda: self.rotate_content(-90))
        self.btn_rotate_r = QPushButton("Xoay Phải")
        self.btn_rotate_r.clicked.connect(lambda: self.rotate_content(90))
        self.btn_flip_h = QPushButton("Lật Ngang")
        self.btn_flip_h.clicked.connect(self.flip_horizontal)
        self.btn_flip_v = QPushButton("Lật Dọc")
        self.btn_flip_v.clicked.connect(self.flip_vertical)

        self.btn_print = QPushButton("In Ảnh (Ctrl+P)")
        self.btn_print.clicked.connect(self.open_print_dialog)
        self.btn_print.setStyleSheet("background-color: #28a745; color: white; padding: 5px 15px;")

        self.img_layout.addWidget(self.btn_zoom_in)
        self.img_layout.addWidget(self.btn_zoom_out)
        self.img_layout.addWidget(self.btn_rotate_l)
        self.img_layout.addWidget(self.btn_rotate_r)
        self.img_layout.addWidget(self.btn_flip_h)
        self.img_layout.addWidget(self.btn_flip_v)
        self.img_layout.addWidget(self.btn_print)

        self.controls_layout.addWidget(self.media_controls)
        self.controls_layout.addWidget(self.image_controls)

        self.bottom_bar = QHBoxLayout()
        self.controls_layout.addLayout(self.bottom_bar)

        self.btn_open = QPushButton("Mở File")
        self.btn_open.clicked.connect(self.open_file)
        self.btn_open.setStyleSheet("background-color: #0078d7; color: white; font-weight: bold; padding: 8px 25px;")

        self.btn_prev = QPushButton()
        self.btn_prev.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowBack))
        self.btn_prev.clicked.connect(self.open_prev_file)
        self.btn_prev.setFixedWidth(40)
        self.btn_prev.setEnabled(False)
        self.btn_prev.hide()

        self.btn_next = QPushButton()
        self.btn_next.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowForward))
        self.btn_next.clicked.connect(self.open_next_file)
        self.btn_next.setFixedWidth(40)
        self.btn_next.setEnabled(False)
        self.btn_next.hide()

        self.bottom_bar.addWidget(self.btn_open, 1)
        self.bottom_bar.addWidget(self.btn_prev)
        self.bottom_bar.addWidget(self.btn_next)

        self.media_controls.hide()
        self.image_controls.hide()

        # Media Player (PyQt6 Setup)
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.audio_output.setVolume(0.7) # Mặc định 70%
        self.media_player.setAudioOutput(self.audio_output)
        self.media_player.setVideoOutput(self.video_item)

        self.media_player.playbackStateChanged.connect(self.media_state_changed)
        self.media_player.positionChanged.connect(self.position_changed)
        self.media_player.durationChanged.connect(self.duration_changed)
        self.media_player.errorOccurred.connect(self.handle_errors)

        # KIỂM TRA ĐỐI SỐ DÒNG LỆNH (CHO WINDOWS DEFAULT APP)
        # Nếu app được mở qua double click file, sys.argv sẽ có len > 1
        if len(sys.argv) > 1:
            file_to_open = sys.argv[1]
            # Sử dụng QTimer để đảm bảo giao diện đã load xong trước khi mở file
            QTimer.singleShot(200, lambda: self.load_content(file_to_open))

    def take_screenshot(self):
        if self.stack.currentIndex() != 1 or self.video_view.isHidden():
            return
        try:
            pixmap = self.video_view.grab()
            if pixmap.isNull(): return
            folder = os.path.dirname(self.current_file_path)
            base_name = os.path.splitext(os.path.basename(self.current_file_path))[0]
            save_path = os.path.join(folder, f"{base_name}_{int(time.time())}.jpg")
            pixmap.save(save_path, "JPG")
            print(f"Đã lưu: {save_path}")
        except Exception as e:
            print(f"Lỗi chụp ảnh: {e}")

    def display_error(self, message):
        filename = os.path.basename(self.current_file_path) if self.current_file_path else "Không rõ"
        full_msg = f"⚠️ LỖI: {message}\nFile: {filename}"
        if self.stack.currentIndex() == 1:
            self.video_view.hide()
            self.music_label.show()
            self.music_label.setText(full_msg)
        else:
            self.stack.setCurrentIndex(2)
            self.placeholder.setText(f"{full_msg}\n\nClick để thử lại")

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_O:
            self.open_file()
            return
        if event.key() == Qt.Key.Key_P and (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            self.open_print_dialog()
            return
        if event.key() in [Qt.Key.Key_PageDown, Qt.Key.Key_Period]:
            if self.playlist and len(self.playlist) > 1:
                self.open_next_file()
                return
        if event.key() in [Qt.Key.Key_PageUp, Qt.Key.Key_Comma]:
            if self.playlist and len(self.playlist) > 1:
                self.open_prev_file()
                return
        if event.key() == Qt.Key.Key_Space:
            if self.stack.currentIndex() == 1:
                self.play_video()
                return
        if self.stack.currentIndex() in [0, 1]:
            if event.key() in [Qt.Key.Key_Plus, Qt.Key.Key_Equal]:
                self.zoom_content(1.25)
            elif event.key() == Qt.Key.Key_Minus:
                self.zoom_content(0.8)
        super().keyPressEvent(event)

    def set_dark_theme(self):
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Base, QColor(25, 25, 25))
        palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
        self.setPalette(palette)

    def open_file(self):
        downloads_path = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DownloadLocation)
        file_dialog = QFileDialog(self)
        file_dialog.setDirectory(downloads_path)
        file_dialog.setNameFilters(["Media Files (*.png *.jpg *.jpeg *.bmp *.gif *.webp *.mp4 *.avi *.mkv *.mp3 *.wav *.flac *.m4a)", "All Files (*)"])
        if file_dialog.exec():
            files = file_dialog.selectedFiles()
            if files: self.load_content(files[0])

    def update_playlist(self, current_file):
        try:
            folder = os.path.dirname(current_file)
            self.current_file_path = os.path.normpath(current_file)
            supported_exts = {'.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp',
                              '.mp4', '.avi', '.mkv', '.mov', '.mp3', '.wav', '.flac', '.m4a'}
            files = [os.path.normpath(os.path.join(folder, f)) for f in os.listdir(folder)
                     if os.path.splitext(f)[1].lower() in supported_exts]
            self.playlist = sorted(files)

            filename = os.path.basename(self.current_file_path)
            self.setWindowTitle(f"{self.base_title} - {filename}")

            has_multiple = len(self.playlist) > 1
            self.btn_prev.setEnabled(has_multiple)
            self.btn_next.setEnabled(has_multiple)
            self.btn_prev.setVisible(bool(self.current_file_path))
            self.btn_next.setVisible(bool(self.current_file_path))
        except: pass

    def open_next_file(self):
        if not self.playlist or not self.current_file_path: return
        try:
            current_idx = self.playlist.index(self.current_file_path)
            next_idx = (current_idx + 1) % len(self.playlist)
            self.load_content(self.playlist[next_idx])
        except: self.update_playlist(self.current_file_path)

    def open_prev_file(self):
        if not self.playlist or not self.current_file_path: return
        try:
            current_idx = self.playlist.index(self.current_file_path)
            prev_idx = (current_idx - 1) % len(self.playlist)
            self.load_content(self.playlist[prev_idx])
        except: self.update_playlist(self.current_file_path)

    def load_content(self, file_path):
        self.current_file_path = os.path.normpath(file_path)
        if not os.path.exists(file_path):
            self.display_error("File không tồn tại.")
            return
        ext = os.path.splitext(file_path)[1].lower()
        self.media_player.stop()
        self.media_player.setPlaybackRate(1.0)
        self.combo_speed.setCurrentIndex(1)
        self.image_scene.clear()
        if self.movie: self.movie.stop(); self.movie = None
        self.image_item = None
        self.update_playlist(file_path)

        image_exts = ['.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp']
        media_exts = ['.mp4', '.avi', '.mkv', '.mov', '.mp3', '.wav', '.flac', '.m4a']
        if ext in image_exts: self.show_image_mode(file_path)
        elif ext in media_exts: self.show_media_mode(file_path)
        else: self.display_error(f"Định dạng '{ext}' không hỗ trợ.")

    def show_image_mode(self, path):
        self.stack.setCurrentIndex(0)
        self.media_controls.hide()
        self.image_controls.show()
        ext = os.path.splitext(path)[1].lower()
        try:
            if ext == '.gif':
                label = QLabel()
                self.movie = QMovie(path)
                if not self.movie.isValid(): raise Exception("GIF lỗi")
                label.setMovie(self.movie)
                self.movie.jumpToFrame(0)
                size = self.movie.currentImage().size()
                label.setFixedSize(size)
                self.image_item = self.image_scene.addWidget(label)
                self.movie.start()
                self.image_scene.setSceneRect(QRectF(0, 0, float(size.width()), float(size.height())))
            else:
                pixmap = QPixmap(path)
                if pixmap.isNull(): raise Exception("Lỗi tải ảnh")
                self.image_item = QGraphicsPixmapItem(pixmap)
                self.image_item.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
                self.image_scene.addItem(self.image_item)
                self.image_scene.setSceneRect(QRectF(pixmap.rect()))
            self.image_view.resetTransform()
            QTimer.singleShot(10, self.center_content)
        except Exception as e: self.display_error(str(e))

    def center_content(self):
        if self.stack.currentIndex() == 0 and self.image_item:
            self.image_view.fitInView(self.image_item, Qt.AspectRatioMode.KeepAspectRatio)
            self.image_view.centerOn(self.image_item)
        elif self.stack.currentIndex() == 1 and self.video_item:
            self.video_view.fitInView(self.video_item, Qt.AspectRatioMode.KeepAspectRatio)
            self.video_view.centerOn(self.video_item)

    def zoom_content(self, factor):
        view = self.image_view if self.stack.currentIndex() == 0 else self.video_view
        view.scale(factor, factor)

    def rotate_content(self, angle):
        view = self.image_view if self.stack.currentIndex() == 0 else self.video_view
        view.rotate(float(angle))

    def flip_horizontal(self):
        view = self.image_view if self.stack.currentIndex() == 0 else self.video_view
        view.scale(-1, 1)

    def flip_vertical(self):
        view = self.image_view if self.stack.currentIndex() == 0 else self.video_view
        view.scale(1, -1)

    def open_print_dialog(self):
        if self.stack.currentIndex() != 0: return
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        dialog = QPrintDialog(printer, self)
        if dialog.exec() == QPrintDialog.Accepted:
            self.render_to_printer(printer)

    def render_to_printer(self, printer):
        pixmap = self.movie.currentPixmap() if self.movie else self.image_item.pixmap()
        if not pixmap or pixmap.isNull(): return
        painter = QPainter()
        if not painter.begin(printer): return
        rect = printer.pageRect(QPrinter.Unit.Point)
        size = pixmap.size()
        size.scale(int(rect.width()), int(rect.height()), Qt.AspectRatioMode.KeepAspectRatio)
        painter.drawPixmap(int(rect.x()), int(rect.y()), int(size.width()), int(size.height()), pixmap)
        painter.end()

    def show_media_mode(self, path):
        self.stack.setCurrentIndex(1)
        self.image_controls.hide()
        self.media_controls.show()
        ext = os.path.splitext(path)[1].lower()
        is_audio = ext in ['.mp3', '.wav', '.flac', '.m4a']
        if is_audio:
            self.video_view.hide(); self.music_label.show()
            self.music_label.setText(f"🎵 ĐANG PHÁT AUDIO:\n\n{os.path.basename(path)}")
            self.btn_screenshot.hide()
        else:
            self.music_label.hide(); self.video_view.show()
            self.video_item.setSize(QRectF(0, 0, 1280, 720).size())
            self.btn_screenshot.show()

        self.media_player.setSource(QUrl.fromLocalFile(path))
        self.media_player.play()
        self.video_view.resetTransform()
        QTimer.singleShot(100, self.center_content)

    def play_video(self):
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.media_player.pause()
        else: self.media_player.play()

    def media_state_changed(self, state):
        icon = QStyle.StandardPixmap.SP_MediaPause if state == QMediaPlayer.PlaybackState.PlayingState else QStyle.StandardPixmap.SP_MediaPlay
        self.btn_play.setIcon(self.style().standardIcon(icon))

    def position_changed(self, position):
        if not self.slider_seek.isSliderDown(): self.slider_seek.setValue(position)

    def duration_changed(self, duration):
        self.slider_seek.setRange(0, int(duration))
        self.duration = duration

    def set_position(self, position):
        self.media_player.setPosition(position)

    def seek_relative(self, delta_ms):
        new_pos = max(0, min(self.media_player.position() + delta_ms, self.duration))
        self.media_player.setPosition(new_pos)

    def set_volume(self, volume):
        self.audio_output.setVolume(volume / 100.0)

    def toggle_mute(self):
        self.audio_output.setMuted(not self.audio_output.isMuted())
        icon = QStyle.StandardPixmap.SP_MediaVolumeMuted if self.audio_output.isMuted() else QStyle.StandardPixmap.SP_MediaVolume
        self.btn_mute.setIcon(self.style().standardIcon(icon))

    def set_speed(self):
        speed = float(self.combo_speed.currentText().replace("x", ""))
        self.media_player.setPlaybackRate(speed)

    def handle_errors(self, error, error_string):
        if error != QMediaPlayer.Error.NoError:
            self.display_error(f"Lỗi Media: {error_string}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = UniversalViewer()
    window.show()
    sys.exit(app.exec())
