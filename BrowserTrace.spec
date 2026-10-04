# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the BrowserTrace standalone Windows executable."""

from PyInstaller.utils.win32 import versioninfo

VERSION = versioninfo.VSVersionInfo(
    ffi=versioninfo.FixedFileInfo(
        filevers=(1, 0, 0, 0),
        prodvers=(1, 0, 0, 0),
        mask=0x3F,
        flags=0x0,
        OS=0x40004,
        fileType=0x1,
        subtype=0x0,
        date=(0, 0),
    ),
    kids=[
        versioninfo.StringFileInfo(
            [
                versioninfo.StringTable(
                    "040904B0",
                    [
                        versioninfo.StringStruct("CompanyName", "BrowserTrace"),
                        versioninfo.StringStruct("FileDescription", "BrowserTrace - Privacy-First Browser Artifact Analysis"),
                        versioninfo.StringStruct("FileVersion", "1.0.0.0"),
                        versioninfo.StringStruct("InternalName", "BrowserTrace"),
                        versioninfo.StringStruct("OriginalFilename", "BrowserTrace.exe"),
                        versioninfo.StringStruct("ProductName", "BrowserTrace"),
                        versioninfo.StringStruct("ProductVersion", "1.0.0.0"),
                    ],
                )
            ]
        ),
        versioninfo.VarFileInfo([versioninfo.VarStruct("Translation", [1033, 1200])]),
    ],
)

a = Analysis(
    ["run.py"],
    pathex=[],
    binaries=[],
    datas=[
        ("browsertrace/resources", "browsertrace/resources"),
    ],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtQuick", "PySide6.QtQml"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="BrowserTrace",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="browsertrace/resources/icon.ico",
    version=VERSION,
)