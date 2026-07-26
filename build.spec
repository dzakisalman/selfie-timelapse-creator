# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_data_files

# Collect mediapipe models/data
mediapipe_datas = collect_data_files('mediapipe')

a = Analysis(
    ['src/main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('src/ui/styles/theme.qss', 'ui/styles'),
        ('src/assets/models/face_landmarker.task', 'assets/models'),
        # Add ffmpeg binary if it exists
        ('src/assets/ffmpeg/ffmpeg.exe', 'assets/ffmpeg'),
    ] + mediapipe_datas,
    hiddenimports=[
        'cv2', 
        'mediapipe', 
        'PIL', 
        'numpy'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Selfie Timelapse Creator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False, # Set to True if you want a console window (for debugging)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon=['assets/icon.ico'], # Uncomment and provide an icon path if desired
)
