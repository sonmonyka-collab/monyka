from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QSizePolicy
from PySide6.QtGui import QFont
from PySide6.QtMultimediaWidgets import QVideoWidget
import os

class VideoWidget916(QVideoWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    def hasHeightForWidth(self): return True
    def heightForWidth(self, width): return int(width * 16 / 9)
    def sizeHint(self): return QSize(240, int(240 * 16 / 9))

class VideoListWidgetItem(QWidget):
    def __init__(self, file_path, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)

        self.lbl_thumbnail = QLabel("🎬")
        self.lbl_thumbnail.setFixedSize(65, 40)
        self.lbl_thumbnail.setStyleSheet("background-color: #001a2b; border: 1px solid #00bcd4; border-radius: 3px;")
        self.lbl_thumbnail.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.lbl_thumbnail)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        
        file_name = os.path.basename(file_path)
        self.lbl_name = QLabel(file_name)
        self.lbl_name.setFont(QFont("Arial", 9, QFont.Bold))
        self.lbl_name.setStyleSheet("color: white;")
        
        try:
            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
            info_text = f"{file_size_mb:.1f} MB | MP4"
        except:
            info_text = "Unknown Size"
            
        self.lbl_info = QLabel(info_text)
        self.lbl_info.setFont(QFont("Arial", 8))
        self.lbl_info.setStyleSheet("color: #8ab4f8;")
        
        text_layout.addWidget(self.lbl_name)
        text_layout.addWidget(self.lbl_info)
        layout.addLayout(text_layout)
        layout.addStretch()
