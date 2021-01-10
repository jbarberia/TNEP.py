# -*- mode: python ; coding: utf-8 -*-
# In terminal run: pyinstaller -y tnep.spec
import sys
import os

block_cipher = None

def get_pulp_path():
    import pulp
    return pulp.__path__[0]

path_main = os.path.dirname(os.path.abspath(sys.argv[2]))


a = Analysis(['tnep\\main.py'],
             pathex=['C:\\Users\\Barberia Juan Luis\\Desktop\\Software\\TNEP.py'],
             binaries=[],
             datas=[],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

a.datas += Tree(get_pulp_path(), prefix='pulp', excludes=["*.pyc"])

pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)

exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='tnep',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=False )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='main')
