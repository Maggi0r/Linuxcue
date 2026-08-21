from __future__ import annotations

import json
import sys
from datetime import datetime
from functools import partial
from pathlib import Path

QT_IMPORT_ERROR: Exception | None = None
try:
    from PySide6.QtCore import QEvent, QPointF, QRect, QRectF, QSize, QTimer, Qt
    from PySide6.QtGui import QBrush, QColor, QFont, QLinearGradient, QPainter, QPen, QPixmap
    from PySide6.QtWidgets import (
        QApplication,
        QCheckBox,
        QColorDialog,
        QComboBox,
        QFileDialog,
        QFrame,
        QGraphicsDropShadowEffect,
        QGridLayout,
        QHBoxLayout,
        QInputDialog,
        QLabel,
        QListWidget,
        QListWidgetItem,
        QMainWindow,
        QMenu,
        QMessageBox,
        QPushButton,
        QScrollArea,
        QSizePolicy,
        QSlider,
        QSpinBox,
        QStackedWidget,
        QButtonGroup,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )
except Exception as exc:
    QT_IMPORT_ERROR = exc
    QMainWindow = object  # type: ignore[assignment, misc]

from .k95_backend import K95_LAYOUT, K95_OPENRGB_ZONE_ORDER
from .m65_backend import M65_BUTTONS, M65_RGB_ZONES
from .m65_monitor import M65DpiInputMonitor
from .models import AudioPreset, DpiStage, HeadsetSetting, LightingZone
from .service import LinuxCueService


K95_ROWS = [
    [f"led_topzone{index}" for index in range(1, 20)],
    ["preset", "lock", "brightness", "mute"],
    ["g1", "esc", "f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8", "f9", "f10", "f11", "f12", "printscreen", "scrolllock", "pause", "stop", "prev", "play", "next"],
    ["g2", "grave", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "minus", "equals", "backspace", "insert", "home", "pageup", "numlock", "kp_slash", "kp_star", "kp_minus"],
    ["g3", "tab", "q", "w", "e", "r", "t", "y", "u", "i", "o", "p", "lbracket", "rbracket", "enter", "delete", "end", "pagedown", "kp7", "kp8", "kp9", "kp_plus"],
    ["g4", "caps", "a", "s", "d", "f", "g", "h", "j", "k", "l", "semicolon", "quote", "iso_slash", "kp4", "kp5", "kp6"],
    ["g5", "lshift", "iso_backslash", "z", "x", "c", "v", "b", "n", "m", "comma", "period", "slash", "rshift", "up", "kp1", "kp2", "kp3", "kp_enter"],
    ["g6", "lctrl", "lwin", "lalt", "space", "ralt", "rwin", "menu", "rctrl", "left", "down", "right", "kp0", "kp_dot"],
]

K95_GRID_POSITIONS: dict[str, tuple[int, int, int]] = {
    **{f"led_topzone{index}": (0, index + 3, 1) for index in range(1, 20)},
    "preset": (1, 4, 1),
    "lock": (1, 5, 1),
    "brightness": (1, 28, 2),
    "mute": (1, 30, 1),
    "g1": (2, 0, 1),
    "esc": (2, 2, 1),
    "f1": (2, 4, 1),
    "f2": (2, 5, 1),
    "f3": (2, 6, 1),
    "f4": (2, 7, 1),
    "f5": (2, 9, 1),
    "f6": (2, 10, 1),
    "f7": (2, 11, 1),
    "f8": (2, 12, 1),
    "f9": (2, 14, 1),
    "f10": (2, 15, 1),
    "f11": (2, 16, 1),
    "f12": (2, 17, 1),
    "printscreen": (2, 19, 1),
    "scrolllock": (2, 20, 1),
    "pause": (2, 21, 1),
    "stop": (2, 28, 1),
    "prev": (2, 29, 1),
    "play": (2, 30, 1),
    "next": (2, 31, 1),
    "g2": (3, 0, 1),
    "grave": (3, 2, 1),
    "1": (3, 3, 1),
    "2": (3, 4, 1),
    "3": (3, 5, 1),
    "4": (3, 6, 1),
    "5": (3, 7, 1),
    "6": (3, 8, 1),
    "7": (3, 9, 1),
    "8": (3, 10, 1),
    "9": (3, 11, 1),
    "0": (3, 12, 1),
    "minus": (3, 13, 1),
    "equals": (3, 14, 1),
    "backspace": (3, 15, 2),
    "insert": (3, 19, 1),
    "home": (3, 20, 1),
    "pageup": (3, 21, 1),
    "numlock": (3, 23, 1),
    "kp_slash": (3, 24, 1),
    "kp_star": (3, 25, 1),
    "kp_minus": (3, 26, 1),
    "g3": (4, 0, 1),
    "tab": (4, 2, 2),
    "q": (4, 4, 1),
    "w": (4, 5, 1),
    "e": (4, 6, 1),
    "r": (4, 7, 1),
    "t": (4, 8, 1),
    "y": (4, 9, 1),
    "u": (4, 10, 1),
    "i": (4, 11, 1),
    "o": (4, 12, 1),
    "p": (4, 13, 1),
    "lbracket": (4, 14, 1),
    "rbracket": (4, 15, 1),
    "backslash": (4, 16, 1),
    "enter": (4, 17, 1),
    "delete": (4, 19, 1),
    "end": (4, 20, 1),
    "pagedown": (4, 21, 1),
    "kp7": (4, 23, 1),
    "kp8": (4, 24, 1),
    "kp9": (4, 25, 1),
    "kp_plus": (4, 26, 1),
    "g4": (5, 0, 1),
    "caps": (5, 2, 2),
    "a": (5, 4, 1),
    "s": (5, 5, 1),
    "d": (5, 6, 1),
    "f": (5, 7, 1),
    "g": (5, 8, 1),
    "h": (5, 9, 1),
    "j": (5, 10, 1),
    "k": (5, 11, 1),
    "l": (5, 12, 1),
    "semicolon": (5, 13, 1),
    "quote": (5, 14, 1),
    "iso_slash": (5, 15, 1),
    "kp4": (5, 23, 1),
    "kp5": (5, 24, 1),
    "kp6": (5, 25, 1),
    "g5": (6, 0, 1),
    "lshift": (6, 2, 2),
    "iso_backslash": (6, 4, 1),
    "z": (6, 5, 1),
    "x": (6, 6, 1),
    "c": (6, 7, 1),
    "v": (6, 8, 1),
    "b": (6, 9, 1),
    "n": (6, 10, 1),
    "m": (6, 11, 1),
    "comma": (6, 12, 1),
    "period": (6, 13, 1),
    "slash": (6, 14, 1),
    "rshift": (6, 15, 2),
    "up": (6, 20, 1),
    "kp1": (6, 23, 1),
    "kp2": (6, 24, 1),
    "kp3": (6, 25, 1),
    "kp_enter": (6, 26, 1),
    "g6": (7, 0, 1),
    "lctrl": (7, 2, 1),
    "lwin": (7, 3, 1),
    "lalt": (7, 4, 1),
    "space": (7, 5, 6),
    "ralt": (7, 11, 1),
    "rwin": (7, 12, 1),
    "menu": (7, 13, 1),
    "rctrl": (7, 14, 1),
    "left": (7, 19, 1),
    "down": (7, 20, 1),
    "right": (7, 21, 1),
    "kp0": (7, 23, 2),
    "kp_dot": (7, 25, 1),
}

K95_KEY_WIDTHS = {
    "backspace": 86,
    "tab": 64,
    "caps": 72,
    "enter": 84,
    "lshift": 84,
    "rshift": 84,
    "space": 260,
    "kp_plus": 70,
    "kp_enter": 78,
    "brightness": 90,
    "vol_wheel": 90,
    "numlock": 76,
    "printscreen": 78,
    "scrolllock": 78,
    "pause": 78,
    "lock": 54,
    "preset": 60,
    "iso_slash": 48,
    "iso_backslash": 48,
    "rwin": 48,
    **{f"led_topzone{index}": 34 for index in range(1, 20)},
}

K95_LABELS = {
    "grave": "^",
    "minus": "-",
    "equals": "=",
    "lbracket": "[",
    "rbracket": "]",
    "semicolon": ";",
    "quote": "'",
    "comma": ",",
    "period": ".",
    "slash": "/",
    "backslash": "\\",
    "iso_slash": "<>",
    "iso_backslash": "#",
    "printscreen": "PRINT",
    "scrolllock": "SCROLL",
    "pause": "PAUSE",
    "brightness": "BRIGHT",
    "vol_wheel": "VOL",
    "lock": "LOCK",
    "prev": "PREV",
    "play": "PLAY",
    "next": "NEXT",
    "kp_slash": "NUM /",
    "kp_star": "NUM *",
    "kp_minus": "NUM -",
    "kp_plus": "+",
    "kp_enter": "ENTER",
    "kp_dot": ".",
    **{f"kp{index}": str(index) for index in range(10)},
    **{f"led_topzone{index}": "" for index in range(1, 20)},
}

PALETTE = ["#04ff00", "#00c2ff", "#1ecfdf", "#eb1fe3", "#ff001f", "#fff000", "#0064ff", "#ffffff", "#000000"]
EQ_BANDS = ["31", "62", "125", "250", "500", "1k", "2k", "4k", "8k", "16k"]
M65_ACTIONS = ["left", "right", "middle", "dpi_up", "dpi_down", "sniper", "forward", "back", "disabled"]
M65_LABELS = {
    "left": "Linksklick",
    "right": "Rechtsklick",
    "middle": "Mausrad",
    "dpi_up": "DPI hoch",
    "dpi_down": "DPI runter",
    "sniper": "Sniper",
    "forward": "Vor",
    "back": "Zurueck",
    "disabled": "Deaktiviert",
}


