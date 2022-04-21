# -*- mode: python ; coding: utf-8 -*-


block_cipher = None


a = Analysis(['spyglass.py'],
             pathex=['C:\\src', 'C:\\spyglass\\spyglass\\src'],
             binaries=[('./lib/*.dll', './lib')],
             datas=[('./vi/ui/*.ui', './vi/ui'), ('./vi/ui/res/*', './vi/ui/res'), ('./vi/ui/res/styles/*', './vi/ui/res/styles')],
             hiddenimports=['pyttsx3.drivers', 'pyttsx3.drivers.dummy', 'import=pyttsx3.drivers.espeak', 'pyttsx3.drivers.nsss', 'pyttsx3.drivers.sapi5', 'PyQt6.QtWebChannel', 'PyQt6.QtWebEngineCore', 'PyQt6.QtQml'],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='spyglass',
          debug=False,
          bootloader_ignore_signals=False,
          strip=True,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=False , icon='.\\icon.ico')