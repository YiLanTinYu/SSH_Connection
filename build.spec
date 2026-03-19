# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 打包配置文件
用法: pyinstaller build.spec
"""

import os
import sys

block_cipher = None

# ── 收集隐式依赖 ──────────────────────────────────────────
hiddenimports = [
    # 核心网络库
    'paramiko',
    'paramiko.transport',
    'paramiko.auth_handler',
    'paramiko.channel',
    'paramiko.client',
    'paramiko.config',
    'paramiko.dsskey',
    'paramiko.ecdsakey',
    'paramiko.ed25519key',
    'paramiko.file',
    'paramiko.hostkeys',
    'paramiko.kex_curve25519',
    'paramiko.kex_ecdh_nist',
    'paramiko.kex_gex',
    'paramiko.kex_group1',
    'paramiko.kex_group14',
    'paramiko.kex_group16',
    'paramiko.message',
    'paramiko.packet',
    'paramiko.primes',
    'paramiko.proxy',
    'paramiko.rsakey',
    'paramiko.server',
    'paramiko.sftp',
    'paramiko.sftp_attr',
    'paramiko.sftp_client',
    'paramiko.sftp_file',
    'paramiko.sftp_handle',
    'paramiko.sftp_server',
    'paramiko.sftp_si',
    'paramiko.ssh_exception',
    'paramiko.transport',
    'paramiko.util',
    'paramiko.win_pageant',
    'paramiko.win_openssh',

    # 加密库
    'cryptography',
    'cryptography.hazmat.primitives',
    'cryptography.hazmat.primitives.asymmetric',
    'cryptography.hazmat.backends',
    'cryptography.hazmat.backends.openssl',
    'cryptography.hazmat.primitives.ciphers',
    'cryptography.hazmat.primitives.hashes',
    'cryptography.hazmat.primitives.kdf',
    'cryptography.hazmat.primitives.serialization',
    'cryptography.x509',
    'bcrypt',

    # netmiko
    'netmiko',
    'netmiko.hp',
    'netmiko.huawei',
    'netmiko.cisco',
    'netmiko.cisco_base_connection',
    'netmiko.ssh_autodetect',

    # 数据处理
    'pandas',
    'pandas._libs',
    'pandas._libs.tslibs',
    'openpyxl',
    'openpyxl.styles',
    'openpyxl.utils',
    'openpyxl.workbook',
    'openpyxl.worksheet',
    'et_xmlfile',

    # PyQt5
    'PyQt5',
    'PyQt5.QtWidgets',
    'PyQt5.QtCore',
    'PyQt5.QtGui',
    'PyQt5.sip',

    # 标准库
    'socket',
    'threading',
    'queue',
    'logging',
    'logging.handlers',
    'json',
    'csv',
    'ipaddress',
    'enum',
    'typing',
    'abc',
    'io',
    're',
    'time',
    'datetime',
    'os',
    'sys',
    'pathlib',
]

# ── 数据文件 ──────────────────────────────────────────────
datas = [
    # Excel 模板（如果存在）
    ('device_template.xlsx', '.'),
]

# ── Analysis ─────────────────────────────────────────────
a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={
        # 告知 pandas hook 不要收集可选的 pyarrow 后端
        "pandas": {"backends": ["openpyxl"]},
    },
    runtime_hooks=[],
    excludes=[
        # 排除冲突的 Qt 绑定（环境中有 PySide6，必须排除）
        'PySide6',
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'PySide6.QtNetwork',
        'PySide6.QtOpenGL',
        'PySide6.QtQml',
        'PySide6.QtQuick',
        'PySide6.QtSql',
        'PySide6.QtSvg',
        'PySide6.QtTest',
        'PySide6.QtXml',
        'PySide2',
        'PySide2.QtCore',
        'PySide2.QtGui',
        'PySide2.QtWidgets',
        'PyQt4',
        # 其他不需要的大型库
        'matplotlib',
        'scipy',
        'numpy.testing',
        'PIL',
        'tkinter',
        'unittest',
        # 注意: pydoc 不能排除，pyarrow.vendored.docscrape 依赖它
        # 'pydoc',
        'doctest',
        'argparse',
        'difflib',
        'ftplib',
        'imaplib',
        'smtplib',
        'poplib',
        'webbrowser',
        'telnetlib',
        # pyarrow 是 pandas 可选依赖，项目只用 openpyxl，直接排除整个 pyarrow
        # 这样可以同时解决 pyarrow->pydoc 的依赖链问题，并大幅缩减包体积
        'pyarrow',
        'pyarrow.vendored',
        'pyarrow.vendored.docscrape',
        # Anaconda 特有的大型包
        'IPython',
        'jupyter',
        'notebook',
        'numba',
        'llvmlite',
        'sphinx',
        'black',
        'jedi',
        'parso',
        'pytest',
        'docutils',
        'babel',
        'zmq',
        'fsspec',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# ── PYZ ──────────────────────────────────────────────────
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# ── EXE ──────────────────────────────────────────────────
# 检测图标文件
_icon = 'app.ico' if os.path.exists('app.ico') else None

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='H3C_SSH_Tool',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # 不显示控制台窗口
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=_icon,
    version_file=None,
)