if QT_IMPORT_ERROR is None:
    class DeviceCardButton(QPushButton):
        def __init__(
            self,
            title: str,
            subtitle: str,
            meta: str,
            state: str,
            pixmap: QPixmap,
            parent: QWidget | None = None,
        ) -> None:
            super().__init__(parent)
            self.title = title
            self.subtitle = subtitle
            self.meta = meta
            self.state = state
            self.pixmap = pixmap
            self.setCheckable(True)
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            self.setMinimumSize(232, 132)
            self.setMaximumSize(286, 150)
            self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

        def sizeHint(self) -> QSize:
            return QSize(258, 138)

        def paintEvent(self, _event) -> None:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            rect = QRectF(self.rect()).adjusted(1.5, 1.5, -1.5, -1.5)
            checked = self.isChecked()

            bg = QLinearGradient(rect.topLeft(), rect.bottomRight())
            if checked:
                bg.setColorAt(0.0, QColor("#173c46"))
                bg.setColorAt(0.55, QColor("#111f26"))
                bg.setColorAt(1.0, QColor("#0a1115"))
                border = QColor("#12e8ff")
            else:
                bg.setColorAt(0.0, QColor("#202a31"))
                bg.setColorAt(0.55, QColor("#151c21"))
                bg.setColorAt(1.0, QColor("#0b1013"))
                border = QColor("#273a42")
            painter.setPen(QPen(border, 1.2))
            painter.setBrush(QBrush(bg))
            painter.drawRoundedRect(rect, 14, 14)

            painter.setPen(QPen(QColor("#12e8ff" if checked else "#30464f"), 1))
            painter.drawLine(int(rect.left()) + 18, int(rect.bottom()) - 28, int(rect.right()) - 18, int(rect.bottom()) - 28)

            if not self.pixmap.isNull():
                target = QRectF(rect.left() + 18, rect.top() + 22, 104, 62)
                scaled = self.pixmap.scaled(
                    int(target.width()),
                    int(target.height()),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                x = int(target.left() + (target.width() - scaled.width()) / 2)
                y = int(target.top() + (target.height() - scaled.height()) / 2)
                painter.drawPixmap(x, y, scaled)

            painter.setPen(QColor("#55f2ff" if checked else "#f2f7f8"))
            painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            text_x = int(rect.left()) + 136
            painter.drawText(text_x, int(rect.top()) + 28, self.title)

            painter.setPen(QColor("#d7edf0"))
            painter.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
            painter.drawText(text_x, int(rect.top()) + 48, self.subtitle)
            painter.drawText(text_x, int(rect.top()) + 66, self.meta)

            state_color = QColor("#57d967") if "online" in self.state else QColor("#f2c94c")
            painter.setBrush(QBrush(state_color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(int(rect.right()) - 30, int(rect.top()) + 18, 10, 10)

            painter.setPen(QColor("#c6d4d9"))
            painter.setFont(QFont("Segoe UI", 8))
            painter.drawText(int(rect.left()) + 20, int(rect.bottom()) - 10, self.state)
            painter.end()


    class KeyboardSelectionSurface(QWidget):
        def __init__(self, owner: "QtLinuxCueGui") -> None:
            super().__init__()
            self.owner = owner
            self.drag_origin = None
            self.drag_rect = QRect()
            self.setMouseTracking(True)

        def mousePressEvent(self, event) -> None:
            if event.button() == Qt.MouseButton.LeftButton:
                self.drag_origin = event.position().toPoint()
                self.drag_rect = QRect(self.drag_origin, self.drag_origin)
                self.update()
                event.accept()
                return
            super().mousePressEvent(event)

        def mouseMoveEvent(self, event) -> None:
            if self.drag_origin is not None:
                self.drag_rect = QRect(self.drag_origin, event.position().toPoint()).normalized()
                self.update()
                event.accept()
                return
            super().mouseMoveEvent(event)

        def mouseReleaseEvent(self, event) -> None:
            if event.button() == Qt.MouseButton.LeftButton and self.drag_origin is not None:
                rect = QRect(self.drag_origin, event.position().toPoint()).normalized()
                self.drag_origin = None
                self.drag_rect = QRect()
                if rect.width() > 8 or rect.height() > 8:
                    keys = [
                        key
                        for key, button in self.owner.k95_buttons.items()
                        if rect.intersects(button.geometry())
                    ]
                    if keys:
                        self.owner.select_k95_keys(keys)
                self.update()
                event.accept()
                return
            super().mouseReleaseEvent(event)

        def paintEvent(self, event) -> None:
            super().paintEvent(event)
            if self.drag_origin is None or self.drag_rect.isNull():
                return
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setPen(QPen(QColor("#d7ff37"), 2))
            painter.setBrush(QBrush(QColor(215, 255, 55, 38)))
            painter.drawRoundedRect(QRectF(self.drag_rect), 8, 8)
            painter.end()
else:
    DeviceCardButton = object  # type: ignore[assignment]
    KeyboardSelectionSurface = object  # type: ignore[assignment]


class QtLinuxCueGui(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.service = LinuxCueService()
        self.current_profile = None
        self.current_name = ""
        self.current_device_filter = "k95"
        self.current_k95_section = "lighting"
        self.current_virtuoso_section = "audio"
        self.device_status_cache: dict[str, object] | None = None
        self.device_status_signature = ""
        self.k95_buttons: dict[str, QPushButton] = {}
        self.k95_zones: dict[str, LightingZone] = {}
        self.virtuoso_eq_sliders: list[QSlider] = []
        self.virtuoso_eq_values: list[QLabel] = []
        self.virtuoso_loading = False
        self.virtuoso_auto_eq = True
        self.m65_loading = False
        self.m65_pending_packet_kind = "all"
        self.m65_dpi_monitor = M65DpiInputMonitor()
        self.m65_dpi_group = QButtonGroup(self)
        self.m65_dpi_group.setExclusive(True)
        self.m65_dpi_rows: list[dict[str, object]] = []
        self.m65_button_combos: dict[str, QComboBox] = {}
        self.m65_rgb_buttons: dict[str, QPushButton] = {}
        self.selected_key = ""
        self.selected_keys: set[str] = set()
        self.live_timer = QTimer(self)
        self.live_timer.setSingleShot(True)
        self.live_timer.timeout.connect(self._write_current_live_silent)
        self.profile_write_timer = QTimer(self)
        self.profile_write_timer.setSingleShot(True)
        self.profile_write_timer.timeout.connect(self._write_current_live_silent)
        self.m65_write_timer = QTimer(self)
        self.m65_write_timer.setSingleShot(True)
        self.m65_write_timer.timeout.connect(self._write_m65_pending_live_silent)
        self.m65_input_timer = QTimer(self)
        self.m65_input_timer.timeout.connect(self.poll_m65_dpi_input)
        self.virtuoso_eq_timer = QTimer(self)
        self.virtuoso_eq_timer.setSingleShot(True)
        self.virtuoso_eq_timer.timeout.connect(self.apply_virtuoso_linux_eq_silent)
        self.hotplug_timer = QTimer(self)
        self.hotplug_timer.timeout.connect(self.refresh_devices)
        self.loading_profiles = False

        self.setWindowTitle("linuxcue Studio")
        self.resize(1540, 930)
        self.setMinimumSize(1180, 760)
        self._build_ui()
        self.refresh_profiles()
        self.refresh_devices()
        self.hotplug_timer.start(2500)

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Delete and self.profile_list.hasFocus():
            self.delete_current_profile()
            return
        super().keyPressEvent(event)

    def eventFilter(self, watched, event) -> bool:
        if getattr(watched, "objectName", lambda: "")() == "KeyButton":
            key = getattr(watched, "linuxcue_key", "")
            if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                self.keyboard_surface.drag_origin = watched.mapTo(self.keyboard_surface, event.position().toPoint())
                self.keyboard_surface.drag_rect = QRect(self.keyboard_surface.drag_origin, self.keyboard_surface.drag_origin)
                self.keyboard_surface.update()
                return False
            if event.type() == QEvent.Type.MouseMove and self.keyboard_surface.drag_origin is not None:
                point = watched.mapTo(self.keyboard_surface, event.position().toPoint())
                self.keyboard_surface.drag_rect = QRect(self.keyboard_surface.drag_origin, point).normalized()
                self.keyboard_surface.update()
                return True
            if event.type() == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton and self.keyboard_surface.drag_origin is not None:
                point = watched.mapTo(self.keyboard_surface, event.position().toPoint())
                rect = QRect(self.keyboard_surface.drag_origin, point).normalized()
                self.keyboard_surface.drag_origin = None
                self.keyboard_surface.drag_rect = QRect()
                if rect.width() > 8 or rect.height() > 8:
                    keys = [
                        name
                        for name, button in self.k95_buttons.items()
                        if rect.intersects(button.geometry())
                    ]
                    if keys:
                        self.select_k95_keys(keys)
                    self.keyboard_surface.update()
                    return True
                if key:
                    self.select_k95_key(str(key))
                    self.keyboard_surface.update()
                    return True
        return super().eventFilter(watched, event)

    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("Root")
        self.setCentralWidget(root)
        shell = QHBoxLayout(root)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)

        self.sidebar = QFrame()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(296)
        self._add_shadow(self.sidebar, blur=34, y=0, alpha=120)
        side = QVBoxLayout(self.sidebar)
        side.setContentsMargins(18, 18, 14, 14)
        side.setSpacing(14)
        side.addWidget(self._title("linuxcue", "Corsair control for Linux"))
        profiles_title = QLabel("PROFILES")
        profiles_title.setObjectName("SectionTitle")
        side.addWidget(profiles_title)
        self.profile_list = QListWidget()
        self.profile_list.setObjectName("ProfileList")
        self.profile_list.currentItemChanged.connect(self._profile_changed)
        self.profile_list.itemClicked.connect(self._profile_clicked)
        self.profile_list.itemDoubleClicked.connect(self._profile_clicked)
        self.profile_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.profile_list.customContextMenuRequested.connect(self.show_profile_context_menu)
        side.addWidget(self.profile_list, 1)
        live_hint = QLabel("Profil anklicken: Auto Live Write sendet direkt an verbundene Hardware.")
        live_hint.setObjectName("SidebarHint")
        live_hint.setWordWrap(True)
        side.addWidget(live_hint)
        side.addLayout(self._sidebar_buttons())
        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("Status")
        self.status_label.setWordWrap(True)
        side.addWidget(self.status_label)
        shell.addWidget(self.sidebar)

        main = QFrame()
        main.setObjectName("Main")
        layout = QVBoxLayout(main)
        layout.setContentsMargins(14, 14, 14, 10)
        layout.setSpacing(10)
        self._header()
        self.device_tabs = QHBoxLayout()
        self.device_tabs.setSpacing(10)
        layout.addLayout(self.device_tabs)
        self.stack = QStackedWidget()
        self.stack.setObjectName("Stack")
        layout.addWidget(self.stack, 1)
        layout.addWidget(self._actions())
        self._build_k95_page()
        self._build_m65_page()
        self._build_virtuoso_page()
        self._build_generic_page()
        self._build_blank_device_page()
        self._populate_device_tabs()
        shell.addWidget(main, 1)
        self.setStyleSheet(STYLESHEET)

    def _title(self, title: str, subtitle: str) -> QWidget:
        box = QFrame()
        box.setObjectName("Brand")
        layout = QHBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 8)
        layout.setSpacing(12)
        mark = QLabel("lc")
        mark.setObjectName("BrandMark")
        title_label = QLabel(title)
        title_label.setObjectName("AppTitle")
        sub = QLabel(subtitle)
        sub.setObjectName("Muted")
        text = QVBoxLayout()
        text.setContentsMargins(0, 0, 0, 0)
        text.setSpacing(0)
        text.addWidget(title_label)
        text.addWidget(sub)
        layout.addWidget(mark)
        layout.addLayout(text, 1)
        return box

    def _header(self) -> QWidget:
        frame = QWidget()
        self.profile_title = QLabel("No profile selected")
        self.profile_title.setObjectName("HeroTitle")
        self.profile_title.hide()
        self.profile_subtitle = QLabel("Importiere oder waehle ein Profil.")
        self.profile_subtitle.setObjectName("HeroSub")
        self.profile_subtitle.hide()
        return frame

    def _sidebar_buttons(self) -> QVBoxLayout:
        layout = QVBoxLayout()
        row = QHBoxLayout()
        for text, slot in (("Import", self.import_icue), ("Refresh", self.refresh_profiles)):
            button = QPushButton(text)
            button.clicked.connect(slot)
            row.addWidget(button)
        layout.addLayout(row)
        return layout

    def show_profile_context_menu(self, position) -> None:
        item = self.profile_list.itemAt(position)
        if item is not None:
            self.profile_list.setCurrentItem(item)
        menu = QMenu(self)
        new_action = menu.addAction("Neues Profil")
        new_action.triggered.connect(self.create_profile_from_menu)
        if item is not None:
            menu.addSeparator()
            delete_action = menu.addAction("Profil loeschen")
            delete_action.triggered.connect(self.delete_current_profile)
        menu.exec(self.profile_list.mapToGlobal(position))

    def create_profile_from_menu(self) -> None:
        labels = {
            "K95 RGB Platinum": "k95",
            "M65 Pro RGB": "m65",
            "Virtuoso SE": "virtuoso-se",
        }
        choice, ok = QInputDialog.getItem(self, "Neues Profil", "Geraet waehlen:", list(labels), 0, False)
        if not ok or not choice:
            return
        name, ok = QInputDialog.getText(self, "Neues Profil", "Profilname:")
        if not ok:
            return
        name = name.strip() or f"{labels[choice]}-{datetime.now():%H%M%S}"
        profile = self.service.create_profile_for_target(labels[choice], name)
        if labels[choice] == "k95":
            self._ensure_k95_per_key_lighting(profile)
        self.service.save_profile(profile)
        self.current_name = name
        self.refresh_profiles()
        self._select_profile_item_by_user_role(name)
        self.show_profile(name)
        self.set_status(f"Profil erstellt: {name}")

    def delete_current_profile(self) -> None:
        item = self.profile_list.currentItem()
        if item is None:
            return
        label = item.text().splitlines()[0]
        name = label
        loaded = self.service.load_profile(label)
        if loaded is None:
            name = str(item.data(Qt.ItemDataRole.UserRole) or label)
        if not QMessageBox.question(
            self,
            "Profil loeschen",
            f"Profil '{label}' wirklich loeschen?",
        ) == QMessageBox.StandardButton.Yes:
            return
        if not self.service.delete_profile(name):
            QMessageBox.warning(self, "linuxcue", f"Profil konnte nicht geloescht werden: {name}")
            return
        if self.current_name == name:
            self.current_name = ""
            self.current_profile = None
        self.refresh_profiles()
        self.set_status(f"Profil geloescht: {name}")

    def _actions(self) -> QWidget:
        frame = QFrame()
        frame.setObjectName("Actions")
        self._add_shadow(frame, blur=30, y=6, alpha=90)
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(18, 12, 18, 12)
        layout.setSpacing(12)
        live_title = QLabel("Live Write")
        live_title.setObjectName("LiveTitle")
        live_sub = QLabel("Aenderungen werden nach Check direkt an die Hardware geschickt.")
        live_sub.setObjectName("Muted")
        title_stack = QVBoxLayout()
        title_stack.addWidget(live_title)
        title_stack.addWidget(live_sub)
        layout.addLayout(title_stack)
        self.auto_write = QCheckBox("Auto Live Write")
        self.auto_write.setObjectName("AutoWrite")
        self.auto_write.setChecked(True)
        self.auto_write.setToolTip("Schreibt Profil- und Farbaenderungen automatisch nach kurzer Pause.")
        layout.addWidget(self.auto_write)
        for step, state in (("1 Validate", "OK"), ("2 Diff", "Ready"), ("3 Backup", "Local"), ("4 Write", "Armed")):
            chip = QLabel(f"{step}\n{state}")
            chip.setObjectName("LiveStep")
            layout.addWidget(chip)
        layout.addStretch(1)
        self.live_status_label = QLabel("Ready")
        self.live_status_label.setObjectName("ReadyBadge")
        layout.addWidget(self.live_status_label)
        for text, slot, primary in (
            ("Live Write", self.write_current_live, True),
            ("Save", self.save_current, False),
            ("Refresh", self.refresh_devices, False),
        ):
            button = QPushButton(text)
            button.setProperty("primary", primary)
            button.clicked.connect(slot)
            layout.addWidget(button)
        return frame

    def _populate_device_tabs(self, status: dict[str, object] | None = None) -> None:
        status = status or self.device_status_cache or {"devices": []}
        while self.device_tabs.count():
            item = self.device_tabs.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        for title, slug, meta, visual in (
            ("K95 RGB Platinum", "k95", "Layout: ISO-DE", "RGB keyboard"),
            ("M65 Pro RGB", "m65", "DPI Profile: Default", "Mouse control"),
            ("Virtuoso SE", "virtuoso-se", "Audio Profile: EasyEffects", "Headset EQ"),
            ("Wireless Receiver", "receiver", "Link + battery status", "USB receiver"),
        ):
            if not self._device_online(slug, status):
                continue
            state = self._device_state_text(slug, status)
            button = DeviceCardButton(
                title=title,
                subtitle=visual,
                meta=meta,
                state=state,
                pixmap=self._device_pixmap(slug, checked=slug == self.current_device_filter),
            )
            button.setObjectName("DeviceTab")
            button.setChecked(slug == self.current_device_filter)
            button.clicked.connect(partial(self.select_device_filter, slug))
            self._add_shadow(button, blur=22, y=6, alpha=85)
            self.device_tabs.addWidget(button)
        if self.device_tabs.count() == 0:
            self.stack.setCurrentWidget(self.blank_device_page)
        else:
            self._sync_stack_for_current_profile_connectivity(status)
        self.device_tabs.addStretch(1)
        return
        for title, slug, meta in (
            ("K95 RGB Platinum", "k95", "Keyboard / ISO-DE   ●"),
            ("M65 Pro RGB", "m65", "DPI + RGB   ●"),
            ("Virtuoso SE", "virtuoso-se", "EQ + Sidetone   ●"),
            ("Wireless Receiver", "receiver", "Wireless link   ●"),
        ):
            button = QPushButton(f"{title}\n{meta}\n{self._device_state_text(slug, status)}")
            button.setObjectName("DeviceTab")
            button.setCheckable(True)
            button.setChecked(slug == self.current_device_filter)
            button.clicked.connect(partial(self.select_device_filter, slug))
            self.device_tabs.addWidget(button)
        self.device_tabs.addStretch(1)

    def _add_shadow(self, widget: QWidget, blur: int = 24, y: int = 5, alpha: int = 85) -> None:
        shadow = QGraphicsDropShadowEffect(widget)
        shadow.setBlurRadius(blur)
        shadow.setOffset(0, y)
        shadow.setColor(QColor(0, 0, 0, alpha))
        widget.setGraphicsEffect(shadow)

    def _device_online(self, slug: str, status: dict[str, object] | None = None) -> bool:
        return self._device_state_text(slug, status) != "offline"

    def _slug_for_profile(self, profile) -> str:
        target_device = str(getattr(profile, "target_device", "")).casefold()
        target_family = str(getattr(profile, "target_family", "")).casefold()
        if target_device == "profile-set":
            return self.current_device_filter
        if "receiver" in target_device or "receiver" in target_family:
            return "receiver"
        if "virtuoso" in target_device or "headset" in target_family:
            return "virtuoso-se"
        if "m65" in target_device or "mouse" in target_family:
            return "m65"
        if "k95" in target_device or "keyboard" in target_family:
            return "k95"
        return ""

    def _profile_device_connected(self, profile, status: dict[str, object] | None = None) -> bool:
        slug = self._slug_for_profile(profile)
        return bool(slug and self._device_online(slug, status))

    def _sync_stack_for_current_profile_connectivity(self, status: dict[str, object] | None = None) -> None:
        if self.current_profile is None:
            self.stack.setCurrentWidget(self.blank_device_page)
            return
        if not self._profile_device_connected(self.current_profile, status):
            self.stack.setCurrentWidget(self.blank_device_page)
            return
        target = self.current_profile.target_device
        if target == "profile-set":
            target = self._slug_for_profile(self.current_profile)
        if target == "k95":
            self.stack.setCurrentWidget(self.k95_page)
        elif target == "m65":
            self.stack.setCurrentWidget(self.m65_page)
        elif target == "virtuoso-se":
            self.stack.setCurrentWidget(self.virtuoso_page)
        else:
            self.stack.setCurrentWidget(self.generic_page)

    def _device_in_current_profile(self, slug: str) -> bool:
        profile = self.current_profile
        if profile is None:
            return False
        if self._profile_matches_slug(profile.target_device, profile.target_family, slug):
            return True
        group = profile.profile_group or (profile.name if profile.target_device == "profile-set" else "")
        if not group:
            return False
        for member in self.service.profiles_in_group(group):
            if self._profile_matches_slug(member.target_device, member.target_family, slug):
                return True
        return False

    @staticmethod
    def _profile_matches_slug(target_device: str, target_family: str, slug: str) -> bool:
        if slug == "receiver":
            return "receiver" in target_device.casefold() or "receiver" in target_family.casefold()
        if slug == "virtuoso-se":
            return "virtuoso" in target_device.casefold() or "headset" in target_family.casefold()
        return slug in target_device.casefold() or slug in target_family.casefold()

    def _device_pixmap(self, slug: str, checked: bool = False) -> QPixmap:
        asset = self._device_image_asset(slug)
        if asset is not None:
            loaded = QPixmap(str(asset))
            if not loaded.isNull():
                return loaded.scaled(130, 70, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        pixmap = QPixmap(130, 70)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        cyan = QColor("#12e8ff" if checked else "#2e8793")
        green = QColor("#57d967")
        dark = QColor("#11181b")
        mid = QColor("#252f34")
        painter.setPen(QPen(QColor("#3c4b51"), 2))
        painter.setBrush(QBrush(dark))
        if slug == "k95":
            painter.drawRoundedRect(8, 12, 114, 42, 6, 6)
            painter.setPen(QPen(cyan, 1))
            for row in range(4):
                for col in range(13):
                    painter.setBrush(QBrush(green if (row + col) % 3 else QColor("#1fc6e2")))
                    painter.drawRoundedRect(16 + col * 8, 19 + row * 7, 6, 5, 2, 2)
            painter.setBrush(QBrush(QColor("#0f1517")))
            painter.drawRect(18, 55, 86, 4)
        elif slug == "m65":
            painter.setBrush(QBrush(mid))
            painter.drawEllipse(42, 7, 48, 55)
            painter.setBrush(QBrush(QColor("#0b0f10")))
            painter.drawRoundedRect(64, 8, 8, 26, 4, 4)
            painter.setBrush(QBrush(QColor("#ffcf55")))
            painter.drawPolygon([QPointF(64, 48), QPointF(75, 56), QPointF(68, 39)])
        elif slug == "virtuoso-se":
            painter.setPen(QPen(cyan, 4))
            painter.drawArc(35, 6, 62, 52, 20 * 16, 140 * 16)
            painter.setPen(QPen(QColor("#3c4b51"), 2))
            painter.setBrush(QBrush(mid))
            painter.drawRoundedRect(27, 33, 23, 25, 8, 8)
            painter.drawRoundedRect(82, 33, 23, 25, 8, 8)
            painter.setPen(QPen(cyan, 2))
            painter.drawLine(92, 58, 118, 64)
        else:
            painter.setBrush(QBrush(mid))
            painter.drawRoundedRect(50, 12, 32, 44, 7, 7)
            painter.setBrush(QBrush(QColor("#d5d9da")))
            painter.drawRect(55, 3, 22, 13)
            painter.setBrush(QBrush(green))
            painter.drawEllipse(62, 38, 9, 9)
        painter.end()
        return pixmap

    def _device_image_asset(self, slug: str) -> Path | None:
        asset_dir = Path(__file__).resolve().parent / "assets" / "devices"
        for suffix in (".png", ".webp", ".jpg", ".jpeg"):
            path = asset_dir / f"{slug}{suffix}"
            if path.exists():
                return path
        return None

    def _device_state_text(self, slug: str, status: dict[str, object] | None = None) -> str:
        status = status or self.device_status_cache or {"devices": []}
        online = any(slug in str(device.get("target", "")).casefold() or slug in str(device.get("family", "")).casefold() for device in status["devices"])
        headset_online = any(
            "virtuoso" in str(device.get("target", "")).casefold()
            and "receiver" not in str(device.get("target", "")).casefold()
            and str(device.get("endpoint_role")) == "headset-hid"
            and bool(device.get("open_ok"))
            for device in status["devices"]
        )
        receiver_online = any(
            "virtuoso" in str(device.get("target", "")).casefold()
            and "receiver" in str(device.get("target", "")).casefold()
            and bool(device.get("open_ok"))
            for device in status["devices"]
        )
        if slug == "virtuoso-se" and headset_online:
            return "online usb hid"
        if slug == "virtuoso-se" and receiver_online:
            return "receiver only"
        return "online" if online else "offline"

    def select_device_filter(self, slug: str) -> None:
        self.current_device_filter = slug
        self._populate_device_tabs()
        self.refresh_profiles()
        target_name = self._profile_name_for_current_device_selection()
        if target_name:
            self._select_profile_item_by_user_role(target_name)
            self.show_profile(target_name)

    def _profile_name_for_current_device_selection(self) -> str:
        if self.current_profile is not None and self.current_profile.target_device == "profile-set":
            return self._profile_name_for_device_selection(self.current_profile.name, "profile-set")
        current_item = self.profile_list.currentItem()
        if current_item is not None:
            visible_name = current_item.text().splitlines()[0]
            profile = self.service.load_profile(visible_name)
            if profile is not None and profile.target_device == "profile-set":
                return self._profile_name_for_device_selection(profile.name, "profile-set")
        for index in range(self.profile_list.count()):
            item = self.profile_list.item(index)
            profile = self.service.load_profile(item.text().splitlines()[0])
            if profile is not None and profile.target_device == "profile-set":
                candidate = self._profile_name_for_device_selection(profile.name, "profile-set")
                if candidate != profile.name:
                    return candidate
        return ""

    def _select_profile_item_by_user_role(self, profile_name: str) -> None:
        for index in range(self.profile_list.count()):
            item = self.profile_list.item(index)
            if str(item.data(Qt.ItemDataRole.UserRole)) == profile_name:
                self.profile_list.setCurrentItem(item)
                return

    def _build_k95_page(self) -> None:
        page = QWidget()
        page.setObjectName("EditorPage")
        layout = QHBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        nav = QFrame()
        nav.setObjectName("DeviceNav")
        nav.setFixedWidth(230)
        nav_layout = QVBoxLayout(nav)
        nav_layout.setContentsMargins(14, 14, 14, 14)
        nav_layout.setSpacing(10)
        nav_title = QLabel("K95 RGB PLATINUM")
        nav_title.setObjectName("DeviceNavTitle")
        nav_layout.addWidget(nav_title)
        self.memory_mode = QCheckBox("Geraetespeichermodus")
        self.memory_mode.setObjectName("AutoWrite")
        self.memory_mode.stateChanged.connect(self.save_k95_options)
        nav_layout.addWidget(self.memory_mode)
        for title, section in (
            ("Beleuchtungseffekte", "lighting"),
            ("Tastenzuweisungen", "keys"),
            ("Optionen", "options"),
        ):
            button = QPushButton(title)
            button.setObjectName("DeviceNavButton")
            button.setCheckable(True)
            button.clicked.connect(partial(self.select_k95_section, section))
            nav_layout.addWidget(button)
            if section == "lighting":
                self.k95_lighting_nav = button
            elif section == "keys":
                self.k95_keys_nav = button
            else:
                self.k95_options_nav = button
        nav_layout.addStretch(1)
        layout.addWidget(nav)

        work = QFrame()
        work.setObjectName("KeyboardPanel")
        work_layout = QVBoxLayout(work)
        work_layout.setContentsMargins(14, 14, 14, 14)
        work_layout.setSpacing(10)
        title_row = QHBoxLayout()
        label = QLabel("K95 RGB Platinum")
        label.setObjectName("PanelTitle")
        title_row.addWidget(label)
        title_row.addStretch(1)
        badge = QLabel("ISO / DE layout map")
        badge.setObjectName("Badge")
        title_row.addWidget(badge)
        work_layout.addLayout(title_row)
        hint = QLabel("Echte K95-Anordnung: G-Block links, Lightbar oben, Media rechts. Farbwechsel werden bei Auto Live Write direkt gesendet.")
        hint.setObjectName("Muted")
        work_layout.addWidget(hint)
        self.k95_content_stack = QStackedWidget()
        self.k95_content_stack.setObjectName("DeviceContentStack")

        lighting_page = QWidget()
        lighting_layout = QHBoxLayout(lighting_page)
        lighting_layout.setContentsMargins(0, 0, 0, 0)
        lighting_layout.setSpacing(12)
        layers = QFrame()
        layers.setObjectName("SubPanel")
        layers.setFixedWidth(230)
        layers_layout = QVBoxLayout(layers)
        layers_layout.setContentsMargins(14, 14, 14, 14)
        layers_layout.setSpacing(10)
        layers_title = QLabel("Lighting Layers")
        layers_title.setObjectName("InspectorTitle")
        layers_layout.addWidget(layers_title)
        for title, subtitle in (
            ("Static Color", "Benutzerdefiniert"),
            ("Color Shift", "Farbwechsel"),
            ("Wave", "Rainbow"),
            ("Reactive", "Tastenreaktion"),
            ("Ambient Light", "Spaeter"),
        ):
            row = QPushButton(f"{title}\n{subtitle}")
            row.setObjectName("LayerButton")
            row.setCheckable(True)
            row.setChecked(title == "Static Color")
            layers_layout.addWidget(row)
        layers_layout.addStretch(1)
        blend = QLabel("Layer Blend\nNormal")
        blend.setObjectName("LiveCard")
        layers_layout.addWidget(blend)
        lighting_layout.addWidget(layers)

        preview = QFrame()
        preview.setObjectName("SubPanel")
        preview_layout = QVBoxLayout(preview)
        preview_layout.setContentsMargins(14, 14, 14, 14)
        preview_layout.setSpacing(10)
        preview_header = QHBoxLayout()
        preview_title = QLabel("Preview")
        preview_title.setObjectName("InspectorTitle")
        preview_header.addWidget(preview_title)
        preview_header.addStretch(1)
        simulate = QPushButton("Apply Simulation")
        simulate.clicked.connect(lambda: self.set_status("Simulation ist lokal; Live Write sendet echte HID-Pakete."))
        preview_header.addWidget(simulate)
        preview_layout.addLayout(preview_header)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName("KeyboardScroll")
        self.keyboard_surface = KeyboardSelectionSurface(self)
        self.keyboard_surface.setObjectName("KeyboardSurface")
        self.keyboard_surface.setMinimumSize(1160, 310)
        scroll.setWidget(self.keyboard_surface)
        preview_layout.addWidget(scroll, 1)
        effects = QFrame()
        effects.setObjectName("InlineControls")
        effects_layout = QHBoxLayout(effects)
        effects_layout.setContentsMargins(10, 8, 10, 8)
        effects_layout.setSpacing(8)
        effects_layout.addWidget(QLabel("Beleuchtungstyp"))
        self.k95_effect_combo = QComboBox()
        self.k95_effect_combo.addItems(["Statische Farbe", "Farbwechsel", "Welle", "Reaktiv"])
        effects_layout.addWidget(self.k95_effect_combo)
        color_wheel = QPushButton("Farbrad / Farbe")
        color_wheel.clicked.connect(self.pick_custom_k95_color)
        effects_layout.addWidget(color_wheel)
        speed = QLabel("Speed  100%")
        speed.setObjectName("Muted")
        effects_layout.addWidget(speed)
        effects_layout.addStretch(1)
        preview_layout.addWidget(effects)
        lighting_layout.addWidget(preview, 1)
        self.k95_content_stack.addWidget(lighting_page)
        self.k95_lighting_page = lighting_page

        keys_page = self._build_k95_placeholder_page(
            "Tastenzuweisungen",
            "Makro- und Tastenbelegung kommt als naechster Mapping-Schritt. Die Ansicht ist schon vorbereitet.",
        )
        self.k95_content_stack.addWidget(keys_page)
        self.k95_keys_page = keys_page

        options_page = self._build_k95_options_page()
        self.k95_content_stack.addWidget(options_page)
        self.k95_options_page = options_page
        work_layout.addWidget(self.k95_content_stack, 1)
        layout.addWidget(work, 1)

        inspector = QFrame()
        inspector.setObjectName("Inspector")
        inspector.setFixedWidth(292)
        side = QVBoxLayout(inspector)
        side.setContentsMargins(16, 16, 16, 16)
        side.setSpacing(12)
        selected_title = QLabel("Selected Key")
        selected_title.setObjectName("InspectorTitle")
        side.addWidget(selected_title)
        self.selected_label = QLabel("Keine Taste ausgewaehlt")
        self.selected_label.setObjectName("SelectedKey")
        self.selected_label.setWordWrap(True)
        side.addWidget(self.selected_label)
        palette_title = QLabel("Palette")
        palette_title.setObjectName("InspectorTitle")
        side.addWidget(palette_title)
        palette_grid = QGridLayout()
        palette_grid.setSpacing(8)
        for index, color in enumerate(PALETTE):
            swatch = QPushButton("")
            swatch.setFixedSize(72, 46)
            swatch.setProperty("swatch", True)
            swatch.setStyleSheet(f"background:{color}; border:1px solid #385648; border-radius:12px;")
            swatch.clicked.connect(partial(self.apply_k95_color, color))
            palette_grid.addWidget(swatch, index // 3, index % 3)
        side.addLayout(palette_grid)
        custom = QPushButton("Custom Color")
        custom.clicked.connect(self.pick_custom_k95_color)
        side.addWidget(custom)
        all_keys = QPushButton("Apply To All Keys")
        all_keys.clicked.connect(self.apply_color_to_all_k95)
        side.addWidget(all_keys)
        self.k95_detail = QLabel("Live Write: Ready\nPackets: -\nDevice: -")
        self.k95_detail.setObjectName("LiveCard")
        self.k95_detail.setWordWrap(True)
        side.addWidget(self.k95_detail, 1)
        layout.addWidget(inspector)
        self.k95_inspector = inspector
        self.stack.addWidget(page)
        self.k95_page = page

    def _build_k95_placeholder_page(self, title: str, text: str) -> QWidget:
        page = QFrame()
        page.setObjectName("SubPanel")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        label = QLabel(title)
        label.setObjectName("PanelTitle")
        body = QLabel(text)
        body.setObjectName("Muted")
        body.setWordWrap(True)
        layout.addWidget(label)
        layout.addWidget(body)
        layout.addStretch(1)
        return page

    def _build_k95_options_page(self) -> QWidget:
        page = QWidget()
        layout = QHBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        option_card = QFrame()
        option_card.setObjectName("SubPanel")
        left = QVBoxLayout(option_card)
        left.setContentsMargins(20, 20, 20, 20)
        left.setSpacing(12)
        options_title = QLabel("Optionen")
        options_title.setObjectName("InspectorTitle")
        left.addWidget(options_title)
        winlock_label = QLabel("WIN-LOCK Verhalten")
        winlock_label.setObjectName("PanelTitle")
        left.addWidget(winlock_label)
        state = QLabel("Needs capture")
        state.setObjectName("AmberBadge")
        left.addWidget(state)
        self.k95_option_alt_tab = QCheckBox("Alt+Tab deaktivieren")
        self.k95_option_alt_f4 = QCheckBox("Alt+F4 deaktivieren")
        self.k95_option_shift_tab = QCheckBox("Umschalt+Tab deaktivieren")
        self.k95_option_win_key = QCheckBox("WINDOWS-TASTE deaktivieren")
        for checkbox in (self.k95_option_alt_tab, self.k95_option_alt_f4, self.k95_option_shift_tab, self.k95_option_win_key):
            checkbox.setObjectName("AutoWrite")
            checkbox.stateChanged.connect(self.save_k95_options)
            left.addWidget(checkbox)
        behavior_note = QLabel("Diese Schalter werden im Profil gespeichert. Die K95-Special-Function/ISO-Initialisierung ist sendbar; die einzelnen Sperr-Bits brauchen noch einen iCUE-Capture.")
        behavior_note.setObjectName("WarningNote")
        behavior_note.setWordWrap(True)
        left.addWidget(behavior_note)
        sync_row = QHBoxLayout()
        sync = QPushButton("Options Sync")
        sync.setProperty("primary", True)
        sync.clicked.connect(self.k95_options_sync)
        sync_row.addWidget(sync)
        hardware = QPushButton("Hardware Mode")
        hardware.clicked.connect(self.k95_hardware_mode)
        sync_row.addWidget(hardware)
        left.addLayout(sync_row)
        capture = QPushButton("Capture Plan anzeigen")
        capture.clicked.connect(self.show_k95_options_capture_plan)
        left.addWidget(capture)
        left.addStretch(1)
        reset = QPushButton("Standard wiederherstellen")
        reset.clicked.connect(self.reset_k95_options)
        left.addWidget(reset)
        layout.addWidget(option_card)

        colors_card = QFrame()
        colors_card.setObjectName("SubPanel")
        colors_card.setMaximumWidth(380)
        right = QVBoxLayout(colors_card)
        right.setContentsMargins(20, 20, 20, 20)
        right.setSpacing(10)
        colors_title = QLabel("Anzeigefarben")
        colors_title.setObjectName("InspectorTitle")
        right.addWidget(colors_title)
        known = QLabel("Live mapped")
        known.setObjectName("GreenBadge")
        right.addWidget(known)
        self.lock_on_color = self._option_color_button("Sperren Ein", "lock_on", "lock")
        self.lock_off_color = self._option_color_button("Sperren Aus", "lock_off", "")
        self.brightness_color = self._option_color_button("Helligkeit", "brightness", "brightness")
        self.profile_color = self._option_color_button("Profil", "profile", "preset")
        color_grid = QGridLayout()
        color_grid.setSpacing(10)
        for index, button in enumerate((self.lock_on_color, self.lock_off_color, self.brightness_color, self.profile_color)):
            color_grid.addWidget(button, index // 2, index % 2)
        right.addLayout(color_grid)
        color_note = QLabel("Lock, Helligkeit und Profil schreiben direkt auf die passenden K95-Anzeige-LEDs. Sperren Aus wird gespeichert, bis der echte Lock-State lesbar ist.")
        color_note.setObjectName("WarningNote")
        color_note.setWordWrap(True)
        right.addWidget(color_note)
        right.addStretch(1)
        layout.addWidget(colors_card)
        return page

    def _option_color_button(self, label: str, option_key: str, target_zone: str) -> QPushButton:
        button = QPushButton(label)
        button.setObjectName("ColorOptionButton")
        button.setMinimumHeight(38)
        button.setMaximumHeight(44)
        button.clicked.connect(partial(self.pick_k95_indicator_color, option_key, target_zone))
        return button

    def select_m65_section(self, section: str) -> None:
        pages = {
            "dpi": self.m65_dpi_page,
            "buttons": self.m65_buttons_page,
            "rgb": self.m65_rgb_page,
        }
        self.m65_content_stack.setCurrentWidget(pages.get(section, self.m65_dpi_page))
        for button, name in (
            (self.m65_dpi_nav, "dpi"),
            (self.m65_buttons_nav, "buttons"),
            (self.m65_rgb_nav, "rgb"),
        ):
            button.setChecked(name == section)

    def _build_m65_page(self) -> None:
        page = QWidget()
        page.setObjectName("EditorPage")
        layout = QHBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        nav = QFrame()
        nav.setObjectName("DeviceNav")
        nav.setFixedWidth(260)
        nav_layout = QVBoxLayout(nav)
        nav_layout.setContentsMargins(16, 16, 16, 16)
        nav_layout.setSpacing(12)
        title = QLabel("M65 PRO RGB")
        title.setObjectName("DeviceNavTitle")
        nav_layout.addWidget(title)
        for label, section in (("DPI Stages", "dpi"), ("Native Buttons", "buttons"), ("RGB Zones", "rgb")):
            button = QPushButton(label)
            button.setObjectName("DeviceNavButton")
            button.setCheckable(True)
            button.setChecked(section == "dpi")
            button.clicked.connect(partial(self.select_m65_section, section))
            nav_layout.addWidget(button)
            if section == "dpi":
                self.m65_dpi_nav = button
            elif section == "buttons":
                self.m65_buttons_nav = button
            else:
                self.m65_rgb_nav = button
        nav_layout.addStretch(1)
        layout.addWidget(nav)

        center = QFrame()
        center.setObjectName("KeyboardPanel")
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(18, 18, 18, 18)
        center_layout.setSpacing(14)
        head = QHBoxLayout()
        heading = QLabel("M65 Pro RGB")
        heading.setObjectName("PanelTitle")
        head.addWidget(heading)
        head.addStretch(1)
        badge = QLabel("DPI + RGB + native buttons")
        badge.setObjectName("Badge")
        head.addWidget(badge)
        center_layout.addLayout(head)
        hint = QLabel("RGB ist capture-basiert gemappt. DPI setzt aktuell den aktiven Slot; echte DPI-Werte im Geraetespeicher brauchen noch einen iCUE-Onboard-Capture.")
        hint.setObjectName("Muted")
        center_layout.addWidget(hint)

        hero = QLabel("M65 Pro RGB\nActive DPI: -\nLogo: -")
        hero.setObjectName("DeviceHeroCard")
        hero.setWordWrap(True)
        self.m65_preview = hero
        center_layout.addWidget(hero)

        self.m65_content_stack = QStackedWidget()
        self.m65_content_stack.setObjectName("DeviceContentStack")

        dpi_page = QFrame()
        dpi_page.setObjectName("SubPanel")
        dpi_layout = QVBoxLayout(dpi_page)
        dpi_layout.setContentsMargins(18, 18, 18, 18)
        dpi_title = QLabel("DPI Stages")
        dpi_title.setObjectName("InspectorTitle")
        dpi_layout.addWidget(dpi_title)
        dpi_note = QLabel(
            "Live Write waehlt und speichert den aktiven DPI-Slot. Die DPI-Werte selbst liegen im Geraetespeicher; "
            "deren komplettes Schreibformat braucht noch einen separaten Speicher-Capture."
        )
        dpi_note.setObjectName("Muted")
        dpi_note.setWordWrap(True)
        dpi_layout.addWidget(dpi_note)
        self.m65_dpi_rows.clear()
        self.m65_dpi_group = QButtonGroup(self)
        self.m65_dpi_group.setExclusive(True)
        for index in range(5):
            row = QHBoxLayout()
            active = QCheckBox("Active")
            active.setObjectName("AutoWrite")
            active.clicked.connect(partial(self.activate_m65_dpi_stage, index))
            self.m65_dpi_group.addButton(active, index)
            name = QLabel(f"Stage {index + 1}")
            name.setMinimumWidth(78)
            x_value = QSpinBox()
            y_value = QSpinBox()
            for spin in (x_value, y_value):
                spin.setRange(100, 18000)
                spin.setSingleStep(50)
                spin.editingFinished.connect(partial(self.save_m65_from_ui, "dpi"))
            color_button = QPushButton("#ffffff")
            color_button.clicked.connect(partial(self.pick_m65_dpi_color, index))
            row.addWidget(active)
            row.addWidget(name)
            row.addWidget(QLabel("X"))
            row.addWidget(x_value)
            row.addWidget(QLabel("Y"))
            row.addWidget(y_value)
            row.addWidget(color_button)
            dpi_layout.addLayout(row)
            self.m65_dpi_rows.append({"active": active, "x": x_value, "y": y_value, "color": color_button})
        dpi_layout.addStretch(1)
        self.m65_content_stack.addWidget(dpi_page)
        self.m65_dpi_page = dpi_page

        buttons_page = QFrame()
        buttons_page.setObjectName("SubPanel")
        buttons_layout = QVBoxLayout(buttons_page)
        buttons_layout.setContentsMargins(18, 18, 18, 18)
        buttons_title = QLabel("Native Buttons")
        buttons_title.setObjectName("InspectorTitle")
        buttons_layout.addWidget(buttons_title)
        buttons_note = QLabel(
            "Die Hauptfunktionen laufen direkt in der M65-Hardware: Linksklick, Rechtsklick, Mausrad, "
            "DPI hoch/runter, Sniper sowie Vor/Zurueck. iCUE-Zusatzbelegungen wurden im Capture nicht "
            "als HID-Write sichtbar und bleiben deshalb vorerst deaktiviert."
        )
        buttons_note.setObjectName("Muted")
        buttons_note.setWordWrap(True)
        buttons_layout.addWidget(buttons_note)
        self.m65_button_combos.clear()
        for button_name in M65_BUTTONS:
            row = QHBoxLayout()
            label = QLabel(M65_LABELS.get(button_name, button_name))
            label.setMinimumWidth(120)
            combo = QComboBox()
            combo.addItem(f"{M65_LABELS.get(button_name, button_name)} (Hardware)", button_name)
            combo.setEnabled(False)
            combo.setToolTip("Native M65-Funktion: kein linuxcue-Hardware-Remap erforderlich.")
            row.addWidget(label)
            row.addWidget(combo, 1)
            buttons_layout.addLayout(row)
            self.m65_button_combos[button_name] = combo
        buttons_layout.addStretch(1)
        self.m65_content_stack.addWidget(buttons_page)
        self.m65_buttons_page = buttons_page

        rgb_page = QFrame()
        rgb_page.setObjectName("SubPanel")
        rgb_layout = QVBoxLayout(rgb_page)
        rgb_layout.setContentsMargins(18, 18, 18, 18)
        rgb_title = QLabel("RGB Zones")
        rgb_title.setObjectName("InspectorTitle")
        rgb_layout.addWidget(rgb_title)
        self.m65_rgb_buttons.clear()
        for zone_name in M65_RGB_ZONES:
            button = QPushButton(zone_name.replace("_", " ").title())
            button.setMinimumHeight(70)
            button.clicked.connect(partial(self.pick_m65_zone_color, zone_name))
            rgb_layout.addWidget(button)
            self.m65_rgb_buttons[zone_name] = button
        rgb_layout.addStretch(1)
        self.m65_content_stack.addWidget(rgb_page)
        self.m65_rgb_page = rgb_page

        center_layout.addWidget(self.m65_content_stack, 1)
        layout.addWidget(center, 1)

        inspector = QFrame()
        inspector.setObjectName("Inspector")
        inspector.setFixedWidth(320)
        side = QVBoxLayout(inspector)
        side.setContentsMargins(16, 16, 16, 16)
        side.setSpacing(12)
        apply_button = QPushButton("Live Write M65")
        apply_button.setProperty("primary", True)
        apply_button.clicked.connect(self.write_current_live)
        side.addWidget(apply_button)
        kind_row = QHBoxLayout()
        kind_row.setSpacing(8)
        for label, packet_kind in (("DPI", "dpi"), ("RGB", "rgb")):
            kind_button = QPushButton(label)
            kind_button.clicked.connect(partial(self.write_m65_kind_live, packet_kind))
            kind_row.addWidget(kind_button)
        side.addLayout(kind_row)
        self.m65_detail = QLabel("M65 Ready\nPackets: -\nMapping: experimental")
        self.m65_detail.setObjectName("LiveCard")
        self.m65_detail.setWordWrap(True)
        side.addWidget(self.m65_detail, 1)
        layout.addWidget(inspector)
        self.stack.addWidget(page)
        self.m65_page = page

    def _build_virtuoso_page(self) -> None:
        page = QWidget()
        page.setObjectName("EditorPage")
        layout = QHBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        nav = QFrame()
        nav.setObjectName("DeviceNav")
        nav.setFixedWidth(260)
        nav_layout = QVBoxLayout(nav)
        nav_layout.setContentsMargins(16, 16, 16, 16)
        nav_layout.setSpacing(12)
        title = QLabel("VIRTUOSO SE")
        title.setObjectName("DeviceNavTitle")
        nav_layout.addWidget(title)
        for label, section, active in (
            ("EQ / Audio", "audio", True),
            ("Beleuchtung", "lighting", False),
            ("Wireless Receiver", "receiver", False),
        ):
            button = QPushButton(label)
            button.setObjectName("DeviceNavButton")
            button.setCheckable(True)
            button.setChecked(active)
            button.clicked.connect(partial(self.select_virtuoso_section, section))
            nav_layout.addWidget(button)
            if section == "audio":
                self.virtuoso_audio_nav = button
            elif section == "lighting":
                self.virtuoso_lighting_nav = button
            else:
                self.virtuoso_receiver_nav = button
        nav_layout.addStretch(1)
        layout.addWidget(nav)

        center = QFrame()
        center.setObjectName("KeyboardPanel")
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(18, 18, 18, 18)
        center_layout.setSpacing(14)
        head = QHBoxLayout()
        heading = QLabel("Virtuoso SE")
        heading.setObjectName("PanelTitle")
        head.addWidget(heading)
        head.addStretch(1)
        badge = QLabel("EQ + RGB mapped")
        badge.setObjectName("Badge")
        head.addWidget(badge)
        center_layout.addLayout(head)
        hint = QLabel("10-Band Equalizer, Accent-Ring und Headset-Regler. Aenderungen werden bei Auto Live Write direkt gespeichert und gesendet.")
        hint.setObjectName("Muted")
        center_layout.addWidget(hint)

        top_cards = QHBoxLayout()
        self.virtuoso_preview = QLabel("Virtuoso SE\nAudio Profile: Default\nAccent Ring: -")
        self.virtuoso_preview.setObjectName("DeviceHeroCard")
        self.virtuoso_preview.setWordWrap(True)
        top_cards.addWidget(self.virtuoso_preview, 2)
        self.virtuoso_color_button = QPushButton("Accent Ring")
        self.virtuoso_color_button.setObjectName("LargeColorButton")
        self.virtuoso_color_button.clicked.connect(self.pick_virtuoso_color)
        top_cards.addWidget(self.virtuoso_color_button, 1)
        center_layout.addLayout(top_cards)

        eq_card = QFrame()
        self.virtuoso_eq_card = eq_card
        eq_card.setObjectName("SubPanel")
        eq_layout = QVBoxLayout(eq_card)
        eq_layout.setContentsMargins(18, 18, 18, 18)
        eq_header = QHBoxLayout()
        eq_title = QLabel("EQ Preset")
        eq_title.setObjectName("InspectorTitle")
        eq_header.addWidget(eq_title)
        eq_header.addStretch(1)
        self.virtuoso_preset = QComboBox()
        self.virtuoso_preset.currentIndexChanged.connect(self.load_selected_virtuoso_preset)
        eq_header.addWidget(self.virtuoso_preset)
        eq_layout.addLayout(eq_header)
        slider_row = QHBoxLayout()
        slider_row.setSpacing(10)
        self.virtuoso_eq_sliders.clear()
        self.virtuoso_eq_values.clear()
        for band in EQ_BANDS:
            column = QVBoxLayout()
            value = QLabel("0")
            value.setObjectName("EqValue")
            value.setAlignment(Qt.AlignmentFlag.AlignCenter)
            slider = QSlider(Qt.Orientation.Vertical)
            slider.setRange(-12, 12)
            slider.setValue(0)
            slider.valueChanged.connect(self.save_virtuoso_from_ui)
            label = QLabel(band)
            label.setObjectName("Muted")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            column.addWidget(value)
            column.addWidget(slider, 1)
            column.addWidget(label)
            slider_row.addLayout(column)
            self.virtuoso_eq_sliders.append(slider)
            self.virtuoso_eq_values.append(value)
        eq_layout.addLayout(slider_row)
        center_layout.addWidget(eq_card, 1)
        layout.addWidget(center, 1)

        inspector = QFrame()
        inspector.setObjectName("Inspector")
        inspector.setFixedWidth(330)
        side = QVBoxLayout(inspector)
        side.setContentsMargins(16, 16, 16, 16)
        side.setSpacing(12)
        self.virtuoso_audio_widgets = []
        self.virtuoso_lighting_widgets = []
        self.virtuoso_receiver_widgets = []
        mic_sidetone_label = self._control_label("Mic Sidetone")
        side.addWidget(mic_sidetone_label)
        self.virtuoso_audio_widgets.append(mic_sidetone_label)
        self.virtuoso_sidetone = QSlider(Qt.Orientation.Horizontal)
        self.virtuoso_sidetone.setRange(0, 100)
        self.virtuoso_sidetone.valueChanged.connect(self.save_virtuoso_from_ui)
        side.addWidget(self.virtuoso_sidetone)
        self.virtuoso_audio_widgets.append(self.virtuoso_sidetone)
        mic_level_label = self._control_label("Mic Level")
        side.addWidget(mic_level_label)
        self.virtuoso_audio_widgets.append(mic_level_label)
        self.virtuoso_mic = QSlider(Qt.Orientation.Horizontal)
        self.virtuoso_mic.setRange(0, 100)
        self.virtuoso_mic.valueChanged.connect(self.save_virtuoso_from_ui)
        side.addWidget(self.virtuoso_mic)
        self.virtuoso_audio_widgets.append(self.virtuoso_mic)
        sleep_label = self._control_label("Sleep Timer")
        side.addWidget(sleep_label)
        self.virtuoso_audio_widgets.append(sleep_label)
        self.virtuoso_sleep = QSpinBox()
        self.virtuoso_sleep.setRange(0, 120)
        self.virtuoso_sleep.setSuffix(" min")
        self.virtuoso_sleep.valueChanged.connect(self.save_virtuoso_from_ui)
        side.addWidget(self.virtuoso_sleep)
        self.virtuoso_audio_widgets.append(self.virtuoso_sleep)
        self.virtuoso_voice = QCheckBox("Voice Prompts")
        self.virtuoso_voice.setObjectName("AutoWrite")
        self.virtuoso_voice.stateChanged.connect(self.save_virtuoso_from_ui)
        side.addWidget(self.virtuoso_voice)
        self.virtuoso_audio_widgets.append(self.virtuoso_voice)
        self.virtuoso_auto_eq_checkbox = QCheckBox("Auto Apply Linux EQ")
        self.virtuoso_auto_eq_checkbox.setObjectName("AutoWrite")
        self.virtuoso_auto_eq_checkbox.setChecked(True)
        self.virtuoso_auto_eq_checkbox.stateChanged.connect(self.set_virtuoso_auto_eq)
        side.addWidget(self.virtuoso_auto_eq_checkbox)
        self.virtuoso_audio_widgets.append(self.virtuoso_auto_eq_checkbox)
        apply_flat = QPushButton("Flat EQ")
        apply_flat.clicked.connect(self.apply_virtuoso_flat_eq)
        side.addWidget(apply_flat)
        self.virtuoso_audio_widgets.append(apply_flat)
        apply_linux_eq = QPushButton("Apply Linux EQ")
        apply_linux_eq.setProperty("primary", True)
        apply_linux_eq.clicked.connect(self.apply_virtuoso_linux_eq)
        side.addWidget(apply_linux_eq)
        self.virtuoso_audio_widgets.append(apply_linux_eq)
        lighting_hint = QLabel("Accent-Ring Farbe\nRGB-HID fuer Virtuoso ist noch in Analyse.")
        lighting_hint.setObjectName("WarningNote")
        lighting_hint.setWordWrap(True)
        side.addWidget(lighting_hint)
        self.virtuoso_lighting_widgets.append(lighting_hint)
        read_status = QPushButton("Read Battery / Link")
        read_status.clicked.connect(self.read_virtuoso_status)
        side.addWidget(read_status)
        self.virtuoso_receiver_widgets.append(read_status)
        pairing_plan = QPushButton("Pairing Capture Plan")
        pairing_plan.clicked.connect(self.show_virtuoso_pairing_capture_plan)
        side.addWidget(pairing_plan)
        self.virtuoso_receiver_widgets.append(pairing_plan)
        self.virtuoso_detail = QLabel("Live Write: Ready\nPackets: -\nDevice: Virtuoso SE")
        self.virtuoso_detail.setObjectName("LiveCard")
        self.virtuoso_detail.setWordWrap(True)
        side.addWidget(self.virtuoso_detail, 1)
        layout.addWidget(inspector)

        self.stack.addWidget(page)
        self.virtuoso_page = page
        self.select_virtuoso_section("audio")

    def _control_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("InspectorTitle")
        return label

    def select_virtuoso_section(self, section: str) -> None:
        self.current_virtuoso_section = section
        for button, name in (
            (self.virtuoso_audio_nav, "audio"),
            (self.virtuoso_lighting_nav, "lighting"),
            (self.virtuoso_receiver_nav, "receiver"),
        ):
            button.setChecked(name == section)
        audio = section == "audio"
        lighting = section == "lighting"
        receiver = section == "receiver"
        self.virtuoso_preview.setVisible(audio)
        self.virtuoso_eq_card.setVisible(audio)
        self.virtuoso_color_button.setVisible(lighting)
        for widget in self.virtuoso_audio_widgets:
            widget.setVisible(audio)
        for widget in self.virtuoso_lighting_widgets:
            widget.setVisible(lighting)
        for widget in self.virtuoso_receiver_widgets:
            widget.setVisible(receiver)
        if receiver:
            self.virtuoso_detail.setText(
                "Wireless Receiver\nPairing und Battery/Link Status\nHinweis: Akku-Reports sind in VirtualBox noch unzuverlaessig."
            )
        elif lighting:
            self.virtuoso_detail.setText("Beleuchtung\nAccent-Ring im Profil gespeichert\nLive-RGB fuer Virtuoso noch nicht bestaetigt")

    def _build_generic_page(self) -> None:
        page = QWidget()
        page.setObjectName("EditorPage")
        layout = QVBoxLayout(page)
        title = QLabel("Profile Details")
        title.setObjectName("PanelTitle")
        layout.addWidget(title)
        self.generic_text = QTextEdit()
        self.generic_text.setObjectName("PreviewText")
        self.generic_text.setReadOnly(True)
        layout.addWidget(self.generic_text, 1)
        self.stack.addWidget(page)
        self.generic_page = page

    def _build_blank_device_page(self) -> None:
        page = QFrame()
        page.setObjectName("BlankDevicePage")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addStretch(1)
        self.stack.addWidget(page)
        self.blank_device_page = page

    def refresh_profiles(self) -> None:
        self.loading_profiles = True
        self.profile_list.clear()
        summaries = self.service.list_profile_summaries()
        group_summaries = [item for item in summaries if item["target_device"] == "profile-set"]
        standalone = [item for item in summaries if item["target_device"] != "profile-set" and not item.get("profile_group")]
        for summary in [*group_summaries, *standalone]:
            profile_name = self._profile_name_for_device_selection(str(summary["name"]), str(summary["target_device"]))
            item = QListWidgetItem(str(summary["name"]))
            item.setData(Qt.ItemDataRole.UserRole, profile_name)
            subtitle = self._profile_subtitle(summary, profile_name)
            item.setToolTip(subtitle)
            item.setText(f"{summary['name']}\n{subtitle}")
            self.profile_list.addItem(item)
        if self.profile_list.count() and self.current_name:
            for index in range(self.profile_list.count()):
                item = self.profile_list.item(index)
                if item.data(Qt.ItemDataRole.UserRole) == self.current_name:
                    self.profile_list.setCurrentItem(item)
                    break
        elif self.profile_list.count():
            self.profile_list.setCurrentRow(0)
        self.loading_profiles = False
        self.set_status(f"Profiles refreshed at {datetime.now():%H:%M:%S}")

    def _profile_name_for_device_selection(self, profile_name: str, target_device: str) -> str:
        if target_device != "profile-set":
            return profile_name
        role = {
            "k95": "keyboard",
            "m65": "mouse",
            "virtuoso-se": "headset",
            "receiver": "receiver",
        }.get(self.current_device_filter, "")
        for member in self.service.profiles_in_group(profile_name):
            if member.group_role == role:
                return member.name
        return profile_name

    def _profile_subtitle(self, summary: dict[str, object], selected_profile_name: str) -> str:
        if summary["target_device"] == "profile-set":
            return f"main profile -> {selected_profile_name}"
        return f"{summary['target_device']} / {summary.get('group_role') or summary['target_family']}"

    def refresh_devices(self) -> None:
        status = self.service.live_status(self.current_profile)
        signature = self._device_status_signature(status)
        changed = signature != self.device_status_signature
        self.device_status_signature = signature
        self.device_status_cache = status
        self._populate_device_tabs(status)
        if changed:
            self.set_status(f"Devices: {status['connected_count']} connected / {status['matching_count']} matching")

    def _device_status_signature(self, status: dict[str, object]) -> str:
        devices = status.get("devices", [])
        parts = []
        for device in devices:
            parts.append(
                "|".join(
                    (
                        str(device.get("target", "")),
                        str(device.get("path", "")),
                        str(device.get("open_ok", "")),
                    )
                )
            )
        return ";".join(sorted(parts))

    def _profile_changed(self, current: QListWidgetItem | None, _previous: QListWidgetItem | None) -> None:
        if current is None:
            return
        name = current.data(Qt.ItemDataRole.UserRole)
        self.show_profile(str(name))

    def _profile_clicked(self, item: QListWidgetItem) -> None:
        name = item.data(Qt.ItemDataRole.UserRole)
        if str(name) != self.current_name:
            self.show_profile(str(name))
        self._schedule_profile_auto_write(force=True)

    def show_profile(self, name: str) -> None:
        profile = self.service.load_profile(name)
        if profile is None:
            return
        self.current_profile = profile
        self.current_name = name
        self.profile_title.setText(profile.name)
        self.profile_subtitle.setText(f"{profile.target_device} / {profile.target_family}    {profile.description}")
        if profile.target_device == "k95":
            self.stop_m65_dpi_monitor()
            self._ensure_k95_per_key_lighting(profile)
            self.load_k95_options(profile)
            self._render_k95(profile)
            self.select_k95_section(self.current_k95_section)
            self.stack.setCurrentWidget(self.k95_page)
        elif profile.target_device == "m65":
            self.load_m65_profile(profile)
            self.stack.setCurrentWidget(self.m65_page)
            self.start_m65_dpi_monitor()
        elif profile.target_device == "virtuoso-se":
            self.stop_m65_dpi_monitor()
            self.load_virtuoso_profile(profile)
            self.select_virtuoso_section(self.current_virtuoso_section)
            self.stack.setCurrentWidget(self.virtuoso_page)
        else:
            self.stop_m65_dpi_monitor()
            self.generic_text.setText(json.dumps(profile.to_dict(), indent=2))
            self.stack.setCurrentWidget(self.generic_page)
        self.refresh_devices()
        self._schedule_profile_auto_write()

    def select_k95_section(self, section: str) -> None:
        self.current_k95_section = section
        if hasattr(self, "k95_inspector"):
            self.k95_inspector.setVisible(section == "lighting")
        if section == "lighting":
            self.k95_content_stack.setCurrentWidget(self.k95_lighting_page)
        elif section == "keys":
            self.k95_content_stack.setCurrentWidget(self.k95_keys_page)
        else:
            self.k95_content_stack.setCurrentWidget(self.k95_options_page)
        for button, name in (
            (self.k95_lighting_nav, "lighting"),
            (self.k95_keys_nav, "keys"),
            (self.k95_options_nav, "options"),
        ):
            button.setChecked(name == section)

    def load_k95_options(self, profile) -> None:
        options = profile.options.setdefault("k95_options", {})
        indicator_colors = profile.options.setdefault(
            "k95_indicator_colors",
            {
                "lock_on": "#1ecfdf",
                "lock_off": "#ff001f",
                "brightness": "#ffffff",
                "profile": "#ff001f",
            },
        )
        self.k95_option_alt_tab.blockSignals(True)
        self.k95_option_alt_f4.blockSignals(True)
        self.k95_option_shift_tab.blockSignals(True)
        self.k95_option_win_key.blockSignals(True)
        self.memory_mode.blockSignals(True)
        self.k95_option_alt_tab.setChecked(bool(options.get("disable_alt_tab", False)))
        self.k95_option_alt_f4.setChecked(bool(options.get("disable_alt_f4", False)))
        self.k95_option_shift_tab.setChecked(bool(options.get("disable_shift_tab", False)))
        self.k95_option_win_key.setChecked(bool(options.get("disable_windows_key", True)))
        self.memory_mode.setChecked(bool(options.get("memory_mode", False)))
        self.k95_option_alt_tab.blockSignals(False)
        self.k95_option_alt_f4.blockSignals(False)
        self.k95_option_shift_tab.blockSignals(False)
        self.k95_option_win_key.blockSignals(False)
        self.memory_mode.blockSignals(False)
        self._refresh_k95_indicator_buttons(indicator_colors)

    def save_k95_options(self) -> None:
        if self.current_profile is None or self.current_profile.target_device != "k95":
            return
        self.current_profile.options["k95_options"] = {
            "disable_alt_tab": self.k95_option_alt_tab.isChecked(),
            "disable_alt_f4": self.k95_option_alt_f4.isChecked(),
            "disable_shift_tab": self.k95_option_shift_tab.isChecked(),
            "disable_windows_key": self.k95_option_win_key.isChecked(),
            "memory_mode": self.memory_mode.isChecked(),
        }
        self.save_current(silent=True)
        self.set_status("K95 Optionen gespeichert. Options Sync sendet die bekannten K95-Setup-Pakete; Sperr-Bits brauchen Capture.")

    def k95_options_sync(self) -> None:
        if self.current_profile is None or self.current_profile.target_device != "k95":
            return
        self.save_current(silent=True)
        try:
            result = self.service.write_k95_options_sync_live(self.current_profile.name)
        except Exception as exc:
            QMessageBox.warning(self, "linuxcue", str(exc))
            self.set_status(f"K95 Options Sync fehlgeschlagen: {exc}")
            return
        self.set_status(f"K95 Options Sync OK: {result.packet_count} packets sent")
        self.k95_detail.setText(
            "Options Sync OK\n"
            f"Profile: {result.profile_name}\n"
            f"Packets: {result.packet_count}\n"
            "Win-Lock Bits: capture needed"
        )

    def show_k95_options_capture_plan(self) -> None:
        message = (
            "Capture fuer K95 Win-Lock Optionen:\n\n"
            "1. In iCUE alle Win-Lock Optionen auf Standard setzen und einen Write capturen.\n"
            "2. Genau eine Option aendern, z.B. WINDOWS-TASTE deaktivieren.\n"
            "3. Wieder capturen und mit linuxcue diff-captures vergleichen.\n\n"
            "CLI: linuxcue capture-plan --target k95 --capability win-lock-options"
        )
        QMessageBox.information(self, "linuxcue", message)
        self.set_status("K95 Capture Plan fuer Win-Lock Optionen angezeigt.")

    def _refresh_k95_indicator_buttons(self, colors: dict[str, str]) -> None:
        for button, label, option_key in (
            (self.lock_on_color, "Sperren Ein", "lock_on"),
            (self.lock_off_color, "Sperren Aus", "lock_off"),
            (self.brightness_color, "Helligkeit", "brightness"),
            (self.profile_color, "Profil", "profile"),
        ):
            color = str(colors.get(option_key, "#ffffff"))
            text_color = "#07110e" if QColor(color).lightness() > 150 else "#ffffff"
            button.setText(f"{label}  {color}")
            button.setStyleSheet(
                f"background:{color}; color:{text_color}; border:1px solid #4f5d52; border-radius:12px; padding:7px 10px; font-weight:800;"
            )

    def pick_k95_indicator_color(self, option_key: str, target_zone: str) -> None:
        if self.current_profile is None or self.current_profile.target_device != "k95":
            return
        indicator_colors = self.current_profile.options.setdefault("k95_indicator_colors", {})
        initial = QColor(str(indicator_colors.get(option_key, "#ffffff")))
        color = QColorDialog.getColor(initial, self, "K95 indicator color")
        if not color.isValid():
            return
        value = color.name()
        indicator_colors[option_key] = value
        self._refresh_k95_indicator_buttons(indicator_colors)
        if target_zone:
            self._set_k95_zone_color(target_zone, value)
        self.save_current(silent=True)
        if target_zone:
            self._schedule_auto_write()
        else:
            self.set_status("Anzeige-Farbe gespeichert. Dieser Status hat noch keinen eigenen Live-Report.")

    def _set_k95_zone_color(self, key: str, color: str) -> None:
        zone = self.k95_zones.get(key)
        if zone is None and self.current_profile is not None:
            for item in self.current_profile.lighting:
                if item.keys == [key]:
                    zone = item
                    self.k95_zones[key] = item
                    break
        if zone is None:
            return
        zone.color = color
        if key in self.k95_buttons:
            self._paint_key_button(key)

    def reset_k95_options(self) -> None:
        self.k95_option_alt_tab.setChecked(False)
        self.k95_option_alt_f4.setChecked(False)
        self.k95_option_shift_tab.setChecked(False)
        self.k95_option_win_key.setChecked(True)
        self.memory_mode.setChecked(False)
        if self.current_profile is not None:
            self.current_profile.options["k95_indicator_colors"] = {
                "lock_on": "#1ecfdf",
                "lock_off": "#ff001f",
                "brightness": "#ffffff",
                "profile": "#ff001f",
            }
            self._refresh_k95_indicator_buttons(self.current_profile.options["k95_indicator_colors"])
            self._set_k95_zone_color("lock", "#1ecfdf")
            self._set_k95_zone_color("brightness", "#ffffff")
            self._set_k95_zone_color("preset", "#ff001f")
        self.save_k95_options()
        self._schedule_auto_write()

    def _render_k95(self, profile) -> None:
        for child in self.keyboard_surface.findChildren(QPushButton):
            child.deleteLater()
        self.k95_buttons.clear()
        self.k95_zones = {zone.keys[0]: zone for zone in profile.lighting if len(zone.keys) == 1}
        for key, (row_index, col, span) in K95_GRID_POSITIONS.items():
            zone = self.k95_zones.get(key)
            if zone is None:
                continue
            button = QPushButton(self.keyboard_surface)
            button.setText(K95_LABELS.get(key, key.upper()))
            button.setObjectName("KeyButton")
            button.linuxcue_key = key
            button.installEventFilter(self)
            button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            x, y, width, height = self._key_geometry(row_index, col, span)
            button.setGeometry(x, y, width, height)
            button.clicked.connect(partial(self.select_k95_key, key))
            self.k95_buttons[key] = button
            self._paint_key_button(key)
            button.show()
        if not self.selected_key or self.selected_key not in self.k95_zones:
            self.select_k95_key("esc")

    @staticmethod
    def _key_geometry(row: int, col: int, span: int) -> tuple[int, int, int, int]:
        unit = 30
        gap = 4
        left = 18
        top = 14
        height = 30
        x = left + col * (unit + gap)
        y = top + row * (height + gap)
        width = span * unit + (span - 1) * gap
        if row == 0:
            width = 28
            height = 18
        return x, y, width, height

    def select_k95_key(self, key: str) -> None:
        self.select_k95_keys([key])

    def select_k95_keys(self, keys: list[str]) -> None:
        valid = [key for key in keys if key in self.k95_zones]
        if not valid:
            return
        self.selected_keys = set(valid)
        self.selected_key = valid[-1]
        if len(valid) == 1:
            zone = self.k95_zones.get(self.selected_key)
            color = zone.color if zone else "-"
            self.selected_label.setText(f"{self.selected_key.upper()}\n{color}")
        else:
            self.selected_label.setText(f"{len(valid)} Tasten ausgewaehlt\nBereichsauswahl")
        for name in self.k95_buttons:
            self._paint_key_button(name)

    def apply_k95_color(self, color: str) -> None:
        target_keys = self.selected_keys or ({self.selected_key} if self.selected_key else set())
        if not target_keys:
            self.set_status("Bitte zuerst eine K95-Taste auswaehlen.")
            return
        changed = 0
        for key in target_keys:
            zone = self.k95_zones.get(key)
            if zone is None:
                continue
            zone.color = color
            self._paint_key_button(key)
            changed += 1
        if changed == 1:
            self.selected_label.setText(f"{self.selected_key.upper()}\n{color}")
        else:
            self.selected_label.setText(f"{changed} Tasten ausgewaehlt\n{color}")
        self.save_current(silent=True)
        self._schedule_auto_write()

    def pick_custom_k95_color(self) -> None:
        zone = self.k95_zones.get(self.selected_key)
        initial = QColor(zone.color if zone else "#04ff00")
        color = QColorDialog.getColor(initial, self, "K95 key color")
        if color.isValid():
            self.apply_k95_color(color.name())

    def apply_color_to_all_k95(self) -> None:
        zone = self.k95_zones.get(self.selected_key)
        if zone is None:
            self.set_status("Bitte zuerst eine Quell-Taste auswaehlen.")
            return
        color = zone.color
        self.selected_keys = set(self.k95_zones)
        for item in self.k95_zones.values():
            item.color = color
        for key in self.k95_buttons:
            self._paint_key_button(key)
        self.selected_label.setText(f"{len(self.k95_zones)} Tasten ausgewaehlt\n{color}")
        self.save_current(silent=True)
        self._schedule_auto_write()

    def load_m65_profile(self, profile) -> None:
        self.m65_loading = True
        if not profile.dpi:
            profile.dpi = [
                DpiStage(name="sniper", x=400, y=400, color="#ffffff", active=False),
                DpiStage(name="stage1", x=800, y=800, color="#00ff85", active=True),
                DpiStage(name="stage2", x=1200, y=1200, color="#8ec5ff", active=False),
                DpiStage(name="stage3", x=1600, y=1600, color="#ffd166", active=False),
                DpiStage(name="stage4", x=3200, y=3200, color="#ff006e", active=False),
            ]
        while len(profile.dpi) < 5:
            profile.dpi.append(DpiStage(name=f"stage{len(profile.dpi)}", x=800, y=800, color="#ffffff"))
        if not any(stage.active for stage in profile.dpi):
            profile.dpi[0].active = True
        active_seen = False
        for stage in profile.dpi:
            if stage.active and not active_seen:
                active_seen = True
            else:
                stage.active = False
        for zone_name, color in (("logo", "#04ff00"), ("dpi_indicator", "#00c2ff"), ("front", "#d7ff37")):
            if not any(zone.name == zone_name for zone in profile.lighting):
                profile.lighting.append(LightingZone(name=zone_name, color=color, mode="static"))
        for index, row in enumerate(self.m65_dpi_rows):
            stage = profile.dpi[index]
            active = row["active"]
            x_value = row["x"]
            y_value = row["y"]
            color_button = row["color"]
            active.blockSignals(True)
            x_value.blockSignals(True)
            y_value.blockSignals(True)
            active.setChecked(stage.active)
            x_value.setValue(stage.x)
            y_value.setValue(stage.y)
            active.blockSignals(False)
            x_value.blockSignals(False)
            y_value.blockSignals(False)
            self._paint_m65_button(color_button, stage.color, stage.name)
        buttons = profile.options.setdefault("m65_buttons", {})
        for button_name, combo in self.m65_button_combos.items():
            action = str(buttons.get(button_name, button_name))
            combo.blockSignals(True)
            index = combo.findData(action)
            combo.setCurrentIndex(index if index >= 0 else 0)
            combo.blockSignals(False)
        self._refresh_m65_rgb_buttons()
        self._refresh_m65_preview()
        self.m65_loading = False

    def save_m65_from_ui(self, _section: str = "", *_args) -> None:
        if self.m65_loading or self.current_profile is None or self.current_profile.target_device != "m65":
            return
        active_index = next((index for index, row in enumerate(self.m65_dpi_rows) if row["active"].isChecked()), 0)
        for index, row in enumerate(self.m65_dpi_rows):
            if index >= len(self.current_profile.dpi):
                self.current_profile.dpi.append(DpiStage(name=f"stage{index + 1}", x=800, y=800))
            stage = self.current_profile.dpi[index]
            stage.x = row["x"].value()
            stage.y = row["y"].value()
            stage.active = index == active_index
            row["active"].blockSignals(True)
            row["active"].setChecked(stage.active)
            row["active"].blockSignals(False)
        self.current_profile.options["m65_buttons"] = {
            button_name: combo.currentData()
            for button_name, combo in self.m65_button_combos.items()
        }
        self.save_current(silent=True)
        self._refresh_m65_preview()
        self._schedule_m65_auto_write(_section or "all")

    def activate_m65_dpi_stage(self, index: int, _checked: bool = True) -> None:
        if self.m65_loading or self.current_profile is None or self.current_profile.target_device != "m65":
            return
        for row_index, row in enumerate(self.m65_dpi_rows):
            checkbox = row["active"]
            checkbox.blockSignals(True)
            checkbox.setChecked(row_index == index)
            checkbox.blockSignals(False)
        self.save_m65_from_ui("dpi")

    def start_m65_dpi_monitor(self) -> None:
        devices = [
            device
            for device in self.service.discover_devices()
            if device.support.family == "mouse" and "m65" in device.support.model_hint.casefold()
        ]
        if self.m65_dpi_monitor.ensure_open_many(devices):
            self.m65_input_timer.start(80)
            self.set_status(f"M65 DPI-Monitor aktiv ({self.m65_dpi_monitor.open_count} HID-Interfaces).")
        else:
            self.m65_input_timer.stop()

    def stop_m65_dpi_monitor(self) -> None:
        self.m65_input_timer.stop()
        self.m65_dpi_monitor.close()

    def poll_m65_dpi_input(self) -> None:
        if self.current_profile is None or self.current_profile.target_device != "m65":
            self.stop_m65_dpi_monitor()
            return
        delta = self.m65_dpi_monitor.read_dpi_delta()
        if delta:
            self.apply_m65_dpi_delta(delta)

    def apply_m65_dpi_delta(self, delta: int) -> None:
        if self.current_profile is None or self.current_profile.target_device != "m65" or not self.current_profile.dpi:
            return
        active_index = next((index for index, stage in enumerate(self.current_profile.dpi[:len(self.m65_dpi_rows)]) if stage.active), 0)
        next_index = max(0, min(len(self.m65_dpi_rows) - 1, active_index + delta))
        if next_index == active_index:
            return
        self.m65_loading = True
        for index, stage in enumerate(self.current_profile.dpi):
            stage.active = index == next_index
        for index, row in enumerate(self.m65_dpi_rows):
            checkbox = row["active"]
            checkbox.blockSignals(True)
            checkbox.setChecked(index == next_index)
            checkbox.blockSignals(False)
        self.m65_loading = False
        self.save_current(silent=True)
        self._refresh_m65_preview()
        direction = "hoch" if delta > 0 else "runter"
        self.set_status(f"M65 DPI-Taste erkannt: {direction}, aktive Stufe {next_index + 1}.")

    def pick_m65_dpi_color(self, index: int) -> None:
        if self.current_profile is None or self.current_profile.target_device != "m65" or index >= len(self.current_profile.dpi):
            return
        stage = self.current_profile.dpi[index]
        color = QColorDialog.getColor(QColor(stage.color), self, "M65 DPI color")
        if not color.isValid():
            return
        stage.color = color.name()
        self._paint_m65_button(self.m65_dpi_rows[index]["color"], stage.color, stage.name)
        self.save_current(silent=True)
        self._refresh_m65_preview()
        self._schedule_m65_auto_write("dpi")

    def pick_m65_zone_color(self, zone_name: str) -> None:
        if self.current_profile is None or self.current_profile.target_device != "m65":
            return
        zone = next((item for item in self.current_profile.lighting if item.name == zone_name), None)
        if zone is None:
            zone = LightingZone(name=zone_name, color="#ffffff", mode="static")
            self.current_profile.lighting.append(zone)
        color = QColorDialog.getColor(QColor(zone.color), self, f"M65 {zone_name} color")
        if not color.isValid():
            return
        zone.color = color.name()
        zone.mode = "static"
        self.save_current(silent=True)
        self._refresh_m65_rgb_buttons()
        self._refresh_m65_preview()
        self._schedule_m65_auto_write("rgb")

    def _refresh_m65_rgb_buttons(self) -> None:
        if self.current_profile is None:
            return
        for zone_name in M65_RGB_ZONES:
            button = self.m65_rgb_buttons.get(zone_name)
            if button is None:
                continue
            label = zone_name.replace("_", " ").title()
            zone = next((item for item in self.current_profile.lighting if item.name == zone_name), LightingZone(name=zone_name, color="#ffffff"))
            self._paint_m65_button(button, zone.color, label)

    def _refresh_m65_preview(self) -> None:
        if self.current_profile is None or self.current_profile.target_device != "m65":
            return
        active = next((stage for stage in self.current_profile.dpi if stage.active), self.current_profile.dpi[0] if self.current_profile.dpi else DpiStage(name="stage1", x=800, y=800))
        logo = next((zone for zone in self.current_profile.lighting if zone.name == "logo"), LightingZone(name="logo", color="#ffffff"))
        self.m65_preview.setText(
            f"M65 Pro RGB\nActive DPI: {active.x}/{active.y}\nLogo: {logo.color}\nNative buttons: hardware"
        )

    def _paint_m65_button(self, button: QPushButton, color: str, label: str) -> None:
        text_color = "#07110e" if QColor(color).lightness() > 150 else "#ffffff"
        button.setText(f"{label}\n{color}")
        button.setStyleSheet(
            f"background:{color}; color:{text_color}; border:1px solid #38d7e6; border-radius:14px; padding:10px; font-weight:900;"
        )

    def load_virtuoso_profile(self, profile) -> None:
        self.virtuoso_loading = True
        if not profile.audio:
            profile.audio = [AudioPreset(name="custom", active=True, bands=[0] * 10)]
        if not any(preset.active for preset in profile.audio):
            profile.audio[0].active = True
        if profile.headset is None:
            profile.headset = HeadsetSetting()
        if not profile.lighting:
            profile.lighting = [LightingZone(name="accent_ring", color="#1ecfdf", mode="static")]
        self.virtuoso_preset.blockSignals(True)
        self.virtuoso_preset.clear()
        for preset in profile.audio:
            self.virtuoso_preset.addItem(preset.name)
        active_index = next((index for index, preset in enumerate(profile.audio) if preset.active), 0)
        self.virtuoso_preset.setCurrentIndex(active_index)
        self.virtuoso_preset.blockSignals(False)
        self._apply_virtuoso_preset_to_sliders(profile.audio[active_index])
        self.virtuoso_sidetone.setValue(profile.headset.sidetone)
        self.virtuoso_mic.setValue(profile.headset.mic_level)
        self.virtuoso_sleep.setValue(profile.headset.sleep_timer_minutes)
        self.virtuoso_voice.setChecked(profile.headset.voice_prompt_enabled)
        self._refresh_virtuoso_preview()
        self.virtuoso_loading = False

    def load_selected_virtuoso_preset(self, *_args) -> None:
        if self.current_profile is None or self.current_profile.target_device != "virtuoso-se":
            return
        index = self.virtuoso_preset.currentIndex()
        if index < 0 or index >= len(self.current_profile.audio):
            return
        for preset_index, preset in enumerate(self.current_profile.audio):
            preset.active = preset_index == index
        self._apply_virtuoso_preset_to_sliders(self.current_profile.audio[index])
        self.save_virtuoso_from_ui()
        self._schedule_virtuoso_eq_apply(120)

    def _apply_virtuoso_preset_to_sliders(self, preset: AudioPreset) -> None:
        bands = list(preset.bands[:10]) if preset.bands else [preset.bass, preset.bass, preset.mids, preset.mids, preset.mids, preset.treble, preset.treble, preset.treble, preset.treble, preset.treble]
        bands.extend([0] * (10 - len(bands)))
        for slider, value_label, value in zip(self.virtuoso_eq_sliders, self.virtuoso_eq_values, bands):
            slider.blockSignals(True)
            slider.setValue(max(-12, min(12, int(value))))
            slider.blockSignals(False)
            value_label.setText(f"{slider.value():+d}")

    def save_virtuoso_from_ui(self, *_args) -> None:
        if self.virtuoso_loading or self.current_profile is None or self.current_profile.target_device != "virtuoso-se":
            return
        index = self.virtuoso_preset.currentIndex()
        if index < 0:
            index = 0
        if not self.current_profile.audio:
            self.current_profile.audio = [AudioPreset(name="custom", active=True, bands=[0] * 10)]
        index = min(index, len(self.current_profile.audio) - 1)
        bands = [slider.value() for slider in self.virtuoso_eq_sliders]
        for value_label, value in zip(self.virtuoso_eq_values, bands):
            value_label.setText(f"{value:+d}")
        for preset_index, preset in enumerate(self.current_profile.audio):
            preset.active = preset_index == index
        self.current_profile.audio[index].bands = bands
        self.current_profile.headset.sidetone = self.virtuoso_sidetone.value()
        self.current_profile.headset.mic_level = self.virtuoso_mic.value()
        self.current_profile.headset.sleep_timer_minutes = self.virtuoso_sleep.value()
        self.current_profile.headset.voice_prompt_enabled = self.virtuoso_voice.isChecked()
        self.save_current(silent=True)
        self._refresh_virtuoso_preview()
        self._schedule_profile_auto_write()
        self._schedule_virtuoso_eq_apply(650)

    def pick_virtuoso_color(self) -> None:
        if self.current_profile is None or self.current_profile.target_device != "virtuoso-se":
            return
        zone = next((item for item in self.current_profile.lighting if item.name == "accent_ring"), None)
        if zone is None:
            zone = LightingZone(name="accent_ring", color="#1ecfdf", mode="static")
            self.current_profile.lighting.append(zone)
        color = QColorDialog.getColor(QColor(zone.color), self, "Virtuoso Accent Ring")
        if not color.isValid():
            return
        zone.color = color.name()
        zone.mode = "static"
        self.save_current(silent=True)
        self._refresh_virtuoso_preview()
        self.virtuoso_detail.setText(
            "RGB Farbe gespeichert\n"
            f"Accent Ring: {zone.color}\n"
            "Live Write wird gesendet.\n"
            "Falls am Headset nichts passiert: RGB-Report braucht Capture."
        )
        self._schedule_profile_auto_write()

    def apply_virtuoso_flat_eq(self) -> None:
        if self.current_profile is None or self.current_profile.target_device != "virtuoso-se":
            return
        self.virtuoso_loading = True
        flat_index = next(
            (index for index, preset in enumerate(self.current_profile.audio) if preset.name.casefold() == "flat"),
            None,
        )
        if flat_index is None:
            self.current_profile.audio.append(AudioPreset(name="Flat", active=False, bands=[0] * 10))
            flat_index = len(self.current_profile.audio) - 1
        self.current_profile.audio[flat_index].bands = [0] * 10
        for index, preset in enumerate(self.current_profile.audio):
            preset.active = index == flat_index
        self.virtuoso_preset.blockSignals(True)
        self.virtuoso_preset.clear()
        for preset in self.current_profile.audio:
            self.virtuoso_preset.addItem(preset.name)
        self.virtuoso_preset.setCurrentIndex(flat_index)
        self.virtuoso_preset.blockSignals(False)
        self._apply_virtuoso_preset_to_sliders(self.current_profile.audio[flat_index])
        self.virtuoso_loading = False
        self.save_current(silent=True)
        self._refresh_virtuoso_preview()
        self.virtuoso_detail.setText("Flat EQ Preset aktiv\nAndere Presets wurden nicht ueberschrieben.\nLive Write wird gesendet.")
        self._schedule_profile_auto_write()
        self._schedule_virtuoso_eq_apply(120)

    def apply_virtuoso_linux_eq(self) -> None:
        if self.current_profile is None or self.current_profile.target_device != "virtuoso-se":
            return
        self.save_current(silent=True)
        try:
            result = self.service.apply_virtuoso_easyeffects(self.current_profile.name)
        except Exception as exc:
            QMessageBox.warning(self, "linuxcue", str(exc))
            self.set_status(f"Linux EQ fehlgeschlagen: {exc}")
            return
        self.virtuoso_detail.setText(
            "Linux EQ aktiv\n"
            f"Preset: {result['preset']}\n"
            f"Backend: {result['backend']}\n"
            "Keine zweite GUI noetig."
        )
        self.set_status(f"Virtuoso EQ ueber PipeWire geladen: {result['preset']}")

    def apply_virtuoso_linux_eq_silent(self) -> None:
        if self.current_profile is None or self.current_profile.target_device != "virtuoso-se":
            return
        try:
            result = self.service.apply_virtuoso_easyeffects(self.current_profile.name)
        except Exception as exc:
            self.set_status(f"Linux EQ Auto Apply fehlgeschlagen: {exc}")
            return
        self.virtuoso_detail.setText(
            "Linux EQ automatisch aktiv\n"
            f"Preset: {result['preset']}\n"
            "EasyEffects/PipeWire Backend"
        )
        self.set_status(f"Virtuoso EQ automatisch geladen: {result['preset']}")

    def set_virtuoso_auto_eq(self, *_args) -> None:
        self.virtuoso_auto_eq = self.virtuoso_auto_eq_checkbox.isChecked()
        if self.virtuoso_auto_eq:
            self._schedule_virtuoso_eq_apply(80)
        else:
            self.virtuoso_eq_timer.stop()
            self.set_status("Virtuoso Auto Apply Linux EQ ist aus.")

    def read_virtuoso_status(self) -> None:
        try:
            result = self.service.read_virtuoso_battery_live(seconds=3.0)
        except Exception as exc:
            try:
                raw_result = self.service.read_virtuoso_status_live(prefer_receiver=self._virtuoso_receiver_only())
            except Exception as raw_exc:
                QMessageBox.warning(self, "linuxcue", f"{exc}\n\nRaw fallback failed: {raw_exc}")
                self.set_status(f"Virtuoso Status fehlgeschlagen: {raw_exc}")
                return
            candidates = raw_result.get("candidate_percent_values", [])
            preview = candidates[:6] if isinstance(candidates, list) else []
            self.virtuoso_detail.setText(
                "Virtuoso Raw Status gelesen\n"
                f"Device: {raw_result.get('device')}\n"
                f"Report: {raw_result.get('report_id')}\n"
                f"Candidates: {preview}\n"
                "Kein Akku-Inputreport empfangen"
            )
            self.set_status("Virtuoso Raw Status gelesen; Akku-Inputreport wurde nicht empfangen.")
            return
        warning = "KRITISCH" if result.get("critical") else "OK"
        self.virtuoso_detail.setText(
            "Virtuoso Akku gelesen\n"
            f"Battery: {result.get('battery_percent')}%\n"
            f"Raw: {result.get('battery_raw_tenths')}\n"
            f"Link State: {result.get('link_state')}\n"
            f"Status: {warning}"
        )
        if result.get("critical"):
            QMessageBox.warning(self, "linuxcue", f"Virtuoso Akku kritisch: {result.get('battery_percent')}%")
        self.set_status(f"Virtuoso Akku gelesen: {result.get('battery_percent')}%.")

    def show_virtuoso_pairing_capture_plan(self) -> None:
        message = (
            "Capture fuer Virtuoso Receiver Pairing:\n\n"
            "1. Headset per USB-Kabel verbinden, Receiver sichtbar in iCUE.\n"
            "2. Wireshark Capture auf dem Receiver starten.\n"
            "3. In iCUE beim Receiver 'Koppeln' klicken.\n"
            "4. Wenn iCUE fragt, USB-Kabel vom Headset abziehen.\n"
            "5. Capture bis Erfolg/Fehler laufen lassen und speichern.\n\n"
            "CLI Plan: linuxcue capture-plan --target virtuoso-rgb-wireless-receiver --capability receiver-pairing"
        )
        QMessageBox.information(self, "linuxcue", message)
        self.set_status("Virtuoso Pairing Capture Plan angezeigt.")

    def _schedule_virtuoso_eq_apply(self, delay_ms: int = 500) -> None:
        if self.virtuoso_loading or not self.virtuoso_auto_eq:
            return
        if self.current_profile is None or self.current_profile.target_device != "virtuoso-se":
            return
        self.set_status("Virtuoso Linux EQ wird ueber EasyEffects geladen...")
        self.virtuoso_eq_timer.start(delay_ms)

    def _refresh_virtuoso_preview(self) -> None:
        if self.current_profile is None or self.current_profile.target_device != "virtuoso-se":
            return
        preset = next((item for item in self.current_profile.audio if item.active), self.current_profile.audio[0] if self.current_profile.audio else AudioPreset(name="custom"))
        zone = next((item for item in self.current_profile.lighting if item.name == "accent_ring"), LightingZone(name="accent_ring", color="#1ecfdf"))
        self.virtuoso_preview.setText(
            f"Virtuoso SE\nAudio Profile: {preset.name}\nAccent Ring: {zone.color}\nSidetone: {self.current_profile.headset.sidetone}%"
        )
        self.virtuoso_color_button.setText(f"Accent Ring\n{zone.color}")
        text_color = "#07110e" if QColor(zone.color).lightness() > 150 else "#ffffff"
        self.virtuoso_color_button.setStyleSheet(
            f"background:{zone.color}; color:{text_color}; border:1px solid #38d7e6; border-radius:18px; padding:18px; font-weight:900;"
        )

    def _paint_key_button(self, key: str) -> None:
        zone = self.k95_zones.get(key)
        color = zone.color if zone else "#101817"
        selected = key in self.selected_keys
        border = "#d7ff37" if selected else "#355144"
        border_width = 2 if selected else 1
        text = "#03120d" if QColor(color).lightness() > 150 else "#f6fff8"
        self.k95_buttons[key].setStyleSheet(
            f"background:{color}; color:{text}; border:{border_width}px solid {border}; border-radius:7px; font-weight:900;"
        )

    def save_current(self, silent: bool = False) -> None:
        if self.current_profile is None:
            return
        self.service.save_profile(self.current_profile)
        if not silent:
            self.set_status(f"Saved {self.current_profile.name}")

    def preview_current(self) -> None:
        if self.current_profile is None:
            return
        self.save_current(silent=True)
        preview = self.service.preview_profile(self.current_profile.name)
        text = json.dumps(preview or {"message": "No preview available"}, indent=2)
        if self.current_profile.target_device == "k95":
            self.k95_detail.setText(f"Preview ready\n{preview.get('packet_count', '-')} packets\nOpen Preview button for JSON in future.")
        else:
            self.generic_text.setText(text)
        self.set_status(f"Preview generated for {self.current_profile.name}")

    def write_current_live(self) -> None:
        self._write_current_live(show_dialog=True)

    def _write_current_live_silent(self) -> None:
        self._write_current_live(show_dialog=False)

    def _write_current_live(self, show_dialog: bool) -> None:
        if self.current_profile is None:
            return
        self.save_current(silent=True)
        try:
            if self.current_profile.target_device == "k95":
                result = self.service.write_k95_profile_live(self.current_profile.name)
            elif self.current_profile.target_device == "profile-set":
                results = self.service.write_profile_set_live(self.current_profile.name)
                result = results[0]
            elif self.current_profile.target_device == "m65":
                result = self.service.write_m65_profile_live(self.current_profile.name)
            elif self.current_profile.target_device == "virtuoso-se":
                result = self.service.write_virtuoso_profile_live(
                    self.current_profile.name,
                    prefer_receiver=self._virtuoso_receiver_only(),
                )
            else:
                raise RuntimeError("Dieses Profil hat kein direktes Live-Ziel.")
        except Exception as exc:
            self.set_status(f"Live Write fehlgeschlagen: {exc}")
            if show_dialog:
                QMessageBox.warning(self, "linuxcue", str(exc))
            return
        payload = {
            "profile": result.profile_name,
            "device": result.device,
            "packet_count": result.packet_count,
            "message": result.message,
        }
        if self.current_profile.target_device == "k95":
            self.k95_detail.setText(
                f"Live Write OK\nProfile: {payload['profile']}\nDevice: {payload['device']}\nPackets: {payload['packet_count']}"
            )
        elif self.current_profile.target_device == "m65":
            self.m65_detail.setText(
                f"Live Write OK\nProfile: {payload['profile']}\nDevice: {payload['device']}\nPackets: {payload['packet_count']}\n64-byte HID reports\nButtons/RGB/DPI experimental"
            )
        elif self.current_profile.target_device == "virtuoso-se":
            self.virtuoso_detail.setText(
                f"Live Write OK\nProfile: {payload['profile']}\nDevice: {payload['device']}\nPackets: {payload['packet_count']}"
            )
        if hasattr(self, "live_status_label"):
            self.live_status_label.setText(f"Ready / {result.packet_count} packets")
        self.set_status(f"Live Write OK: {result.packet_count} packets sent")
        if show_dialog:
            QMessageBox.information(self, "linuxcue", f"Live Write OK: {result.packet_count} packets sent.")

    def _virtuoso_receiver_only(self) -> bool:
        status = self.device_status_cache or self.service.live_status(self.current_profile)
        devices = status.get("devices", [])
        has_headset = any(
            "virtuoso" in str(device.get("target", "")).casefold()
            and "receiver" not in str(device.get("target", "")).casefold()
            and str(device.get("endpoint_role")) == "headset-hid"
            and bool(device.get("open_ok"))
            for device in devices
        )
        has_receiver = any(
            "virtuoso" in str(device.get("target", "")).casefold()
            and "receiver" in str(device.get("target", "")).casefold()
            and bool(device.get("open_ok"))
            for device in devices
        )
        return bool(has_receiver and not has_headset)

    def write_m65_kind_live(self, packet_kind: str) -> None:
        if self.current_profile is None or self.current_profile.target_device != "m65":
            return
        self.save_current(silent=True)
        try:
            result = self.service.write_m65_profile_live(self.current_profile.name, packet_kind=packet_kind)
        except Exception as exc:
            self.set_status(f"M65 {packet_kind} write fehlgeschlagen: {exc}")
            QMessageBox.warning(self, "linuxcue", str(exc))
            return
        self.m65_detail.setText(
            f"M65 {packet_kind.upper()} Write OK\nProfile: {result.profile_name}\nDevice: {result.device}\nPackets: {result.packet_count}\nMode: output_report"
        )
        self.set_status(f"M65 {packet_kind}: {result.packet_count} packets sent")

    def _write_m65_pending_live_silent(self) -> None:
        if self.current_profile is None or self.current_profile.target_device != "m65":
            return
        packet_kind = self.m65_pending_packet_kind or "all"
        self.save_current(silent=True)
        try:
            result = self.service.write_m65_profile_live(self.current_profile.name, packet_kind=packet_kind)
        except Exception as exc:
            self.set_status(f"M65 Auto Write fehlgeschlagen: {exc}")
            return
        self.m65_detail.setText(
            f"M65 Auto {packet_kind.upper()} OK\nProfile: {result.profile_name}\nDevice: {result.device}\nPackets: {result.packet_count}\nMode: output_report"
        )
        if hasattr(self, "live_status_label"):
            self.live_status_label.setText(f"M65 {packet_kind} / {result.packet_count} packets")
        self.set_status(f"M65 Auto {packet_kind}: {result.packet_count} packets sent")

    def _schedule_auto_write(self) -> None:
        if self.auto_write.isChecked() and self.current_profile and self.current_profile.target_device == "k95":
            self.set_status("Farbe gespeichert, Auto Live Write wird gesendet...")
            self.live_timer.start(350)
        else:
            self.set_status("Farbe gespeichert. Auto Live Write ist aus.")

    def _schedule_profile_auto_write(self, force: bool = False) -> None:
        if self.loading_profiles and not force:
            return
        if not self.auto_write.isChecked() or self.current_profile is None:
            return
        if self.current_profile.target_device not in {"k95", "profile-set", "m65", "virtuoso-se"}:
            return
        if not self._profile_device_connected(self.current_profile):
            self.set_status(f"{self.current_profile.name} ausgewaehlt, aber das Zielgeraet ist nicht verbunden.")
            return
        self.set_status(f"{self.current_profile.name} ausgewaehlt, Auto Live Write wird gesendet...")
        self.profile_write_timer.start(250)

    def _schedule_m65_auto_write(self, packet_kind: str) -> None:
        if self.loading_profiles or self.m65_loading:
            return
        if not self.auto_write.isChecked() or self.current_profile is None or self.current_profile.target_device != "m65":
            self.set_status("M65 gespeichert. Auto Live Write ist aus.")
            return
        self.m65_pending_packet_kind = packet_kind if packet_kind in {"rgb", "dpi", "buttons"} else "all"
        self.set_status(f"M65 {self.m65_pending_packet_kind} geaendert, Auto Live Write wird gesendet...")
        self.m65_write_timer.start(250)

    def import_icue(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Import iCUE profile", "", "iCUE profiles (*.cueprofile);;All files (*)")
        if not path:
            return
        result = self.service.import_icue_profiles(path)
        self.refresh_profiles()
        names = result.get("profile_names") or []
        if names:
            matches = self.profile_list.findItems(str(names[0]), Qt.MatchFlag.MatchExactly)
            if matches:
                self.profile_list.setCurrentItem(matches[0])
        self.set_status(f"Imported {result['saved_count']} profiles")

    def create_starter(self, target: str) -> None:
        name = f"{target}-{datetime.now():%H%M%S}"
        profile = self.service.create_profile_for_target(target, name)
        if target == "k95":
            self._ensure_k95_per_key_lighting(profile)
        self.service.save_profile(profile)
        self.current_name = name
        self.refresh_profiles()

    def k95_hardware_mode(self) -> None:
        try:
            result = self.service.write_k95_hardware_mode_live()
        except Exception as exc:
            QMessageBox.warning(self, "linuxcue", str(exc))
            self.set_status(f"K95 hardware mode failed: {exc}")
            return
        self.set_status(f"K95 hardware mode sent: {result.packet_count} packet")

    def _ensure_k95_per_key_lighting(self, profile) -> None:
        all_keys = [key for key in K95_OPENRGB_ZONE_ORDER if key != "fn"]
        existing_single = {
            zone.keys[0]: zone
            for zone in profile.lighting
            if len(zone.keys) == 1 and zone.keys[0] in all_keys
        }
        if len(existing_single) == len(all_keys):
            return
        key_colors = {key: "#04ff00" for key in all_keys}
        key_modes = {key: "static" for key in all_keys}
        for zone in profile.lighting:
            keys = [key for key in zone.keys if key in key_colors]
            if not keys:
                keys = [key for key in K95_LAYOUT.get(zone.name, []) if key in key_colors]
            if len(zone.keys) == 1 and zone.name.startswith("key_") and zone.name[4:] in key_colors:
                keys = [zone.name[4:]]
            for key in keys:
                key_colors[key] = zone.color
                key_modes[key] = zone.mode
        profile.lighting = [
            LightingZone(name=f"key_{key}", color=key_colors[key], mode=key_modes[key], keys=[key])
            for key in all_keys
        ]

    def set_status(self, text: str) -> None:
        self.status_label.setText(text)


STYLESHEET = """
QWidget#Root {
    background: #0b0f11;
    color: #eef8ef;
    font-family: "Segoe UI", "Noto Sans", sans-serif;
}
QFrame#Sidebar, QFrame#Hero, QFrame#Actions, QFrame#KeyboardPanel, QFrame#Inspector, QFrame#DeviceCard {
    border: 1px solid #203d44;
    border-radius: 20px;
}
QFrame#Sidebar {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #10191d, stop:0.45 #0c1514, stop:1 #07100d);
}
QFrame#Main {
    background: transparent;
}
QFrame#Hero {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #091216, stop:0.58 #0d171a, stop:1 #122024);
    border-color: #203640;
}
QFrame#Actions {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #111c18, stop:0.45 #13221d, stop:1 #10191c);
    border-color: #28433b;
}
QFrame#KeyboardPanel, QWidget#EditorPage {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #101d18, stop:0.55 #0b1512, stop:1 #07110e);
}
QFrame#Inspector {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #173126, stop:1 #101d18);
}
QFrame#DeviceCard {
    background: #101f1a;
}
QFrame#DeviceNav, QFrame#SubPanel {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #151817, stop:1 #0d100f);
    border: 1px solid #26332e;
    border-radius: 16px;
}
QLabel#DeviceNavTitle {
    color: #dfe8f1;
    font-size: 18px;
    font-weight: 900;
}
QPushButton#DeviceNavButton {
    text-align: left;
    background: transparent;
    border: 0;
    border-radius: 8px;
    padding: 10px 12px;
    color: #aeb7bd;
}
QPushButton#DeviceNavButton:checked {
    background: #555555;
    color: #ffffff;
}
QPushButton#DeviceTab {
    text-align: left;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1a2023, stop:1 #111619);
    border: 1px solid #29363a;
    border-radius: 16px;
    padding: 18px 20px;
    min-width: 230px;
    min-height: 70px;
    font-size: 15px;
}
QPushButton#DeviceTab:checked {
    color: #08dff7;
    border-color: #08dff7;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #142f36, stop:1 #102026);
}
QLabel#AppTitle {
    color: #d7ff37;
    font-size: 26px;
    font-weight: 800;
}
QLabel#TopLogo {
    color: #ffffff;
    font-size: 30px;
    font-weight: 900;
    padding-right: 26px;
}
QLabel#TinyLabel {
    color: #08dff7;
    font-size: 11px;
    font-weight: 800;
}
QLabel#ReadyBadge {
    color: #dff8e7;
    background: #10191c;
    border: 1px solid #2a3a40;
    border-radius: 12px;
    padding: 10px 18px;
}
QLabel#GreenBadge {
    color: #07110e;
    background: #57d967;
    border: 1px solid #85ef91;
    border-radius: 12px;
    padding: 7px 12px;
    font-weight: 900;
}
QLabel#AmberBadge {
    color: #170f02;
    background: #ffcf55;
    border: 1px solid #ffe28a;
    border-radius: 12px;
    padding: 7px 12px;
    font-weight: 900;
}
QLabel#LiveStep {
    color: #dcece4;
    background: #0c1614;
    border: 1px solid #244139;
    border-radius: 14px;
    padding: 9px 16px;
    min-width: 82px;
    font-weight: 800;
}
QLabel#LiveTitle {
    color: #ffcf55;
    font-size: 20px;
    font-weight: 900;
}
QLabel#HeroTitle {
    color: #f5fff5;
    font-size: 18px;
    font-weight: 800;
}
QLabel#HeroSub, QLabel#Muted, QLabel#Status {
    color: #9db4aa;
}
QLabel#SidebarHint {
    color: #a8c0b6;
    background: #10231c;
    border: 1px solid #264438;
    border-radius: 14px;
    padding: 10px;
}
QLabel#Badge {
    color: #07110e;
    background: #d7ff37;
    border-radius: 12px;
    padding: 6px 12px;
    font-weight: 900;
}
QLabel#PanelTitle {
    color: #f5fff5;
    font-size: 22px;
    font-weight: 800;
}
QLabel#InspectorTitle, QLabel#DeviceName {
    color: #eaffd6;
    font-size: 14px;
    font-weight: 800;
}
QLabel#SelectedKey {
    color: #d7ff37;
    font-size: 18px;
    font-weight: 800;
    padding: 10px;
    border: 1px solid #294237;
    border-radius: 14px;
    background: #0b1512;
}
QLabel#ColorHint {
    color: #d9e4e8;
    padding: 8px 0;
}
QLabel#WarningNote {
    color: #ffeab2;
    background: #20190d;
    border: 1px solid #6a5521;
    border-radius: 12px;
    padding: 10px;
}
QLabel#LiveCard {
    color: #dcece4;
    background: #091410;
    border: 1px solid #294237;
    border-radius: 14px;
    padding: 14px;
    font-family: "Cascadia Mono", "Consolas", monospace;
}
QPushButton#ColorOptionButton {
    text-align: left;
    min-height: 34px;
    min-width: 132px;
}
QStackedWidget#DeviceContentStack {
    background: transparent;
}
QWidget#KeyboardSurface {
    background: transparent;
}
QListWidget#ProfileList {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0e211a, stop:1 #07110e);
    border: 1px solid #20362e;
    border-radius: 14px;
    padding: 6px;
    color: #dfeee7;
}
QListWidget#ProfileList::item {
    padding: 12px 10px;
    margin: 4px;
    min-height: 38px;
    border-radius: 12px;
    background: #102019;
}
QListWidget#ProfileList::item:selected {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #174f54, stop:1 #263c29);
    color: #ffffff;
    border: 1px solid #d7ff37;
}
QPushButton {
    background: #20382f;
    color: #eef8ef;
    border: 1px solid #355144;
    border-radius: 12px;
    padding: 9px 12px;
    font-weight: 700;
}
QPushButton:hover {
    background: #2c4a3f;
}
QPushButton[primary="true"] {
    background: #d7ff37;
    color: #07110e;
    border-color: #eaff7a;
}
QCheckBox#AutoWrite {
    color: #eaffd6;
    font-weight: 800;
    spacing: 10px;
    padding: 6px;
}
QCheckBox#AutoWrite::indicator {
    width: 34px;
    height: 18px;
    border-radius: 9px;
    background: #313733;
    border: 1px solid #56635c;
}
QCheckBox#AutoWrite::indicator:checked {
    background: #57d967;
    border-color: #95ff9e;
}
QLabel#SectionTitle {
    color: #96aaa1;
    font-size: 11px;
    padding-top: 8px;
}
QLabel#SidebarDevice {
    color: #eef8ef;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #12393d, stop:1 #13241f);
    border: 1px solid #24443c;
    border-radius: 12px;
    padding: 11px 12px;
}
QLabel#DeviceHeroCard {
    color: #effff5;
    background: qradialgradient(cx:0.7, cy:0.1, radius:1.0, fx:0.7, fy:0.1, stop:0 #26333a, stop:0.55 #151d20, stop:1 #0d1315);
    border: 1px solid #293e43;
    border-radius: 18px;
    padding: 22px;
    font-size: 18px;
    font-weight: 800;
}
QPushButton#LargeColorButton {
    min-height: 118px;
    font-size: 17px;
}
QPushButton#DeviceTab {
    background: qradialgradient(cx:0.65, cy:0.15, radius:0.9, fx:0.65, fy:0.15, stop:0 #23313a, stop:0.58 #161d20, stop:1 #101518);
    border: 1px solid #2b3b40;
    min-height: 92px;
}
QPushButton#DeviceTab:checked {
    background: qradialgradient(cx:0.45, cy:0.25, radius:0.9, fx:0.45, fy:0.25, stop:0 #183b46, stop:0.55 #10272d, stop:1 #0d171b);
}
QSlider::groove:horizontal {
    height: 6px;
    background: #25322f;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #10d4e8;
    width: 18px;
    margin: -7px 0;
    border-radius: 9px;
}
QSlider::groove:vertical {
    width: 5px;
    background: #25322f;
    border-radius: 3px;
}
QSlider::handle:vertical {
    background: #10d4e8;
    height: 18px;
    margin: 0 -7px;
    border-radius: 9px;
}
QLabel#EqValue {
    color: #d7ff37;
    font-weight: 900;
}
QScrollArea#KeyboardScroll {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #151918, stop:0.45 #111715, stop:1 #2b2d2a);
    border: 1px solid #27372f;
    border-radius: 18px;
}
QTextEdit#PreviewText {
    background: #091410;
    color: #dcece4;
    border: 1px solid #294237;
    border-radius: 14px;
    padding: 10px;
    font-family: "Cascadia Mono", "Consolas", monospace;
}

QWidget#Root {
    background: qradialgradient(cx:0.72, cy:0.08, radius:1.2, fx:0.72, fy:0.08, stop:0 #13212a, stop:0.42 #081014, stop:1 #040708);
}
QFrame#Main {
    background: transparent;
}
QFrame#Brand {
    border-bottom: 1px solid #16262c;
}
QLabel#BrandMark {
    color: #0b1114;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #12e8ff, stop:0.5 #145b66, stop:1 #d7ff37);
    border: 1px solid #33e7f5;
    border-radius: 15px;
    padding: 9px 10px;
    font-size: 16px;
    font-weight: 900;
}
QLabel#AppTitle {
    color: #f4fbff;
    font-size: 29px;
    font-weight: 900;
    letter-spacing: -1px;
}
QLabel#TopLogo {
    color: #f4fbff;
    font-size: 28px;
    font-weight: 900;
    min-width: 150px;
}
QFrame#Sidebar {
    border: 0;
    border-radius: 0;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #111b21, stop:0.42 #0b1418, stop:1 #060b0d);
}
QFrame#Hero {
    border: 1px solid #1d323a;
    border-radius: 16px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #071015, stop:0.58 #0a151a, stop:1 #111b20);
}
QFrame#ProfileSelect {
    border: 1px solid #263941;
    border-radius: 12px;
    background: #081014;
}
QLabel#IconChip {
    color: #d7eef2;
    background: #0b1418;
    border: 1px solid #2b3d44;
    border-radius: 12px;
    padding: 15px 18px;
    font-weight: 800;
}
QLabel#ReadyBadge {
    color: #dff8e7;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #101b20, stop:1 #0a1215);
    border: 1px solid #2b3f48;
    border-radius: 12px;
    padding: 12px 18px;
    font-weight: 800;
}
QListWidget#ProfileList {
    background: transparent;
    border: 0;
    padding: 0;
}
QListWidget#ProfileList::item {
    padding: 14px 12px;
    margin: 3px 0;
    min-height: 46px;
    border-radius: 10px;
    background: transparent;
    color: #d4dde2;
}
QListWidget#ProfileList::item:selected {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0c9bb0, stop:0.58 #12424d, stop:1 #16262b);
    color: #ffffff;
    border-left: 4px solid #12e8ff;
    border-top: 1px solid #1ebed1;
    border-bottom: 1px solid #204650;
}
QLabel#SectionTitle {
    color: #a9b5bb;
    font-size: 12px;
    font-weight: 800;
    padding-top: 10px;
    letter-spacing: 1px;
}
QLabel#SidebarDevice {
    color: #eef8ef;
    background: transparent;
    border: 0;
    border-radius: 0;
    padding: 9px 10px;
}
QPushButton#DeviceTab {
    text-align: left;
    color: #f2f7f8;
    background: qradialgradient(cx:0.58, cy:0.08, radius:1.0, fx:0.58, fy:0.08, stop:0 #24313a, stop:0.42 #151d22, stop:1 #0c1114);
    border: 1px solid #263943;
    border-radius: 13px;
    padding: 10px 14px;
    min-width: 214px;
    max-width: 246px;
    min-height: 104px;
    max-height: 122px;
    font-size: 12px;
    font-weight: 800;
}
QPushButton#DeviceTab:checked {
    color: #12e8ff;
    border: 1px solid #12e8ff;
    background: qradialgradient(cx:0.28, cy:0.16, radius:1.0, fx:0.28, fy:0.16, stop:0 #173d48, stop:0.5 #10252d, stop:1 #0b1216);
}
QFrame#KeyboardPanel, QWidget#EditorPage {
    border: 1px solid #1d343b;
    border-radius: 16px;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #101a18, stop:0.52 #091210, stop:1 #050908);
}
QFrame#BlankDevicePage {
    border: 0;
    background: transparent;
}
QFrame#DeviceNav, QFrame#SubPanel, QFrame#Inspector {
    border: 1px solid #20383b;
    border-radius: 16px;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #151b1d, stop:1 #0a0f10);
}
QFrame#Inspector {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #153629, stop:1 #091211);
}
QFrame#Actions {
    border: 1px solid #26383b;
    border-radius: 14px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0c1517, stop:0.48 #101819, stop:1 #15150c);
}
QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #27343a, stop:1 #182226);
    color: #eef8ef;
    border: 1px solid #354951;
    border-radius: 10px;
    padding: 10px 14px;
    font-weight: 800;
}
QPushButton:hover {
    border-color: #12e8ff;
    background: #21353a;
}
QPushButton[primary="true"] {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffe27a, stop:1 #f4b82e);
    color: #0f1008;
    border-color: #ffd45b;
}
QPushButton#DeviceNavButton:checked {
    background: #4a4a4a;
    color: #ffffff;
    border-left: 4px solid #d7ff37;
}
QLabel#DeviceHeroCard {
    background: qradialgradient(cx:0.78, cy:0.08, radius:1.0, fx:0.78, fy:0.08, stop:0 #26333a, stop:0.48 #141d22, stop:1 #0a1013);
    border: 1px solid #2c414a;
    border-radius: 18px;
}
QLabel#EmptyDeviceStrip {
    color: #91aab1;
    background: #081014;
    border: 1px dashed #263941;
    border-radius: 14px;
    padding: 18px 22px;
    min-height: 82px;
    font-weight: 800;
}
QLabel#HeroTitle {
    font-size: 17px;
}
QLabel#HeroSub {
    color: #91aab1;
    font-size: 12px;
}
QLabel#LiveStep {
    padding: 8px 14px;
    min-width: 78px;
}
QLabel#LiveTitle {
    font-size: 18px;
}
QLabel#PanelTitle {
    font-size: 20px;
}
QLabel#DeviceNavTitle {
    font-size: 17px;
}
QPushButton#DeviceNavButton {
    padding: 9px 12px;
}
QScrollArea#KeyboardScroll {
    background: qradialgradient(cx:0.48, cy:0.2, radius:0.9, fx:0.48, fy:0.2, stop:0 #1c2421, stop:0.46 #131817, stop:1 #050807);
    border: 1px solid #243b36;
    border-radius: 16px;
}
QPushButton#KeyButton {
    border-radius: 8px;
    font-size: 9px;
    font-weight: 900;
    padding: 0;
}
QPushButton#LargeColorButton {
    min-height: 96px;
}
QFrame#InlineControls {
    border: 1px solid #20383b;
    border-radius: 12px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #11191d, stop:1 #0d1417);
}
QPushButton#LayerButton {
    text-align: left;
    border-radius: 12px;
    padding: 11px 12px;
    background: transparent;
    border: 1px solid transparent;
    color: #dce8eb;
}
QPushButton#LayerButton:checked {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #165862, stop:1 #12252b);
    border-color: #12e8ff;
    color: #ffffff;
}
"""


def launch_gui() -> None:
    if QT_IMPORT_ERROR is not None:
        raise RuntimeError(
            "PySide6/Qt is missing. On CachyOS install it with: sudo pacman -S --needed pyside6\n"
            "Then reinstall linuxcue with: bash scripts/install-cachyos-dev.sh"
        ) from QT_IMPORT_ERROR
    app = QApplication(sys.argv)
    window = QtLinuxCueGui()
    window.show()
    app.exec()


def main() -> int:
    try:
        launch_gui()
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0
