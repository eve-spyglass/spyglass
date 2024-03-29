# -*- mode: python -*-
import sys

app_name = 'spyglass'
block_cipher = None

a = Analysis(['src/spyglass.py'],
             binaries=None,
             datas=None,
             hiddenimports=['pyttsx3.drivers', 'pyttsx3.drivers.sapi5'],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

a.datas += [('vi/ui/MainWindow.ui', 'src/vi/ui/MainWindow.ui', 'DATA'),
            ('vi/ui/SystemChat.ui', 'src/vi/ui/SystemChat.ui', 'DATA'),
            ('vi/ui/ChatEntry.ui', 'src/vi/ui/ChatEntry.ui', 'DATA'),
            ('vi/ui/Info.ui', 'src/vi/ui/Info.ui', 'DATA'),
            ('vi/ui/ChatroomsChooser.ui', 'src/vi/ui/ChatroomsChooser.ui', 'DATA'),
            ('vi/ui/RegionChooser.ui', 'src/vi/ui/RegionChooser.ui', 'DATA'),
            ('vi/ui/SoundSetup.ui', 'src/vi/ui/SoundSetup.ui', 'DATA'),
            ('vi/ui/JumpbridgeChooser.ui', 'src/vi/ui/JumpbridgeChooser.ui', 'DATA'),
            ('vi/ui/res/qmark.png', 'src/vi/ui/res/qmark.png', 'DATA'),
            ('vi/ui/res/logo.png', 'src/vi/ui/res/logo.png', 'DATA'),
            ('vi/ui/res/logo_splash.png', 'src/vi/ui/res/logo_splash.png', 'DATA'),
            ('vi/ui/res/logo_small.png', 'src/vi/ui/res/logo_small.png', 'DATA'),
            ('vi/ui/res/logo_small_green.png', 'src/vi/ui/res/logo_small_green.png', 'DATA'),
            ('vi/ui/res/178028__zimbot__bosun-whistle-sttos-recreated.wav', 'src/vi/ui/res/178028__zimbot__bosun-whistle-sttos-recreated.wav', 'DATA'),
            ('vi/ui/res/178031__zimbot__transporterstartbeep0-sttos-recreated.wav', 'src/vi/ui/res/178031__zimbot__transporterstartbeep0-sttos-recreated.wav', 'DATA'),
            ('vi/ui/res/178032__zimbot__redalert-klaxon-sttos-recreated.wav', 'src/vi/ui/res/178032__zimbot__redalert-klaxon-sttos-recreated.wav', 'DATA'),
            ('vi/ui/res/mapdata/Providencecatch.svg', 'src/vi/ui/res/mapdata/Providencecatch.svg', 'DATA'),
            ('vi/ui/res/styles/abyss.css', 'src/vi/ui/res/styles/abyss.css', 'DATA'),
            ('vi/ui/res/styles/abyss.yaml', 'src/vi/ui/res/styles/abyss.yaml', 'DATA'),
            ('vi/ui/res/styles/light.css', 'src/vi/ui/res/styles/light.css', 'DATA'),
            ('vi/ui/res/styles/light.yaml', 'src/vi/ui/res/styles/light.yaml', 'DATA'),
            ('docs/jumpbridgeformat.txt', 'src/docs/jumpbridgeformat.txt', 'DATA'),
            ('./avbin64.dll', 'src/lib/avbin64.dll', 'DATA'),
            ]

exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name=os.path.join('dist', app_name + ('.exe' if sys.platform == 'win32' else '')),
          debug=True,
          strip=False,
          icon='src/icon.ico',
          console=True,
          cipher=block_cipher)

# Build a .app if on OS X
if sys.platform == 'darwin':
   app = BUNDLE(exe,
                name=app_name + '.app',
                icon='icon.ico')
