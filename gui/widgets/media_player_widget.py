"""
Widget for output clip gallery and integrated multimedia player playback.
"""

from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QSlider
)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget
import os

class MediaPlayerWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("class", "card")
        self.output_dir = "clips"
        self.init_ui()
        self.init_player()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        # Header Title & Open Folder Button
        header_layout = QHBoxLayout()
        title_label = QLabel("🎬 Output Clips Gallery & Video Player")
        title_label.setProperty("class", "section-header")

        self.btn_open_folder = QPushButton("📂 Open Output Folder")
        self.btn_open_folder.clicked.connect(self.on_open_folder)

        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.btn_open_folder)
        layout.addLayout(header_layout)

        content_layout = QHBoxLayout()

        # Left Column: Clips List Gallery
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("Daftar Klip Dihasilkan:"))
        self.clip_list = QListWidget()
        self.clip_list.setFixedWidth(200)
        self.clip_list.itemClicked.connect(self.on_clip_selected)
        left_layout.addWidget(self.clip_list)

        content_layout.addLayout(left_layout)

        # Right Column: Embedded QVideoWidget & Playback Controls
        right_layout = QVBoxLayout()

        self.video_widget = QVideoWidget()
        self.video_widget.setFixedHeight(260)
        self.video_widget.setStyleSheet("background-color: #000000; border-radius: 8px;")
        right_layout.addWidget(self.video_widget)

        # Player Controls (Play, Pause, Seek, Volume)
        ctrl_layout = QHBoxLayout()

        self.btn_play = QPushButton("▶ Play")
        self.btn_play.clicked.connect(self.toggle_play)

        self.seek_slider = QSlider(Qt.Orientation.Horizontal)
        self.seek_slider.setRange(0, 0)
        self.seek_slider.sliderMoved.connect(self.set_position)

        ctrl_layout.addWidget(self.btn_play)
        ctrl_layout.addWidget(self.seek_slider)
        right_layout.addLayout(ctrl_layout)

        content_layout.addLayout(right_layout, 1)

        layout.addLayout(content_layout)

    def init_player(self):
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.player.setVideoOutput(self.video_widget)

        self.player.positionChanged.connect(self.on_position_changed)
        self.player.durationChanged.connect(self.on_duration_changed)

    def update_outputs(self, outputs: list, output_dir: str):
        self.output_dir = output_dir
        self.clip_list.clear()
        for item in outputs:
            name = item.get("name")
            path = item.get("path")
            size_mb = item.get("size", 0) / (1024 * 1024)
            list_item = QListWidgetItem(f"{name} ({size_mb:.1f} MB)")
            list_item.setData(Qt.ItemDataRole.UserRole, path)
            self.clip_list.addItem(list_item)

        if self.clip_list.count() > 0:
            self.clip_list.setCurrentRow(0)
            self.on_clip_selected(self.clip_list.item(0))

    def on_clip_selected(self, item: QListWidgetItem):
        path = item.data(Qt.ItemDataRole.UserRole)
        if path and os.path.exists(path):
            url = QUrl.fromLocalFile(path)
            self.player.setSource(url)
            self.player.play()
            self.btn_play.setText("⏸ Pause")

    def toggle_play(self):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
            self.btn_play.setText("▶ Play")
        else:
            self.player.play()
            self.btn_play.setText("⏸ Pause")

    def on_position_changed(self, position: int):
        self.seek_slider.setValue(position)

    def on_duration_changed(self, duration: int):
        self.seek_slider.setRange(0, duration)

    def set_position(self, position: int):
        self.player.setPosition(position)

    def on_open_folder(self):
        if os.path.exists(self.output_dir):
            abs_path = os.path.abspath(self.output_dir)
            QDesktopServices.openUrl(QUrl.fromLocalFile(abs_path))
