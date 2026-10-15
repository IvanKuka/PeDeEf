"""Application preferences, committed only when the user applies them."""

from PySide6.QtWidgets import QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLabel, QVBoxLayout, QWidget

from pdftool.gui.settings import Settings, THEMES, THUMBNAIL_SIZES


class SettingsDialog(QDialog):
    def __init__(self, settings: Settings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Nastavenia")
        self.setMinimumWidth(440)
        self._settings = settings
        self._theme = QComboBox()
        self._thumbnails = QComboBox()
        self._images = QComboBox()
        for value, label in THEMES:
            self._theme.addItem(label, value)
        for value, label in THUMBNAIL_SIZES:
            self._thumbnails.addItem(label, value)
        self._images.addItem("A4 s okrajmi", "a4")
        self._images.addItem("Bez okrajov, podľa obrázka", "image")
        for combo, value in ((self._theme, settings.theme()), (self._thumbnails, settings.thumbnail_size()),
                             (self._images, settings.image_format())):
            combo.setCurrentIndex(combo.findData(value))
        form = QFormLayout()
        form.addRow("Téma:", self._theme)
        form.addRow("Náhľady strán:", self._thumbnails)
        form.addRow("Obrázky pri zlučovaní:", self._images)
        self._updates = QCheckBox("Pri spustení skontrolovať novú verziu na GitHube")
        self._updates.setToolTip("Zistí sa len číslo najnovšej verzie; neodosielajú sa žiadne dokumenty ani údaje o vás.")
        self._updates.setChecked(settings.check_for_updates())
        form.addRow("Aktualizácie:", self._updates)
        hint = QLabel("Zmeny sa použijú ihneď po uložení a zapamätajú sa aj na ďalšie spustenie.")
        hint.setWordWrap(True)
        hint.setObjectName("hint")
        buttons = QDialogButtonBox()
        buttons.addButton("Zrušiť", QDialogButtonBox.ButtonRole.RejectRole)
        buttons.addButton("Uložiť nastavenia", QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(hint)
        layout.addWidget(buttons)

    def accept(self) -> None:
        self._settings.set_preferences(self._theme.currentData(), self._thumbnails.currentData(), self._images.currentData())
        self._settings.set_check_for_updates(self._updates.isChecked())
        super().accept()
