"""Real PKCS#12 signatures, including a check with cryptography independent of pyHanko."""

import hashlib
from datetime import datetime, timedelta, timezone

import pytest
from asn1crypto import cms
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from pypdf import PdfReader

from pdftool.gui import pages_tab
from pdftool.gui.digital_signature_dialog import DigitalSignatureDialog
from pdftool.operations import PdfToolError
from pdftool.signing import inspect_signatures, load_identity, sign_pdf
from tests.helpers import make_pdf


@pytest.fixture
def certificate(tmp_path):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(x509.NameOID.COMMON_NAME, "Testovací podpis – Žilina")])
    now = datetime.now(timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
            .serial_number(x509.random_serial_number()).not_valid_before(now - timedelta(days=1))
            .not_valid_after(now + timedelta(days=30)).sign(key, hashes.SHA256()))
    path = tmp_path / "identity.pfx"
    path.write_bytes(pkcs12.serialize_key_and_certificates(
        b"test", key, cert, None, serialization.BestAvailableEncryption(b"test-password")
    ))
    return path, key, cert


def test_real_signature_verifies_with_cryptography_and_detects_content_tampering(tmp_path, certificate):
    path, key, _ = certificate
    source = make_pdf(tmp_path / "source.pdf", [101])
    original = source.read_bytes()
    output = tmp_path / "signed.pdf"
    identity = load_identity(path, "test-password")
    assert "signing_key" not in repr(identity) and "test-password" not in repr(identity)
    sign_pdf(source, identity, output, "Schválené")
    assert source.read_bytes() == original
    [status] = inspect_signatures(output)
    assert status.integrity_ok and status.coverage.name == "ENTIRE_FILE"

    data = output.read_bytes()
    signature = next(iter(PdfReader(output).get_fields().values()))["/V"]
    start, length, rest, rest_length = map(int, signature["/ByteRange"])
    digest = hashlib.sha256(data[start:start + length] + data[rest:rest + rest_length]).digest()
    signer = cms.ContentInfo.load(bytes(signature["/Contents"]))["content"]["signer_infos"][0]
    attrs = signer["signed_attrs"]
    recorded = next(item["values"][0].native for item in attrs if item["type"].native == "message_digest")
    assert recorded == digest
    key.public_key().verify(signer["signature"].native, attrs.untag().dump(), padding.PKCS1v15(), hashes.SHA256())

    altered = data.replace(b"/MediaBox [ 0.0 0.0 101 500 ]", b"/MediaBox [ 0.0 0.0 102 500 ]", 1)
    if altered == data:
        altered = data.replace(b"/MediaBox [ 0 0 101 500 ]", b"/MediaBox [ 0 0 102 500 ]", 1)
    assert altered != data
    tampered = tmp_path / "tampered.pdf"
    tampered.write_bytes(altered)
    assert not inspect_signatures(tampered)[0].integrity_ok
    target = tmp_path / "existing.pdf"
    target.write_bytes(b"previous output")
    with pytest.raises(PdfToolError):
        sign_pdf(tampered, identity, target)
    assert target.read_bytes() == b"previous output"


def test_adding_a_second_signature_preserves_the_first_revision(tmp_path, certificate):
    identity = load_identity(certificate[0], "test-password")
    source = make_pdf(tmp_path / "source.pdf", [101])
    first, second = tmp_path / "first.pdf", tmp_path / "second.pdf"
    sign_pdf(source, identity, first)
    sign_pdf(first, identity, second)
    results = inspect_signatures(second)
    assert len(results) == 2 and all(item.integrity_ok for item in results)
    assert results[0].coverage.name == "ENTIRE_REVISION"
    assert second.read_bytes().startswith(first.read_bytes())


def test_signing_preserves_pdf_encryption(tmp_path, certificate):
    source = make_pdf(tmp_path / "source.pdf", [101], password="pdf-password")
    output = tmp_path / "signed.pdf"
    sign_pdf(source, load_identity(certificate[0], "test-password"), output, password="pdf-password")
    reader = PdfReader(output)
    assert reader.is_encrypted and reader.decrypt("pdf-password")
    assert inspect_signatures(output, "pdf-password")[0].integrity_ok


def test_bad_password_missing_key_and_source_overwrite_are_rejected(tmp_path, certificate):
    path, _, cert = certificate
    with pytest.raises(PdfToolError, match="heslo"):
        load_identity(path, "wrong")
    no_key = tmp_path / "no-key.p12"
    no_key.write_bytes(pkcs12.serialize_key_and_certificates(b"test", None, cert, None, serialization.NoEncryption()))
    with pytest.raises(PdfToolError, match="súkromný kľúč"):
        load_identity(no_key, "")
    source = make_pdf(tmp_path / "source.pdf", [101])
    before = source.read_bytes()
    with pytest.raises(PdfToolError, match="iným názvom"):
        sign_pdf(source, load_identity(path, "test-password"), source)
    assert source.read_bytes() == before


