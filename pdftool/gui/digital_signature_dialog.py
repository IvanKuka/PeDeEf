"""Choose a PKCS#12 identity and review it before signing a final document."""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QHBoxLayout,
    QLabel, QLineEdit, QMessageBox, QPushButton, QVBoxLayout, QWidget,
)

from pdftool.gui.widgets import busy_cursor
from pdftool.operations import PdfToolError
from pdftool.signing import SigningIdentity, load_identity


class DigitalSignatureDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Digitálne podpísať PDF – P12/PFX")
        self.setMinimumWidth(540)
        self._identity: SigningIdentity | None = None
        self._path = QLineEdit()
        self._path.setPlaceholderText("Vyberte súbor .p12 alebo .pfx")
        browse = QPushButton("Vybrať…")
        browse.clicked.connect(self._choose_file)
        file_row = QHBoxLayout()
        file_row.addWidget(self._path)
        file_row.addWidget(browse)
        self._password = QLineEdit()
        self._password.setEchoMode(QLineEdit.EchoMode.Password)
        self._reason = QLineEdit()
        self._reason.setPlaceholderText("Voliteľné")
        load = QPushButton("Načítať a skontrolovať certifikát")
        load.clicked.connect(self._load_identity)
        form = QFormLayout()
        form.addRow("Certifikát P12/PFX:", file_row)
        form.addRow("Heslo certifikátu:", self._password)
        form.addRow("Dôvod podpisu:", self._reason)
        self._summary = QLabel("Certifikát zatiaľ nebol načítaný.")
        self._summary.setTextFormat(Qt.TextFormat.PlainText)
        self._summary.setWordWrap(True)
        notice = QLabel(
            "Podpíše sa finálny dokument. Podpis bude bez viditeľného obrázka; PDF prehliadače ho zobrazia "
            "v paneli podpisov. Podpis obrázkom je samostatná funkcia.\n\n"
            "Kľúč ani heslo sa neukladajú. Nepoužíva sa sieť ani časová pečiatka. "
            "Dôveryhodnosť a zneplatnenie certifikátu sa neoverujú."
        )
        notice.setWordWrap(True)
        notice.setObjectName("hint")
        buttons = QDialogButtonBox()
        buttons.addButton("Zrušiť", QDialogButtonBox.ButtonRole.RejectRole)
        self._sign_button = buttons.addButton("Podpísať a uložiť ako…", QDialogButtonBox.ButtonRole.AcceptRole)
        self._sign_button.setObjectName("primary")
        self._sign_button.setEnabled(False)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self._path.textChanged.connect(self._invalidate)
        self._password.textChanged.connect(self._invalidate)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(load)
        layout.addWidget(self._summary)
        layout.addWidget(notice)
        layout.addWidget(buttons)

    def _choose_file(self) -> None:
        name, _ = QFileDialog.getOpenFileName(self, "Vybrať certifikát", "", "Certifikáty (*.p12 *.pfx)")
        if name:
            self._path.setText(name)

    def _invalidate(self) -> None:
        self._identity = None
        self._summary.setText("Certifikát treba načítať a skontrolovať.")
        self._sign_button.setEnabled(False)

    def _load_identity(self) -> None:
        try:
            with busy_cursor():
                identity = load_identity(Path(self._path.text()), self._password.text())
        except PdfToolError as exc:
            QMessageBox.warning(self, "Certifikát sa nepodarilo načítať", str(exc))
            return
        self._identity = identity
        self._summary.setText(
            f"Podpisujúci: {identity.subject}\nVydavateľ: {identity.issuer}\n"
            f"Platnosť do: {identity.valid_until:%d. %m. %Y}"
        )
        self._sign_button.setEnabled(True)

    def identity(self) -> SigningIdentity:
        assert self._identity is not None
        return self._identity

    def reason(self) -> str:
        return self._reason.text().strip()

    def release_identity(self) -> None:
        self._identity = None
        self._password.clear()
