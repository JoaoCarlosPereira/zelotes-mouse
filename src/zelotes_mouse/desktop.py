"""Janela no formato do driver de fábrica do C-18."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QPointF, QSize, Qt, QTimer
from PySide6.QtGui import (
    QAction,
    QCloseEvent,
    QColor,
    QFont,
    QIcon,
    QLinearGradient,
    QPainter,
    QPixmap,
)
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QColorDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMenu,
    QPushButton,
    QSlider,
    QStackedWidget,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from zelotes_mouse.device import MouseError
from zelotes_mouse.gui import start_server
from zelotes_mouse.i18n import (
    ASSIGNMENT_IDS,
    DEFAULT_BUTTON_IDS,
    MODE_IDS,
    assignment_label,
    profile_name,
    tr,
)
from zelotes_mouse.launcher import APP_ID, ICON_SIZES, icon_file, install_launcher
from zelotes_mouse.preferences import Preferences, load_preferences, save_preferences
from zelotes_mouse.protocol import ProtocolError
from zelotes_mouse.service import apply_settings
from zelotes_mouse.settings import (
    SESSION,
    Library,
    Settings,
    config_path,
    load_library,
    parse_color,
    parse_settings,
    save_library,
)

HOST = "127.0.0.1"
RED = "#e10600"
_TAB_KEYS = ("tab.buttons", "tab.performance", "tab.lighting", "tab.macros", "tab.settings")
_MACRO_TOOLS = ("macro.select", "macro.record", "macro.delay", "macro.click", "macro.delete")
_MACRO_KINDS = ("select", "record", "delay", "click", "delete")


def app_icon() -> QIcon:
    icon = QIcon()
    for size in ICON_SIZES:
        path = icon_file(size)
        if path.is_file():
            icon.addFile(str(path), QSize(size, size))
    return icon


def run(port: int = 8765) -> int:
    install_launcher()
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("Zelotes C-18")
    app.setDesktopFileName(APP_ID)
    app.setWindowIcon(app_icon())
    app.setQuitOnLastWindowClosed(False)
    window = MainWindow(port)
    window.show()
    return app.exec()


class MainWindow(QMainWindow):
    def __init__(self, port: int) -> None:
        super().__init__()
        self.port = port
        self.library = load_library()
        self.prefs = load_preferences()
        if self.prefs.iniciar_com_sistema:
            save_preferences(self.prefs)
        self.open_action: QAction | None = None
        self.quit_action: QAction | None = None
        self._saved_mtime = _mtime()
        self.setWindowTitle("ZELOTES")
        self.setMinimumSize(980, 640)
        self.resize(1040, 680)
        icon = app_icon()
        self.setWindowIcon(icon)

        self.rows: list[QPushButton] = []
        self.mode_group = QButtonGroup(self)
        self.rate_group = QButtonGroup(self)
        self.description = QLineEdit()
        self.description.setObjectName("description")
        self.correlation = QCheckBox(self._t("correlation"))
        self.color = QColor("#ff0000")
        self.color_button = QPushButton()
        self.color_button.setObjectName("swatch")
        self.color_button.clicked.connect(self._pick_color)
        self.brightness = _slider()
        self.speed = _slider()
        self.dpi_boxes: list[QLineEdit] = []
        self.macros = QListWidget()
        self.macros.addItems(self.library.macros)
        self.status = QLabel("")
        self.status.setObjectName("status")

        shell = QWidget()
        shell.setObjectName("shell")
        column = QVBoxLayout(shell)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(0)
        column.addWidget(self._header())
        column.addWidget(self._tabs())
        self.stack = QStackedWidget()
        self.stack.addWidget(self._button_page())
        self.stack.addWidget(self._performance_page())
        self.stack.addWidget(self._lighting_page())
        self.stack.addWidget(self._armoury_page())
        self.stack.addWidget(self._settings_page())
        column.addWidget(self.stack, 1)
        column.addWidget(self._footer())
        self.setCentralWidget(shell)
        self.setStyleSheet(_STYLE)
        self._load(self.library.current())
        self._select_tab(0)

        self.tray: QSystemTrayIcon | None = None
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray = QSystemTrayIcon(icon, self)
            self.tray.setToolTip("ZELOTES")
            menu = QMenu()
            self.open_action = QAction(self._t("tray.open"), self)
            self.open_action.triggered.connect(self.show)
            self.quit_action = QAction(self._t("tray.quit"), self)
            self.quit_action.triggered.connect(QApplication.quit)
            menu.addAction(self.open_action)
            menu.addAction(self.quit_action)
            self.tray.setContextMenu(menu)
            self.tray.show()

        try:
            start_server(port)
            self.api_note = f"http://{HOST}:{port}"
        except OSError:
            self.api_note = ""
            self.status.setText(self._t("status.port").format(port=port))
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._reload_external)
        self._timer.start(1000)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.tray is not None and self.tray.isVisible():
            event.ignore()
            self.hide()
            return
        event.accept()
        QApplication.quit()

    def _header(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("header")
        bar.setFixedHeight(78)
        grid = QGridLayout(bar)
        grid.setContentsMargins(18, 10, 18, 0)
        self.badge = QLabel(self._t("badge"))
        self.badge.setObjectName("badge")
        logo = QLabel("ZELOTES®")
        logo.setObjectName("logo")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        grid.addWidget(logo, 0, 0)
        grid.addWidget(self.badge, 0, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        return bar

    def _tabs(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("tabbar")
        row = QHBoxLayout(bar)
        row.setContentsMargins(28, 0, 28, 0)
        row.setSpacing(18)
        self.tabs: list[QPushButton] = []
        for index, key in enumerate(_TAB_KEYS):
            button = QPushButton(self._t(key))
            button.setObjectName("tab")
            button.setCheckable(True)
            button.clicked.connect(lambda _checked=False, i=index: self._select_tab(i))
            self.tabs.append(button)
            row.addWidget(button)
        row.addStretch(1)
        return bar

    def _button_page(self) -> QWidget:
        page = QWidget()
        row = QHBoxLayout(page)
        row.setContentsMargins(24, 8, 24, 8)
        row.addWidget(self._column(range(6)))
        self.canvas = MouseCanvas(self.prefs.marcadores)
        row.addWidget(self.canvas, 1)
        row.addWidget(self._column(range(6, 11)))
        return page

    def _column(self, indexes: range) -> QWidget:
        box = QWidget()
        box.setFixedWidth(230)
        column = QVBoxLayout(box)
        column.setSpacing(8)
        column.addStretch(1)
        for index in indexes:
            button = QPushButton(f"{index + 1}    {assignment_label(self.prefs.idioma, DEFAULT_BUTTON_IDS[index])}")
            button.setObjectName("assign")
            button.clicked.connect(lambda _checked=False, i=index: self._assign(i))
            self.rows.append(button)
            column.addWidget(button)
        column.addStretch(1)
        return box

    def _performance_page(self) -> QWidget:
        page = QWidget()
        column = QVBoxLayout(page)
        column.setContentsMargins(48, 28, 48, 16)
        self.rate_caption = _caption(self._t("rate"))
        column.addWidget(self.rate_caption)
        rates = QHBoxLayout()
        for hz in (125, 250, 500, 1000):
            button = QPushButton(f"{hz} Hz")
            button.setObjectName("choice")
            button.setCheckable(True)
            self.rate_group.addButton(button, hz)
            rates.addWidget(button)
        column.addLayout(rates)
        column.addSpacing(18)
        self.dpi_caption = _caption("DPI")
        column.addWidget(self.dpi_caption)
        dpi_row = QHBoxLayout()
        for number in range(1, 6):
            cell = QVBoxLayout()
            cell.addWidget(QLabel(str(number)))
            field = QLineEdit()
            field.setObjectName("dpi")
            self.dpi_boxes.append(field)
            cell.addWidget(field)
            dpi_row.addLayout(cell)
        column.addLayout(dpi_row)
        column.addStretch(1)
        return page

    def _lighting_page(self) -> QWidget:
        page = QWidget()
        row = QHBoxLayout(page)
        row.setContentsMargins(48, 24, 48, 16)
        modes = QVBoxLayout()
        self.mode_caption = _caption(self._t("mode"))
        modes.addWidget(self.mode_caption)
        self.mode_buttons: list[QPushButton] = []
        for index, key in enumerate(MODE_IDS):
            button = QPushButton(self._t(f"mode.{key}"))
            button.setObjectName("choice")
            button.setCheckable(True)
            self.mode_group.addButton(button, index)
            self.mode_buttons.append(button)
            modes.addWidget(button)
        modes.addStretch(1)
        side = QVBoxLayout()
        self.color_caption = _caption(self._t("color"))
        side.addWidget(self.color_caption)
        self.color_button.setFixedHeight(42)
        side.addWidget(self.color_button)
        bar = RainbowBar()
        bar.picked.connect(self._set_color)
        side.addWidget(bar)
        self.brightness_caption = QLabel(self._t("brightness"))
        side.addWidget(self.brightness_caption)
        side.addWidget(self.brightness)
        self.speed_caption = QLabel(self._t("speed"))
        side.addWidget(self.speed_caption)
        side.addWidget(self.speed)
        side.addStretch(1)
        row.addLayout(modes, 1)
        row.addSpacing(36)
        row.addLayout(side, 1)
        return page

    def _armoury_page(self) -> QWidget:
        page = QWidget()
        column = QVBoxLayout(page)
        column.setContentsMargins(48, 24, 48, 16)
        self.macro_caption = _caption(self._t("macros"))
        column.addWidget(self.macro_caption)
        column.addWidget(self.macros, 1)
        tools = QHBoxLayout()
        self.macro_tools: list[QPushButton] = []
        for key, kind in zip(_MACRO_TOOLS, _MACRO_KINDS, strict=True):
            button = QPushButton(self._t(key))
            button.setObjectName("tool")
            button.clicked.connect(lambda _checked=False, name=kind: self._macro(name))
            self.macro_tools.append(button)
            tools.addWidget(button)
        column.addLayout(tools)
        return page

    def _footer(self) -> QWidget:
        box = QWidget()
        box.setObjectName("footer")
        column = QVBoxLayout(box)
        column.setContentsMargins(22, 8, 22, 8)
        top = QHBoxLayout()
        self.profile_buttons: list[QPushButton] = []
        for number in (1, 2):
            button = QPushButton(self._t("profile").format(n=number))
            button.setObjectName("profile")
            button.setCheckable(True)
            button.clicked.connect(lambda _checked=False, n=number: self._switch_profile(n))
            self.profile_buttons.append(button)
            top.addWidget(button)
        top.addSpacing(16)
        self.description_label = QLabel(self._t("description"))
        top.addWidget(self.description_label)
        top.addWidget(self.description, 1)
        top.addWidget(self.correlation)
        self.export_button = QPushButton(self._t("export"))
        self.export_button.setObjectName("link")
        self.export_button.clicked.connect(self._export)
        self.import_button = QPushButton(self._t("import"))
        self.import_button.setObjectName("link")
        self.import_button.clicked.connect(self._import)
        top.addWidget(self.export_button)
        top.addWidget(self.import_button)
        column.addLayout(top)
        actions = QHBoxLayout()
        actions.addStretch(1)
        self.restore_button = QPushButton(self._t("restore"))
        self.restore_button.setObjectName("ghost")
        self.restore_button.clicked.connect(self._restore)
        self.apply_button = QPushButton(self._t("apply"))
        self.apply_button.setObjectName("application")
        self.apply_button.clicked.connect(self._apply)
        actions.addWidget(self.restore_button)
        actions.addWidget(self.apply_button)
        column.addLayout(actions)
        bottom = QHBoxLayout()
        self.driver = QLabel(self._t("driver"))
        self.driver.setObjectName("driver")
        self.dedication = QLabel(self._t("dedication"))
        self.dedication.setObjectName("dedication")
        self.dedication.setOpenExternalLinks(True)
        self.dedication.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        bottom.addWidget(self.driver)
        bottom.addSpacing(28)
        bottom.addWidget(self.dedication)
        bottom.addStretch(1)
        bottom.addWidget(self.status)
        column.addLayout(bottom)
        return box

    def _settings_page(self) -> QWidget:
        page = QWidget()
        column = QVBoxLayout(page)
        column.setContentsMargins(48, 28, 48, 16)
        column.setSpacing(12)
        self.language_caption = _caption(self._t("settings.language"))
        column.addWidget(self.language_caption)
        languages = QHBoxLayout()
        self.language_group = QButtonGroup(self)
        self.language_buttons: dict[str, QPushButton] = {}
        for code, label in (("pt-BR", "Português (Brasil)"), ("en", "English")):
            button = QPushButton(label)
            button.setObjectName("choice")
            button.setCheckable(True)
            button.setMinimumWidth(220)
            button.setChecked(code == self.prefs.idioma)
            self.language_group.addButton(button)
            button.clicked.connect(lambda _checked=False, name=code: self._choose_language(name))
            self.language_buttons[code] = button
            languages.addWidget(button)
        languages.addStretch(1)
        column.addLayout(languages)
        column.addSpacing(18)
        self.autostart = QCheckBox(self._t("settings.autostart"))
        self.autostart.setChecked(self.prefs.iniciar_com_sistema)
        self.autostart.toggled.connect(self._toggle_autostart)
        column.addWidget(self.autostart)
        self.autostart_hint = QLabel(self._t("settings.autostart_hint"))
        self.autostart_hint.setObjectName("hint")
        column.addWidget(self.autostart_hint)
        column.addStretch(1)
        return page

    def _choose_language(self, code: str) -> None:
        if code == self.prefs.idioma:
            return
        self.prefs.idioma = code
        save_preferences(self.prefs)
        self._retranslate()
        self.status.setText(self._t("status.language"))

    def _toggle_autostart(self, enabled: bool) -> None:
        self.prefs.iniciar_com_sistema = enabled
        save_preferences(self.prefs)
        key = "status.autostart_on" if enabled else "status.autostart_off"
        self.status.setText(self._t(key))

    def _retranslate(self) -> None:
        self.badge.setText(self._t("badge"))
        for button, key in zip(self.tabs, _TAB_KEYS, strict=True):
            button.setText(self._t(key))
        for index, button in enumerate(self.rows):
            name = button.text().split(maxsplit=1)[1]
            button.setText(f"{index + 1}    {assignment_label(self.prefs.idioma, name)}")
        self.rate_caption.setText(self._t("rate"))
        self.mode_caption.setText(self._t("mode"))
        for button, key in zip(self.mode_buttons, MODE_IDS, strict=True):
            button.setText(self._t(f"mode.{key}"))
        self.color_caption.setText(self._t("color"))
        self.brightness_caption.setText(self._t("brightness"))
        self.speed_caption.setText(self._t("speed"))
        self.macro_caption.setText(self._t("macros"))
        for button, key in zip(self.macro_tools, _MACRO_TOOLS, strict=True):
            button.setText(self._t(key))
        for number, button in enumerate(self.profile_buttons, start=1):
            button.setText(self._t("profile").format(n=number))
        self.description_label.setText(self._t("description"))
        self.description.setText(profile_name(self.prefs.idioma, self.description.text(), self.library.active))
        self.correlation.setText(self._t("correlation"))
        self.export_button.setText(self._t("export"))
        self.import_button.setText(self._t("import"))
        self.restore_button.setText(self._t("restore"))
        self.apply_button.setText(self._t("apply"))
        self.driver.setText(self._t("driver"))
        self.dedication.setText(self._t("dedication"))
        self.language_caption.setText(self._t("settings.language"))
        self.autostart.setText(self._t("settings.autostart"))
        self.autostart_hint.setText(self._t("settings.autostart_hint"))
        if self.open_action is not None:
            self.open_action.setText(self._t("tray.open"))
        if self.quit_action is not None:
            self.quit_action.setText(self._t("tray.quit"))

    def _select_tab(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        for tab_index, button in enumerate(self.tabs):
            button.setChecked(tab_index == index)

    def _assign(self, index: int) -> None:
        menu = QMenu(self)
        for key in ASSIGNMENT_IDS:
            label = assignment_label(self.prefs.idioma, key)
            action = menu.addAction(label)
            action.triggered.connect(lambda _checked=False, i=index, text=label: self._rename(i, text))
        button = self.rows[index]
        menu.exec(button.mapToGlobal(button.rect().bottomLeft()))

    def _rename(self, index: int, text: str) -> None:
        self.rows[index].setText(f"{index + 1}    {text}")

    def _switch_profile(self, number: int) -> None:
        if number == self.library.active:
            self._paint_profiles()
            return
        try:
            self._store_form()
        except ProtocolError as exc:
            self.status.setText(str(exc))
            self._paint_profiles()
            return
        self.library.active = number
        self._load(self.library.current())
        self._persist()

    def _macro(self, kind: str) -> None:
        if kind == "delete":
            row = self.macros.currentRow()
            if row >= 0:
                self.macros.takeItem(row)
            return
        count = self.macros.count() + 1
        labels = {
            "select": self._t("macro.item.select").format(n=count),
            "record": self._t("macro.item.record").format(n=count),
            "delay": self._t("macro.item.delay").format(n=count),
            "click": self._t("macro.item.click").format(n=count),
        }
        self.macros.addItem(labels[kind])

    def _apply(self) -> None:
        try:
            self._store_form()
            settings = self.library.current()
            ready = parse_settings(settings.to_dict(), settings)
            ready.gravar_luz = True
            ready.light_bytes()
            apply_settings(ready)
        except (ProtocolError, MouseError) as exc:
            self.status.setText(str(exc))
            return
        self.library.slots[self.library.active] = ready
        SESSION.settings = ready
        self._persist()
        self.status.setText(self._status_applied(ready))

    def _restore(self) -> None:
        number = self.library.active
        self.library.slots[number] = Settings(
            perfil=number,
            nome=self._t("profile.default").format(n=number),
            cor="#ff0000",
        )
        self._load(self.library.slots[number])
        self.status.setText(self._t("status.factory"))

    def _export(self) -> None:
        self._store_form()
        path, _filter = QFileDialog.getSaveFileName(self, self._t("export"), "zelotes-c18.json", "JSON (*.json)")
        if not path:
            return
        from pathlib import Path

        Path(path).write_text(
            __import__("json").dumps(
                {"ativo": self.library.active, "perfis": [self.library.slots[1].to_dict(), self.library.slots[2].to_dict()], "macros": self._macro_names()},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def _import(self) -> None:
        path, _filter = QFileDialog.getOpenFileName(self, self._t("import"), "", "JSON (*.json)")
        if not path:
            return
        try:
            payload = __import__("json").loads(open(path, encoding="utf-8").read())
            library = Library(active=int(payload.get("ativo", 1)))
            for item in payload.get("perfis", []):
                settings = parse_settings(item, remember=True)
                if settings.perfil in (1, 2):
                    library.slots[settings.perfil] = settings
            library.macros = [str(item) for item in payload.get("macros", [])]
        except (OSError, ValueError, ProtocolError) as exc:
            self.status.setText(str(exc))
            return
        self.library = library
        self.macros.clear()
        self.macros.addItems(library.macros)
        self._load(library.current())
        self._persist()

    def _pick_color(self) -> None:
        chosen = QColorDialog.getColor(self.color, self, self._t("color"))
        if chosen.isValid():
            self._set_color(chosen)

    def _set_color(self, color: QColor) -> None:
        self.color = color
        self.color_button.setStyleSheet(f"background:{color.name()};")

    def _load(self, settings: Settings) -> None:
        for index, name in enumerate(settings.botoes):
            self.rows[index].setText(f"{index + 1}    {assignment_label(self.prefs.idioma, name)}")
        self._check_mode(settings.modo)
        rate = self.rate_group.button(settings.hz)
        if rate is not None:
            rate.setChecked(True)
        self.brightness.setValue(settings.brilho)
        self.speed.setValue(settings.velocidade)
        for field, value in zip(self.dpi_boxes, settings.dpi, strict=True):
            field.setText(str(value))
        fallback = self._t("profile.default").format(n=settings.perfil)
        self.description.setText(profile_name(self.prefs.idioma, settings.nome or fallback, settings.perfil))
        self.correlation.setChecked(settings.correlacao)
        self._set_color(QColor(settings.cor))
        self._paint_profiles()

    def _store_form(self) -> None:
        current = self.library.current()
        names = tuple(button.text().split(maxsplit=1)[1] for button in self.rows)
        dpi: list[int] = []
        for field in self.dpi_boxes:
            try:
                dpi.append(int(field.text()))
            except ValueError as exc:
                raise ProtocolError(self._t("status.dpi")) from exc
        mode = MODE_IDS[self.mode_group.checkedId()] if self.mode_group.checkedId() >= 0 else "padrao"
        settings = Settings(
            perfil=self.library.active,
            hz=self.rate_group.checkedId() if self.rate_group.checkedId() > 0 else current.hz,
            modo=mode,
            nivel=1 if mode in ("padrao", "fluxo", "desligado") else min(current.nivel or 1, 10),
            brilho=self.brightness.value(),
            velocidade=self.speed.value(),
            cor=self.color.name(),
            dpi=tuple(dpi),  # type: ignore[arg-type]
            nome=self.description.text().strip() or self._t("profile.default").format(n=self.library.active),
            botoes=names,
            correlacao=self.correlation.isChecked(),
            programa=current.programa,
        )
        self.library.slots[self.library.active] = settings
        self.library.macros = self._macro_names()

    def _persist(self) -> None:
        save_library(self.library)
        SESSION.settings = self.library.current()
        self._saved_mtime = _mtime()

    def _reload_external(self) -> None:
        mtime = _mtime()
        if mtime == self._saved_mtime:
            return
        self.library = load_library()
        self.macros.clear()
        self.macros.addItems(self.library.macros)
        self._load(self.library.current())
        self._saved_mtime = mtime

    def _paint_profiles(self) -> None:
        for number, button in enumerate(self.profile_buttons, start=1):
            button.setChecked(number == self.library.active)

    def _check_mode(self, mode: str) -> None:
        if mode not in MODE_IDS:
            return
        button = self.mode_group.button(MODE_IDS.index(mode))
        if button is not None:
            button.setChecked(True)

    def _t(self, key: str) -> str:
        return tr(self.prefs.idioma, key)

    def _status_applied(self, settings: Settings) -> str:
        modo = self._t(f"mode.{settings.modo}")
        dpi = ", ".join(str(item) for item in settings.dpi)
        if settings.gravar_luz:
            text = self._t("status.applied_light").format(perfil=settings.perfil, hz=settings.hz, modo=modo, dpi=dpi)
        else:
            text = self._t("status.applied").format(perfil=settings.perfil, hz=settings.hz)
        return f"{text} {self._t('status.local_only')}"

    def _macro_names(self) -> list[str]:
        return [self.macros.item(row).text() for row in range(self.macros.count())]


# Frações da foto: clique, menu, roda, avançar, voltar, DPI e o analógico.
_MARKS = {
    1: (0.6427, 0.4),
    2: (0.8215, 0.4306),
    3: (0.695, 0.19),
    4: (0.2968, 0.3484),
    5: (0.26, 0.4707),
    6: (0.765, 0.325),
    7: (0.3647, 0.3619),
    8: (0.3463, 0.4833),
    9: (0.3005, 0.4248),
    10: (0.43, 0.425),
    11: (0.3599, 0.4227),
}


class MouseCanvas(QWidget):
    """Foto do C-18 com os números fixos em cima de cada controle."""

    def __init__(self, saved: dict[int, tuple[float, float]] | None = None) -> None:
        super().__init__()
        self.setMinimumSize(280, 360)
        self._photo = QPixmap(str(Path(__file__).resolve().parent / "ui" / "mouse.png"))
        self.marks = {number: _MARKS[number] for number in range(1, 12)}
        if saved:
            self.marks.update(saved)

    def mark_point(self, number: int) -> QPointF:
        origin_x, origin_y, fitted = self._fitted()
        fx, fy = self.marks[number]
        return QPointF(origin_x + fx * fitted.width(), origin_y + fy * fitted.height())

    def _fitted(self) -> tuple[float, float, QPixmap]:
        fitted = self._photo.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        origin_x = (self.width() - fitted.width()) / 2
        origin_y = (self.height() - fitted.height()) / 2
        return origin_x, origin_y, fitted

    def paintEvent(self, _event: object) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        if self._photo.isNull():
            painter.end()
            return
        origin_x, origin_y, fitted = self._fitted()
        painter.drawPixmap(int(origin_x), int(origin_y), fitted)
        painter.setFont(QFont("Sans Serif", 8, QFont.Weight.Bold))
        for number in range(1, 12):
            center = self.mark_point(number)
            painter.setBrush(QColor(RED))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(center, 8, 8)
            painter.setPen(QColor("white"))
            painter.drawText(int(center.x() - 8), int(center.y() - 8), 16, 16, Qt.AlignmentFlag.AlignCenter, str(number))
        painter.end()


class RainbowBar(QWidget):
    from PySide6.QtCore import Signal

    picked = Signal(QColor)

    def __init__(self) -> None:
        super().__init__()
        self.setFixedHeight(28)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def paintEvent(self, _event: object) -> None:
        painter = QPainter(self)
        gradient = QLinearGradient(0, 0, self.width(), 0)
        for stop, color in (
            (0, "#ff0000"),
            (0.16, "#ffff00"),
            (0.33, "#00ff00"),
            (0.5, "#00ffff"),
            (0.66, "#0000ff"),
            (0.83, "#ff00ff"),
            (1, "#ff0000"),
        ):
            gradient.setColorAt(stop, QColor(color))
        painter.fillRect(self.rect().adjusted(0, 4, 0, -4), gradient)
        painter.end()

    def mousePressEvent(self, event: object) -> None:
        image = self.grab().toImage()
        point = event.position()  # type: ignore[attr-defined]
        color = image.pixelColor(int(point.x()), int(point.y()))
        if color.isValid():
            self.picked.emit(color)


def _slider() -> QSlider:
    slider = QSlider(Qt.Orientation.Horizontal)
    slider.setRange(0, 10)
    slider.setValue(10)
    return slider


def _caption(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("caption")
    return label


def _mtime() -> float:
    path = config_path()
    return path.stat().st_mtime if path.is_file() else 0


_STYLE = f"""
#shell, QMainWindow {{ background: #121212; color: #f2f2f2; }}
QLabel {{ color: #f2f2f2; }}
#header {{
  background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2a2a2a, stop:1 #101010);
  border-bottom: 1px solid #3a0000;
}}
#logo {{ color: {RED}; font-size: 34px; font-style: italic; font-weight: 700; letter-spacing: 2px; }}
#badge {{
  color: #d0d0d0;
  border: 1px solid #5a5a5a;
  padding: 4px 8px;
  font-size: 11px;
  letter-spacing: 1px;
}}
#tabbar {{ background: #161616; }}
#tab {{
  background: transparent;
  color: #b5b5b5;
  border: none;
  border-bottom: 2px solid transparent;
  padding: 10px 4px;
  font-size: 16px;
}}
#tab:checked {{ color: {RED}; border-bottom: 2px solid {RED}; }}
#assign, #choice, #tool, #ghost, #profile {{
  background: #2a2a2a;
  color: white;
  border: 1px solid #3c3c3c;
  border-radius: 3px;
  padding: 8px 12px;
  text-align: left;
}}
#choice:checked, #profile:checked {{ background: {RED}; border-color: {RED}; }}
#application {{
  background: #3a3a3a;
  color: white;
  border: 1px solid #6a6a6a;
  border-radius: 4px;
  padding: 8px 22px;
  font-size: 16px;
}}
#ghost {{ text-align: center; }}
#link {{ background: transparent; color: #d0d0d0; border: none; }}
#description, #dpi {{
  background: white;
  color: black;
  border: 1px solid #888;
  padding: 4px 6px;
}}
#footer {{ background: #101010; border-top: 1px solid #2a2a2a; }}
#driver, #status, #hint, #dedication {{ color: #8d8d8d; font-size: 12px; }}
#dedication a {{ color: #d0d0d0; text-decoration: none; }}
#caption {{ color: #dddddd; font-size: 15px; }}
QListWidget {{ background: #1b1b1b; color: white; border: 1px solid #333; }}
QCheckBox {{ color: #dddddd; }}
QSlider::groove:horizontal {{ height: 4px; background: #444; }}
QSlider::handle:horizontal {{ width: 14px; margin: -6px 0; background: {RED}; border-radius: 7px; }}
"""