def test_certificate_dialog_requires_review_and_clears_identity_on_input_changes(app, certificate):
    dialog = DigitalSignatureDialog()
    dialog._path.setText(str(certificate[0]))
    dialog._password.setText("test-password")
    assert not dialog._sign_button.isEnabled()
    dialog._load_identity()
    assert dialog._sign_button.isEnabled() and "Žilina" in dialog._summary.text()
    dialog._password.setText("different")
    assert not dialog._sign_button.isEnabled() and dialog._identity is None
    dialog.release_identity()
    assert dialog._password.text() == ""


def test_tab_signs_pending_rotation_and_opens_verified_output(app, dialogs, tmp_path, monkeypatch, certificate):
    source = make_pdf(tmp_path / "source.pdf", [101])
    output = tmp_path / "signed.pdf"
    dialogs.save_path = output
    identity = load_identity(certificate[0], "test-password")
    monkeypatch.setattr(DigitalSignatureDialog, "exec", lambda self: self.DialogCode.Accepted)
    monkeypatch.setattr(DigitalSignatureDialog, "identity", lambda self: identity)
    tab = pages_tab.PagesTab()
    tab.open_file(source)
    tab._list.item(0).setSelected(True)
    tab._rotate_selected(90)
    tab._sign_certificate()
    assert tab._source_path == output and not tab.has_unsaved_changes()
    assert PdfReader(output).pages[0].rotation == 90
    assert inspect_signatures(output)[0].integrity_ok


def test_cancelled_signature_does_not_change_open_work(app, dialogs, tmp_path, monkeypatch):
    source = make_pdf(tmp_path / "source.pdf", [101])
    before = source.read_bytes()
    monkeypatch.setattr(DigitalSignatureDialog, "exec", lambda self: self.DialogCode.Rejected)
    tab = pages_tab.PagesTab()
    tab.open_file(source)
    tab._sign_certificate()
    assert source.read_bytes() == before and not dialogs.successes


def test_signing_failure_leaves_existing_output_untouched(tmp_path, certificate, monkeypatch):
    from pdftool import signing
    source = make_pdf(tmp_path / "source.pdf", [101])
    output = tmp_path / "existing.pdf"
    output.write_bytes(b"keep this result")
    def fail(*args, **kwargs):
        raise ValueError("unsupported signing operation")
    monkeypatch.setattr(signing.signers.PdfSigner, "sign_pdf", fail)
    with pytest.raises(PdfToolError, match="nepodarilo podpísať"):
        sign_pdf(source, load_identity(certificate[0], "test-password"), output)
    assert output.read_bytes() == b"keep this result"


def test_certified_document_forbidding_changes_cannot_get_another_signature(tmp_path, certificate):
    from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
    from pyhanko.sign import signers
    from pyhanko.sign.fields import MDPPerm
    source = make_pdf(tmp_path / "source.pdf", [101])
    identity = load_identity(certificate[0], "test-password")
    certified = tmp_path / "certified.pdf"
    with source.open("rb") as stream, certified.open("wb") as output:
        signers.PdfSigner(
            signers.PdfSignatureMetadata(field_name="Certification", certify=True, docmdp_permissions=MDPPerm.NO_CHANGES),
            identity.signer,
        ).sign_pdf(IncrementalPdfFileWriter(stream), output=output)
    target = tmp_path / "second.pdf"
    with pytest.raises(PdfToolError):
        sign_pdf(certified, identity, target)
    assert not target.exists()


def test_elliptic_curve_certificate_can_sign_pdf(tmp_path):
    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(x509.NameOID.COMMON_NAME, "EC test")])
    now = datetime.now(timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
            .serial_number(x509.random_serial_number()).not_valid_before(now - timedelta(days=1))
            .not_valid_after(now + timedelta(days=1)).sign(key, hashes.SHA256()))
    pfx = tmp_path / "ec.p12"
    pfx.write_bytes(pkcs12.serialize_key_and_certificates(b"ec", key, cert, None, serialization.NoEncryption()))
    source = make_pdf(tmp_path / "source.pdf", [101])
    target = tmp_path / "signed.pdf"
    sign_pdf(source, load_identity(pfx, ""), target)
    assert inspect_signatures(target)[0].integrity_ok
