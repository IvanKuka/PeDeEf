"""PKCS#12 signing and offline integrity inspection, using pyHanko.

Signatures are appended incrementally to the final PDF; ordinary page export must
never be used afterwards to "save" the signature. No network services are used.
Private keys and passwords remain in memory and are never logged or persisted.
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from cryptography import x509
from cryptography.exceptions import UnsupportedAlgorithm
from cryptography.hazmat.primitives.serialization import pkcs12
from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
from pyhanko.pdf_utils.reader import PdfFileReader
from pyhanko.sign import signers
from pyhanko.sign.validation import validate_pdf_signature
from pyhanko.sign.validation.status import SignatureCoverageLevel
from pyhanko_certvalidator import ValidationContext

from pdftool.operations import PdfToolError, write_file_atomically


@dataclass(frozen=True)
class SigningIdentity:
    subject: str
    issuer: str
    valid_until: datetime
    signer: signers.SimpleSigner = field(repr=False, compare=False)


@dataclass(frozen=True)
class SignatureResult:
    field_name: str
    subject: str
    intact: bool
    valid: bool
    coverage: SignatureCoverageLevel
    allowed_changes: bool

    @property
    def integrity_ok(self) -> bool:
        return self.intact and self.valid and self.coverage in (
            SignatureCoverageLevel.ENTIRE_FILE, SignatureCoverageLevel.ENTIRE_REVISION
        ) and self.allowed_changes


def load_identity(path: Path, password: str) -> SigningIdentity:
    try:
        data = Path(path).read_bytes()
    except OSError as exc:
        raise PdfToolError("Certifikát sa nepodarilo prečítať. Skontrolujte cestu a prístup k súboru.") from exc
    try:
        key, cert, _ = pkcs12.load_key_and_certificates(data, password.encode("utf-8") or None)
    except (ValueError, TypeError, UnsupportedAlgorithm) as exc:
        raise PdfToolError("P12/PFX sa nepodarilo otvoriť. Skontrolujte heslo a formát súboru.") from exc
    if key is None or cert is None:
        raise PdfToolError("P12/PFX musí obsahovať certifikát aj jeho súkromný kľúč.")
    now = datetime.now(timezone.utc)
    if not cert.not_valid_before_utc <= now <= cert.not_valid_after_utc:
        raise PdfToolError("Certifikát ešte nie je platný alebo jeho platnosť už skončila.")
    try:
        usage = cert.extensions.get_extension_for_class(x509.KeyUsage).value
        if not (usage.digital_signature or usage.content_commitment):
            raise PdfToolError("Tento certifikát nepovoľuje digitálne podpisovanie.")
    except x509.ExtensionNotFound:
        pass  # an absent key-usage extension places no such restriction on the key
    try:
        signer = signers.SimpleSigner.load_pkcs12_data(data, (), password.encode("utf-8") or None)
    except (ValueError, TypeError) as exc:
        raise PdfToolError("Kľúč v tomto P12/PFX nie je podporovaný na podpisovanie PDF.") from exc
    names = cert.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)
    subject = names[0].value if names else cert.subject.rfc4514_string()
    return SigningIdentity(subject, cert.issuer.rfc4514_string(), cert.not_valid_after_utc, signer)


def _inspect(data: bytes, password: str | None = None) -> list[SignatureResult]:
    reader = PdfFileReader(io.BytesIO(data))
    if reader.security_handler is not None:
        reader.decrypt(password or "")
    results = []
    for signature in reader.embedded_regular_signatures:
        # No roots are implicitly trusted and fetching is explicitly disabled. Only the
        # cryptographic integrity/coverage fields are consumed, never a trust verdict.
        status = validate_pdf_signature(signature, ValidationContext(trust_roots=[], allow_fetching=False))
        cert = signature.signer_cert
        subject = cert.subject.native.get("common_name") or cert.subject.human_friendly
        results.append(SignatureResult(
            signature.field_name, str(subject), status.intact, status.valid, status.coverage,
            status.docmdp_ok is True,
        ))
    return results


def inspect_signatures(path: Path, password: str | None = None) -> list[SignatureResult]:
    try:
        return _inspect(Path(path).read_bytes(), password)
    except Exception as exc:
        raise PdfToolError("Podpisy sa nepodarilo overiť. PDF môže byť poškodené, nepodporované alebo chránené iným heslom.") from exc


def sign_pdf(source: Path, identity: SigningIdentity, output: Path, reason: str = "", password: str | None = None) -> None:
    source, output = Path(source), Path(output)
    if str(source.resolve()).casefold() == str(output.resolve()).casefold():
        raise PdfToolError("Podpísané PDF uložte pod iným názvom. Zdrojový súbor sa neprepisuje.")
    if datetime.now(timezone.utc) > identity.valid_until:
        raise PdfToolError("Platnosť certifikátu už skončila. Vyberte platný certifikát.")
    try:
        data = source.read_bytes()
        previous = _inspect(data, password)
        if any(not result.integrity_ok for result in previous):
            raise PdfToolError("Dokument obsahuje neplatný alebo neoveriteľný podpis. Ďalší podpis nebol pridaný.")
        writer = IncrementalPdfFileWriter(io.BytesIO(data))
        if writer.security_handler is not None:
            writer.encrypt(password or "")
        field_name = f"Podpis_{uuid4().hex}"
        metadata = signers.PdfSignatureMetadata(field_name=field_name, reason=reason or None, name=identity.subject)
        result = io.BytesIO()
        signers.PdfSigner(metadata, identity.signer).sign_pdf(writer, output=result)
        signed = result.getvalue()
        checked = _inspect(signed, password)
        if len(checked) != len(previous) + 1 or any(not item.integrity_ok for item in checked):
            raise PdfToolError("Kontrola podpísaného PDF zlyhala. Výsledok nebol uložený.")
    except PdfToolError:
        raise
    except Exception as exc:
        raise PdfToolError("PDF sa nepodarilo podpísať. Skontrolujte certifikát, heslo a povolené zmeny dokumentu.") from exc
    write_file_atomically(lambda stream: stream.write(signed), output)
