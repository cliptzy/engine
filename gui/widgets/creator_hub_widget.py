"""
Widget for YouTuber Creator Channels (Compact Authentic Cards), Video Catalog Browser, Search & Pagination.
"""

import urllib.request
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit, QPushButton,
    QStackedWidget, QWidget, QComboBox, QRadioButton, QButtonGroup, QScrollArea
)
from PyQt6.QtGui import QPixmap, QImage
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from core.channel_manager import channel_manager
from core.logger import log

class ImageDownloader(QThread):
    finished_signal = pyqtSignal(str, bytes)

    def __init__(self, url: str):
        super().__init__()
        self.url = url

    def run(self):
        try:
            req = urllib.request.Request(self.url, headers={'User-Agent': 'Mozilla/5.0'})
            data = urllib.request.urlopen(req, timeout=5).read()
            self.finished_signal.emit(self.url, data)
        except Exception:
            self.finished_signal.emit(self.url, b"")

class CreatorHubWidget(QFrame):
    video_selected_signal = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.active_channel_id = None
        self.current_tab = "upload"
        self.current_page = 1
        self.current_search = ""
        self.current_sort = "views"
        self.image_workers = []
        self.init_ui()
        self.load_channels()

    def init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(20, 18, 20, 18)
        root_layout.setSpacing(16)

        # Top Header Bar: Add YouTuber Channel Input
        top_bar = QHBoxLayout()
        title_label = QLabel("🎮 YouTuber Channel Catalog")
        title_label.setProperty("class", "section-header")
        top_bar.addWidget(title_label)
        top_bar.addStretch()

        self.input_handle = QLineEdit()
        self.input_handle.setPlaceholderText("Tambah YouTuber: username (@WindahBasudara) atau URL channel...")
        self.input_handle.setFixedWidth(400)
        self.input_handle.returnPressed.connect(self.on_add_channel)

        self.btn_add_channel = QPushButton("➕ Daftarkan YouTuber")
        self.btn_add_channel.setProperty("class", "primary")
        self.btn_add_channel.clicked.connect(self.on_add_channel)

        top_bar.addWidget(self.input_handle)
        top_bar.addWidget(self.btn_add_channel)
        root_layout.addLayout(top_bar)

        # Stacked pages: Page 0 = YouTuber Channels Grid, Page 1 = Videos Catalog
        self.stack = QStackedWidget()

        # --- Page 0: Compact YouTuber Cards Grid ---
        self.channels_page = QWidget()
        channels_layout = QVBoxLayout(self.channels_page)
        channels_layout.setContentsMargins(0, 0, 0, 0)
        channels_layout.setSpacing(10)

        section_hint = QLabel("Pilih YouTuber untuk menjelajahi daftar video Upload & Live Stream:")
        section_hint.setProperty("class", "muted")
        channels_layout.addWidget(section_hint)

        channels_scroll = QScrollArea()
        channels_scroll.setWidgetResizable(True)
        channels_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.channels_grid_container = QWidget()
        self.channels_grid = QGridLayout(self.channels_grid_container)
        self.channels_grid.setSpacing(16)
        self.channels_grid.setContentsMargins(0, 0, 0, 0)
        self.channels_grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        channels_scroll.setWidget(self.channels_grid_container)
        channels_layout.addWidget(channels_scroll, 1)
        self.stack.addWidget(self.channels_page)

        # --- Page 1: Channel Video Catalog Explorer ---
        self.videos_page = QWidget()
        videos_layout = QVBoxLayout(self.videos_page)
        videos_layout.setContentsMargins(0, 0, 0, 0)
        videos_layout.setSpacing(12)

        # Navigation Header
        nav_header = QHBoxLayout()
        self.btn_back = QPushButton("⬅ Kembali ke Daftar YouTuber")
        self.btn_back.clicked.connect(self.show_channels_grid)
        nav_header.addWidget(self.btn_back)

        self.active_channel_title = QLabel("Channel: -")
        self.active_channel_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #38bdf8;")
        nav_header.addWidget(self.active_channel_title)

        self.active_channel_subs = QLabel("- subscriber")
        self.active_channel_subs.setStyleSheet("color: #94a3b8; font-size: 13px;")
        nav_header.addWidget(self.active_channel_subs)
        nav_header.addStretch()

        videos_layout.addLayout(nav_header)

        # Filter & Search Bar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(12)

        # Tabs: Uploads vs Live
        self.tab_group = QButtonGroup(self)
        self.radio_uploads = QRadioButton("📹 Uploads")
        self.radio_live = QRadioButton("🔴 Live Streams")
        self.radio_uploads.setChecked(True)
        self.tab_group.addButton(self.radio_uploads, 1)
        self.tab_group.addButton(self.radio_live, 2)
        self.tab_group.idToggled.connect(self.on_tab_changed)

        toolbar.addWidget(self.radio_uploads)
        toolbar.addWidget(self.radio_live)

        # Search
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Cari judul video...")
        self.search_input.textChanged.connect(self.on_search_changed)
        toolbar.addWidget(self.search_input, 1)

        # Sort
        toolbar.addWidget(QLabel("Urutkan:"))
        self.sort_combo = QComboBox()
        self.sort_combo.addItem("🔥 Views Terbanyak", "views")
        self.sort_combo.addItem("🆕 Terbaru", "newest")
        self.sort_combo.addItem("⏱ Durasi Terlama", "duration")
        self.sort_combo.currentIndexChanged.connect(self.on_sort_changed)
        toolbar.addWidget(self.sort_combo)

        videos_layout.addLayout(toolbar)

        # Videos Catalog Scroll Area
        videos_scroll = QScrollArea()
        videos_scroll.setWidgetResizable(True)
        videos_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.videos_grid_container = QWidget()
        self.videos_grid = QGridLayout(self.videos_grid_container)
        self.videos_grid.setSpacing(14)
        self.videos_grid.setContentsMargins(0, 0, 0, 0)
        self.videos_grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        videos_scroll.setWidget(self.videos_grid_container)
        videos_layout.addWidget(videos_scroll, 1)

        # Pagination Control Bar
        pagination_layout = QHBoxLayout()
        self.btn_prev_page = QPushButton("◀ Prev")
        self.btn_prev_page.clicked.connect(self.on_prev_page)

        self.page_info_label = QLabel("Halaman 1 dari 1")
        self.page_info_label.setStyleSheet("font-weight: bold; color: #94a3b8;")

        self.btn_next_page = QPushButton("Next ▶")
        self.btn_next_page.clicked.connect(self.on_next_page)

        pagination_layout.addStretch()
        pagination_layout.addWidget(self.btn_prev_page)
        pagination_layout.addWidget(self.page_info_label)
        pagination_layout.addWidget(self.btn_next_page)
        pagination_layout.addStretch()

        videos_layout.addLayout(pagination_layout)
        self.stack.addWidget(self.videos_page)

        root_layout.addWidget(self.stack, 1)

    def load_channels(self):
        """Loads compact YouTuber cards into grid."""
        while self.channels_grid.count():
            item = self.channels_grid.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        channels = channel_manager.get_all_channels()
        cols = 3
        for idx, ch in enumerate(channels):
            r = idx // cols
            c = idx % cols
            card = self.create_compact_channel_card(ch)
            self.channels_grid.addWidget(card, r, c)

    def create_compact_channel_card(self, ch: dict) -> QFrame:
        """Creates a sleek, compact authentic YouTuber card."""
        card = QFrame()
        card.setMinimumWidth(260)
        card.setFixedHeight(92)
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        card.setStyleSheet("""
            QFrame {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 12px;
                padding: 10px 14px;
            }
            QFrame:hover {
                border: 1px solid #6366f1;
                background-color: #312e81;
            }
        """)
        layout = QHBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(12)

        # Avatar Image Label
        avatar_lbl = QLabel()
        avatar_lbl.setFixedSize(54, 54)
        avatar_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar_lbl.setStyleSheet("background-color: #0f172a; border-radius: 27px; color: #818cf8; font-weight: bold; font-size: 20px;")
        avatar_lbl.setText("🎮")
        
        avatar_url = ch.get("avatar")
        if avatar_url:
            worker = ImageDownloader(avatar_url)
            def on_avatar_downloaded(url, data, lbl=avatar_lbl, w=worker):
                if data:
                    img = QImage()
                    img.loadFromData(data)
                    pixmap = QPixmap.fromImage(img)
                    scaled = pixmap.scaled(54, 54, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
                    lbl.setPixmap(scaled)
                if w in self.image_workers:
                    self.image_workers.remove(w)
            worker.finished_signal.connect(on_avatar_downloaded)
            self.image_workers.append(worker)
            worker.start()

        layout.addWidget(avatar_lbl)

        # Text Details
        meta = QVBoxLayout()
        meta.setSpacing(4)
        
        name_lbl = QLabel(ch.get("name", "YouTuber"))
        name_lbl.setStyleSheet("font-weight: bold; font-size: 14px; color: #f8fafc;")

        sub_lbl = QLabel(f"{ch.get('handle', '@channel')} • {ch.get('subscribers_str', 'Subscriber N/A')}")
        sub_lbl.setStyleSheet("color: #94a3b8; font-size: 12px;")

        btn_explore = QLabel("▶ Jelajahi Video Catalog")
        btn_explore.setStyleSheet("color: #38bdf8; font-size: 11px; font-weight: bold;")

        meta.addWidget(name_lbl)
        meta.addWidget(sub_lbl)
        meta.addWidget(btn_explore)
        layout.addLayout(meta, 1)

        c_id = ch.get("id")
        c_name = ch.get("name")
        c_subs = ch.get("subscribers_str", "")
        card.mousePressEvent = lambda e, cid=c_id, cname=c_name, csubs=c_subs: self.open_channel_catalog(cid, cname, csubs)

        return card

    def on_add_channel(self):
        query = self.input_handle.text().strip()
        if not query:
            return
        self.btn_add_channel.setEnabled(False)
        self.btn_add_channel.setText("⏳ Scraping Channel...")

        try:
            ch_data = channel_manager.add_channel_by_url_or_handle(query)
            self.input_handle.clear()
            self.load_channels()
            self.open_channel_catalog(ch_data.get("id"), ch_data.get("name"), ch_data.get("subscribers_str", ""))
        except Exception as e:
            log.error(f"Gagal menambahkan channel: {e}")
        finally:
            self.btn_add_channel.setEnabled(True)
            self.btn_add_channel.setText("➕ Daftarkan YouTuber")

    def show_channels_grid(self):
        self.stack.setCurrentIndex(0)

    def open_channel_catalog(self, channel_id: str, channel_name: str, channel_subs: str = ""):
        self.active_channel_id = channel_id
        self.active_channel_title.setText(f"Channel: {channel_name}")
        self.active_channel_subs.setText(channel_subs)
        self.current_page = 1
        self.stack.setCurrentIndex(1)
        self.load_video_catalog()

    def on_tab_changed(self, btn_id: int, checked: bool):
        if checked:
            self.current_tab = "upload" if btn_id == 1 else "live"
            self.current_page = 1
            self.load_video_catalog()

    def on_search_changed(self, text: str):
        self.current_search = text.strip()
        self.current_page = 1
        self.load_video_catalog()

    def on_sort_changed(self, idx: int):
        self.current_sort = self.sort_combo.currentData()
        self.current_page = 1
        self.load_video_catalog()

    def on_prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.load_video_catalog()

    def on_next_page(self):
        self.current_page += 1
        self.load_video_catalog()

    def load_video_catalog(self):
        if not self.active_channel_id:
            return

        while self.videos_grid.count():
            item = self.videos_grid.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        res = channel_manager.get_channel_videos_catalog(
            channel_id=self.active_channel_id,
            tab=self.current_tab,
            search=self.current_search,
            sort_by=self.current_sort,
            page=self.current_page,
            per_page=12
        )

        videos = res.get("videos", [])
        total_pages = res.get("total_pages", 1)
        self.current_page = res.get("current_page", 1)

        self.page_info_label.setText(f"Halaman {self.current_page} dari {total_pages} ({res.get('total_items', 0)} video)")
        self.btn_prev_page.setEnabled(self.current_page > 1)
        self.btn_next_page.setEnabled(self.current_page < total_pages)

        cols = 3
        for idx, v in enumerate(videos):
            r = idx // cols
            c = idx % cols
            card = self.create_video_card(v)
            self.videos_grid.addWidget(card, r, c)

    def create_video_card(self, v: dict) -> QFrame:
        card = QFrame()
        card.setMinimumWidth(220)
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        card.setStyleSheet("""
            QFrame {
                background-color: #0f172a;
                border: 1px solid #334155;
                border-radius: 10px;
                padding: 10px;
            }
            QFrame:hover {
                border: 1px solid #38bdf8;
                background-color: #1e293b;
            }
        """)
        layout = QVBoxLayout(card)
        layout.setSpacing(6)

        # Video Thumbnail Label
        thumb_lbl = QLabel()
        thumb_lbl.setFixedSize(200, 112)
        thumb_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        thumb_lbl.setStyleSheet("background-color: #1e293b; border-radius: 6px; color: #64748b;")
        thumb_lbl.setText("Thumbnail N/A")

        thumb_url = v.get("thumbnail")
        if thumb_url:
            worker = ImageDownloader(thumb_url)
            def on_thumb_downloaded(url, data, lbl=thumb_lbl, w=worker):
                if data:
                    img = QImage()
                    img.loadFromData(data)
                    pixmap = QPixmap.fromImage(img)
                    scaled = pixmap.scaled(200, 112, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
                    lbl.setPixmap(scaled)
                if w in self.image_workers:
                    self.image_workers.remove(w)
            worker.finished_signal.connect(on_thumb_downloaded)
            self.image_workers.append(worker)
            worker.start()

        layout.addWidget(thumb_lbl, 0, Qt.AlignmentFlag.AlignCenter)

        title_lbl = QLabel(v.get("title", "Untitled"))
        title_lbl.setWordWrap(True)
        title_lbl.setFixedHeight(38)
        title_lbl.setStyleSheet("font-weight: bold; font-size: 12px; color: #f8fafc;")
        layout.addWidget(title_lbl)

        views = v.get("views", 0)
        views_str = f"{views:,} views" if views else "Views N/A"
        dur_s = v.get("duration", 0)
        m, s = divmod(dur_s, 60)
        h, m = divmod(m, 60)
        dur_str = f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"

        meta_lbl = QLabel(f"👁 {views_str} | ⏱ {dur_str}")
        meta_lbl.setStyleSheet("color: #94a3b8; font-size: 11px;")
        layout.addWidget(meta_lbl)

        btn_clip = QPushButton("🎬 Clip Video Ini")
        btn_clip.setProperty("class", "primary")
        btn_clip.setStyleSheet("padding: 6px 12px; font-size: 12px; font-weight: bold;")
        url = v.get("url")
        btn_clip.clicked.connect(lambda checked, u=url: self.video_selected_signal.emit(u))
        card.mousePressEvent = lambda e, u=url: self.video_selected_signal.emit(u)

        layout.addWidget(btn_clip)

        return card
