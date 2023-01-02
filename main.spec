# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
import builtins
import logging
import shutil
import yaml

block_cipher = None
env_path = Path('.env')
for line in env_path.read_text(encoding='utf8').split('\n'):
    if '=' not in line:
        continue
    line = line.split('=')
    key = line[0].strip()
    value = '='.join(line[1:]).strip()
    setattr(builtins, key, value)


a = Analysis(['main.py'],
             pathex=[Path(SPECPATH).absolute()],
             binaries=[],
             datas=[
                 ('.env', '.'),
             ],
             hiddenimports=[
                 'pkg_resources.py2_warn'
             ],
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
          [],
          exclude_binaries=True,
          name='main',
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
               name=builtins.APP_NAME)


with open('pure.yaml', 'r', encoding='utf-8') as f:
    logging.info('=== 读取设定档 ====')
    setting = yaml.load(f, yaml.SafeLoader)
with open(f'dist/{builtins.APP_NAME}/config.yaml', 'w', encoding='utf-8') as f:
    logging.info('=== 保存设定档 ====')
    yaml.dump({k:v for k,v in setting.items() if k in ['CHUNK_SIZE', 'CONFIG_URL', 'CURRENT']}, f, allow_unicode=True)

