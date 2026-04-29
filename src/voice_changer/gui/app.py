import sys

from PySide6.QtWidgets import QApplication

from .main_window import MainWindow

_STYLESHEET = """
QWidget {
    background-color: #1A1B2E;
    color: #E8E8F0;
    font-size: 13px;
}
QMainWindow { background-color: #1A1B2E; }
QGroupBox {
    border: 1px solid #3D3E5C;
    border-radius: 8px;
    margin-top: 8px;
    padding-top: 20px;
    padding-left: 8px;
    padding-right: 8px;
    padding-bottom: 8px;
    font-weight: bold;
    color: #9090A0;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 4px;
}
QComboBox {
    background-color: #252636;
    border: 1px solid #3D3E5C;
    border-radius: 4px;
    padding: 4px 8px;
    min-height: 28px;
    color: #E8E8F0;
}
QComboBox::drop-down { border: none; width: 20px; }
QComboBox QAbstractItemView {
    background-color: #252636;
    border: 1px solid #3D3E5C;
    selection-background-color: #3D3E5C;
    color: #E8E8F0;
}
QPushButton#start-btn {
    background-color: #4CAF50;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 6px 24px;
    font-weight: bold;
    min-width: 64px;
}
QPushButton#start-btn:hover { background-color: #66BB6A; }
QPushButton#start-btn:disabled { background-color: #2E4D30; color: #5A8A5C; }
QPushButton#stop-btn {
    background-color: #EF5350;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 6px 24px;
    font-weight: bold;
    min-width: 64px;
}
QPushButton#stop-btn:hover { background-color: #E53935; }
QPushButton#stop-btn:disabled { background-color: #4D2A28; color: #8A4A47; }
QPushButton#preset-btn {
    background-color: #252636;
    border: 1px solid #3D3E5C;
    border-radius: 6px;
    color: #9090A0;
    font-weight: bold;
    padding: 8px;
}
QPushButton#preset-btn:hover { border-color: #4FC3F7; color: #E8E8F0; }
QPushButton#preset-btn:checked {
    background-color: #1A3A5C;
    border-color: #4FC3F7;
    color: #4FC3F7;
}
QPushButton#waveform-btn {
    background-color: #252636;
    border: 1px solid #3D3E5C;
    border-radius: 4px;
    color: #9090A0;
    padding: 4px 12px;
}
QPushButton#waveform-btn:hover { border-color: #4FC3F7; color: #E8E8F0; }
QPushButton#waveform-btn:disabled { color: #3D3E5C; border-color: #2A2A3E; }
QSlider::groove:horizontal {
    height: 4px;
    background: #3D3E5C;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    width: 16px;
    height: 16px;
    margin: -6px 0;
    background: #4FC3F7;
    border-radius: 8px;
}
QSlider::sub-page:horizontal {
    background: #4FC3F7;
    border-radius: 2px;
}
QSlider:disabled::handle:horizontal { background: #3D3E5C; }
QSlider:disabled::sub-page:horizontal { background: #3D3E5C; }
QLabel[class="effect-name"] {
    font-size: 14px;
    font-weight: bold;
    color: #E8E8F0;
}
QLabel[class="param-label"] { color: #9090A0; font-size: 12px; }
QLabel[class="param-value"] { color: #4FC3F7; font-size: 12px; }
QFrame#separator { color: #3D3E5C; max-height: 1px; }
QLineEdit {
    background-color: #252636;
    border: 1px solid #3D3E5C;
    border-radius: 4px;
    padding: 4px 8px;
    min-height: 28px;
    color: #E8E8F0;
}
QLineEdit:focus { border-color: #4FC3F7; }
QPushButton#preset-action-btn {
    background-color: #252636;
    border: 1px solid #3D3E5C;
    border-radius: 4px;
    color: #9090A0;
    padding: 4px 12px;
    min-height: 28px;
}
QPushButton#preset-action-btn:hover { border-color: #4FC3F7; color: #E8E8F0; }
QPushButton#preset-action-btn:disabled { color: #3D3E5C; border-color: #2A2A3E; }
QPushButton#preset-delete-btn {
    background-color: #252636;
    border: 1px solid #3D3E5C;
    border-radius: 4px;
    color: #9090A0;
    padding: 4px 12px;
    min-height: 28px;
}
QPushButton#preset-delete-btn:hover { border-color: #EF5350; color: #EF5350; }
QPushButton#preset-delete-btn:disabled { color: #3D3E5C; border-color: #2A2A3E; }
"""


def run_gui() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("Voice Changer")
    app.setStyleSheet(_STYLESHEET)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())
