import sys
from cx_Freeze import setup, Executable
from pathlib import Path

# GUI uygulamaları Windows'ta farklı bir "base" gerektirir.
# Bu, konsol penceresinin açılmasını engeller.
base = None
if sys.platform == "win32":
    base = "Win32GUI"

# .exe'ye dahil edilmesi gereken ek dosyalar (arayüz dosyası gibi)
ui_file = Path(__file__).parent / "mainwindow.ui"

build_exe_options = {
    # Otomatik olarak bulunamayan paketleri buraya ekleyebilirsiniz.
    "packages": ["PyQt6", "pyqtgraph"],
    "excludes": [],
    "include_files": [ui_file],
}

setup(
    name="IIoT-Reciever-Tool",
    version="1.0",
    description="IIoT Receiver Tool",
    options={"build_exe": build_exe_options},
    executables=[Executable("main.py", base=base, target_name="IIoT-Reciever-Tool.exe")]
)