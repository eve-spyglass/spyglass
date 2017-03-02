# -*- mode: python -*-
import sys

app_name = 'provii'
block_cipher = None

a = Analysis(['provii.py'],
             pathex=['c:\\projects\\provii\\src' if sys.platform == 'win32' else '/home/michael/provi-i/src'],
             binaries=None,
             datas=None,
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

a.datas += [('vi/ui/MainWindow.ui', 'vi/ui/MainWindow.ui', 'DATA'),
            ('vi/ui/SystemChat.ui', 'vi/ui/SystemChat.ui', 'DATA'),
            ('vi/ui/ChatEntry.ui', 'vi/ui/ChatEntry.ui', 'DATA'),
            ('vi/ui/Info.ui', 'vi/ui/Info.ui', 'DATA'),
            ('vi/ui/ChatroomsChooser.ui', 'vi/ui/ChatroomsChooser.ui', 'DATA'),
            ('vi/ui/RegionChooser.ui', 'vi/ui/RegionChooser.ui', 'DATA'),
            ('vi/ui/SoundSetup.ui', 'vi/ui/SoundSetup.ui', 'DATA'),
            ('vi/ui/JumpbridgeChooser.ui', 'vi/ui/JumpbridgeChooser.ui', 'DATA'),
            ('vi/ui/res/qmark.png', 'vi/ui/res/qmark.png', 'DATA'),
            ('vi/ui/res/logo.png', 'vi/ui/res/logo.png', 'DATA'),
            ('vi/ui/res/logo_small.png', 'vi/ui/res/logo_small.png', 'DATA'),
            ('vi/ui/res/logo_small_green.png', 'vi/ui/res/logo_small_green.png', 'DATA'),
            ('vi/ui/res/178028__zimbot__bosun-whistle-sttos-recreated.wav', 'vi/ui/res/178028__zimbot__bosun-whistle-sttos-recreated.wav', 'DATA'),
            ('vi/ui/res/178031__zimbot__transporterstartbeep0-sttos-recreated.wav', 'vi/ui/res/178031__zimbot__transporterstartbeep0-sttos-recreated.wav', 'DATA'),
            ('vi/ui/res/178032__zimbot__redalert-klaxon-sttos-recreated.wav', 'vi/ui/res/178032__zimbot__redalert-klaxon-sttos-recreated.wav', 'DATA'),
            ('vi/ui/res/mapdata/Providencecatch.svg', 'vi/ui/res/mapdata/Providencecatch.svg', 'DATA'),
            ('vi/ui/res/styles/dark.css', 'vi/ui/res/styles/dark.css', 'DATA'),
            ('vi/ui/res/styles/dark.yaml', 'vi/ui/res/styles/dark.yaml', 'DATA'),
            ('vi/ui/res/styles/default.css', 'vi/ui/res/styles/default.css', 'DATA'),
            ('vi/ui/res/styles/default.yaml', 'vi/ui/res/styles/default.yaml', 'DATA'),
            ('docs/jumpbridgeformat.txt', 'docs/jumpbridgeformat.txt', 'DATA'),
            ]

exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name=os.path.join('dist', app_name + ('.exe' if sys.platform == 'win32' else '')),
          debug=False,
          strip=False,
          icon='icon.ico',
          console=False,
          cipher=block_cipher)

# Build a .app if on OS X
if sys.platform == 'darwin':
   app = BUNDLE(exe,
                name=app_name + '.app',
                icon='icon.ico')
