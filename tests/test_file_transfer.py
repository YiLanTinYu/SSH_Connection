import ftplib
import io
import os
import socket

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

from ui.file_transfer_dialog import FileTransferDialog
from utils.file_transfer_service import (
    FTPServiceConfig,
    FTPTransferService,
    TFTPServiceConfig,
    TFTPTransferService,
    available_transfer_backends,
)


def test_file_transfer_backends_are_available():
    assert available_transfer_backends() == {"ftp": True, "tftp": True}


def test_ftp_service_download_and_upload(tmp_path):
    source = tmp_path / "from_aomt.cfg"
    source.write_bytes(b"sysname AOMT-FTP\n")
    events = []
    service = FTPTransferService(
        FTPServiceConfig(
            root=str(tmp_path),
            bind_host="127.0.0.1",
            port=0,
            username="test",
            password="secret",
            allow_upload=True,
            passive_port_start=50100,
            passive_port_end=50110,
        ),
        events.append,
    )
    service.start()
    try:
        ftp = ftplib.FTP()
        ftp.connect("127.0.0.1", service.bound_port, timeout=3)
        ftp.login("test", "secret")
        downloaded = io.BytesIO()
        ftp.retrbinary("RETR from_aomt.cfg", downloaded.write)
        ftp.storbinary("STOR from_switch.cfg", io.BytesIO(b"save force\n"))
        ftp.quit()

        assert downloaded.getvalue() == b"sysname AOMT-FTP\n"
        assert (tmp_path / "from_switch.cfg").read_bytes() == b"save force\n"
        assert any("FTP 下载完成" in event for event in events)
        assert any("FTP 上传完成" in event for event in events)
    finally:
        service.stop()
    assert service.is_running is False


def test_tftp_service_download_and_upload(tmp_path):
    from partftpy.TftpClient import TftpClient

    source = tmp_path / "from_aomt.bin"
    source.write_bytes(b"AOMT-TFTP-DOWNLOAD")
    destination = tmp_path / "downloaded.bin"
    upload_source = tmp_path / "local-upload.bin"
    upload_source.write_bytes(b"AOMT-TFTP-UPLOAD")
    events = []
    service = TFTPTransferService(
        TFTPServiceConfig(
            root=str(tmp_path),
            bind_host="127.0.0.1",
            port=0,
            allow_upload=True,
        ),
        events.append,
    )
    service.start()
    try:
        client = TftpClient(
            "127.0.0.1",
            service.bound_port,
            af_family=socket.AF_INET,
        )
        client.download(
            "from_aomt.bin",
            str(destination),
            timeout=1,
            retries=2,
        )
        client.upload(
            "from_switch.bin",
            str(upload_source),
            timeout=1,
            retries=2,
        )

        assert destination.read_bytes() == b"AOMT-TFTP-DOWNLOAD"
        assert (tmp_path / "from_switch.bin").read_bytes() == b"AOMT-TFTP-UPLOAD"
        assert any("TFTP 开始下载" in event for event in events)
        assert any("TFTP 开始上传" in event for event in events)
    finally:
        service.stop()
    assert service.is_running is False


def test_file_transfer_dialog_protocol_controls(monkeypatch, tmp_path):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(
        "ui.file_transfer_dialog.discover_local_addresses",
        lambda: ["192.168.10.2"],
    )
    dialog = FileTransferDialog()
    try:
        dialog.root_input.setText(str(tmp_path))
        assert dialog.windowTitle() == "交换机文件传输"
        assert dialog.windowFlags() & Qt.WindowMaximizeButtonHint
        assert dialog.protocol_combo.currentData() == "tftp"
        assert dialog.port_spin.value() == 69
        assert dialog.ftp_options.isHidden() is True
        assert "192.168.10.2" in dialog.command_preview.toPlainText()

        dialog.protocol_combo.setCurrentIndex(
            dialog.protocol_combo.findData("ftp")
        )
        app.processEvents()
        assert dialog.port_spin.value() == 21
        assert dialog.ftp_options.isHidden() is False
        assert "ftp 192.168.10.2" in dialog.command_preview.toPlainText()
    finally:
        dialog.close()


def test_file_transfer_dialog_uses_h3c_ipv6_command_syntax(
    monkeypatch,
    tmp_path,
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(
        "ui.file_transfer_dialog.discover_local_addresses",
        lambda: ["2026::1"],
    )
    dialog = FileTransferDialog()
    try:
        dialog.root_input.setText(str(tmp_path))
        dialog.bind_combo.setCurrentIndex(
            dialog.bind_combo.findData("2026::1")
        )
        app.processEvents()
        assert "tftp ipv6 2026::1" in dialog.command_preview.toPlainText()

        dialog.protocol_combo.setCurrentIndex(
            dialog.protocol_combo.findData("ftp")
        )
        app.processEvents()
        assert "ftp ipv6 2026::1" in dialog.command_preview.toPlainText()
    finally:
        dialog.close()
