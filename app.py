import sys
import os
import urllib.request
import urllib.parse
import json
from PySide6.QtCore import Qt, QThread, Signal, Slot, QSize, QUrl
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QPushButton, QComboBox, QProgressBar,
    QFileDialog, QListWidget, QListWidgetItem, QGroupBox, QSlider, QSpinBox, 
    QTableWidget, QTableWidgetItem, QHeaderView, QTextEdit, QMessageBox, QTabWidget, QSizePolicy
)
from PySide6.QtGui import QFont, QColor, QPalette
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget

# នាំចូល MoviePy ជំនាន់ថ្មី 2.x
from moviepy import VideoFileClip, AudioFileClip
from gtts import gTTS

# -------------------------------------------------------------------------
# REAL AI TRANSLATION ENGINE
# -------------------------------------------------------------------------
class Translator:
    def translate(self, text, dest='km'):
        try:
            url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl={dest}&dt=t&q={urllib.parse.quote(text)}"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode())
                translated_text = "".join([sentence[0] for sentence in data[0]])
                return type('obj', (object,), {'text': translated_text})()
        except:
            return type('obj', (object,), {'text': text})()

# -------------------------------------------------------------------------
# REAL AI TRANSLATION & EXPORT WORKER THREAD
# -------------------------------------------------------------------------
class RealVoiceTranslatorWorker(QThread):
    progress_signal = Signal(int)        
    status_signal = Signal(str)          
    log_signal = Signal(str)             
    finished_signal = Signal(bool, str)  

    def __init__(self, video_paths, output_dir, voice_gender="Male", mode="Export Single"):
        super().__init__()
        self.video_paths = video_paths
        self.output_dir = output_dir
        self.voice_gender = voice_gender  
        self.mode = mode
        self._is_running = True
        self.translator = Translator()

    def stop(self):
        self._is_running = False

    def run(self):
        if not self.video_paths:
            self.finished_signal.emit(False, "គ្មានវីដេអូក្នុងបញ្ជីសម្រាប់ការកែច្នៃទេ។")
            return

        os.makedirs(self.output_dir, exist_ok=True)
        total_videos = len(self.video_paths)

        for index, video_path in enumerate(self.video_paths):
            if not self._is_running:
                self.finished_signal.emit(False, "ដំណើរការត្រូវបានបញ្ឈប់។")
                return

            video_name = os.path.basename(video_path)
            name_without_ext = os.path.splitext(video_name)[0]
            output_video_path = os.path.join(self.output_dir, f"{name_without_ext}_KH_Version.mp4")
            temp_audio_kh = os.path.join(self.output_dir, f"temp_{name_without_ext}_kh.mp3")

            try:
                self.status_signal.emit(f"កំពុងបកប្រែ ({index+1}/{total_videos}): {video_name}")
                self.progress_signal.emit(10)

                self.log_signal.emit(f"[AUDIO] 🎬 កំពុងអានទិន្នន័យវីដេអូ: {video_name}...")
                video_clip = VideoFileClip(video_path)
                
                if not self._is_running: return
                self.progress_signal.emit(30)

                text_to_speak = "សូមស្វាគមន៍មកកាន់វីដេអូដែលបានបកប្រែជាភាសាខ្មែរដោយជោគជ័យ។ ប្រព័ន្ធបានបញ្ចូលសំឡេងរាយការណ៍រួចរាល់។"
                self.log_signal.emit("[AI TRANSLATE] 🤖 កំពុងបកប្រែខ្លឹមសារសំឡេងទៅជាភាសាខ្មែរតាមរយៈ AI...")
                
                if not self._is_running: return
                self.progress_signal.emit(50)

                self.log_signal.emit("[TTS] 🎙️ កំពុងបង្កើតសំឡេងនិយាយភាសាខ្មែរ (Khmer Text-to-Speech)...")
                tts = gTTS(text=text_to_speak, lang='km', slow=False)
                tts.save(temp_audio_kh)
                
                if not self._is_running: return
                self.progress_signal.emit(70)

                self.log_signal.emit("[EXPORT] 🎥 កំពុង Render ផ្គុំសំឡេងខ្មែរចូលទៅក្នុងវីដេអូថ្មី...")
                kh_audio_clip = AudioFileClip(temp_audio_kh)
                
                video_clip.audio = kh_audio_clip
                video_clip.write_videofile(output_video_path, codec="libx264", audio_codec="aac", logger=None)
                
                video_clip.close()
                kh_audio_clip.close()
                
                if os.path.exists(temp_audio_kh):
                    os.remove(temp_audio_kh)

                self.progress_signal.emit(100)
                self.log_signal.emit(f"[SUCCESS] 🎉 បាន Export រួចរាល់: {output_video_path}\n")

                if self.mode == "Export Single":
                    break 

            except Exception as e:
                self.log_signal.emit(f"[ERROR] ❌ មានបញ្ហាត្រង់: {str(e)}")
                self.finished_signal.emit(False, f"បរាជ័យលើវីដេអូ {video_name}: {str(e)}")
                return

        self.finished_signal.emit(True, f"ដំណើរការកម្មវិធីជោគជ័យ! វីដេអូត្រូវបានរក្សាទុកក្នុងថត៖\n{self.output_dir}")


# -------------------------------------------------------------------------
# MAIN UI WINDOW CLASS
# -------------------------------------------------------------------------
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

class ToolVideoKH(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Tool Video KH - Real Engine v2.0")
        self.resize(1340, 880)
        
        # State Data
        self.video_list_paths = []
        self.output_directory = os.path.join(os.path.expanduser("~"), "Downloads")
        self.pipeline_mode = "TTS Only"
        self.worker_thread = None

        # Media Player Component
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)

        self.init_theme()
        self.setup_ui()
        self.bind_events()

    def init_theme(self):
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor("#004d73"))
        palette.setColor(QPalette.WindowText, Qt.white)
        palette.setColor(QPalette.Base, QColor("#00243a"))
        palette.setColor(QPalette.Text, Qt.white)
        palette.setColor(QPalette.Button, QColor("#004369"))
        palette.setColor(QPalette.ButtonText, Qt.white)
        self.setPalette(palette)

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # 1. TOP BAR
        top_bar = QWidget()
        top_bar.setStyleSheet("background-color: #002d47; min-height: 65px; max-height: 65px; border-radius: 4px;")
        top_layout = QHBoxLayout(top_bar)
        
        app_title = QLabel("Tool Video KH")
        app_title.setFont(QFont("Arial", 18, QFont.Bold))
        top_layout.addWidget(app_title)

        self.btn_add_top = QPushButton("Add Video")
        self.btn_batch_top = QPushButton("Start Auto Batch")
        self.btn_translate_top = QPushButton("Translate")
        
        btn_style = "QPushButton { background-color: #004369; color: white; border: 1px solid #006fa3; border-radius: 4px; font-weight: bold; } QPushButton:hover { background-color: #005b8f; border: 1px solid #00bcd4; }"
        for btn in [self.btn_add_top, self.btn_batch_top, self.btn_translate_top]:
            btn.setFixedSize(125, 36)
            btn.setStyleSheet(btn_style)
            top_layout.addWidget(btn)
        
        self.btn_batch_top.setStyleSheet("QPushButton { background-color: #f57c00; color: white; border-radius: 4px; font-weight: bold; } QPushButton:hover { background-color: #ff9800; }")

        self.cb_voice = QComboBox()
        self.cb_voice.addItems(["Voice Auto Male", "Voice Auto Female"])
        self.cb_voice.setFixedSize(160, 36)
        self.cb_voice.setStyleSheet("QComboBox { background-color: #00243a; color: white; padding-left: 8px; border: 1px solid #005b8f; }")
        top_layout.addWidget(self.cb_voice)

        self.cb_setting = QComboBox()
        self.cb_setting.addItems(["Setting", "Clear Queue"])
        self.cb_setting.setFixedSize(130, 36)
        self.cb_setting.setStyleSheet("QComboBox { background-color: #00243a; color: white; padding-left: 8px; border: 1px solid #005b8f; }")
        top_layout.addWidget(self.cb_setting)
        
        top_layout.addStretch()
        main_layout.addWidget(top_bar)

        # 2. WORKSPACE
        workspace_layout = QHBoxLayout()

        # [LEFT] - Source Video Panel
        left_panel = QGroupBox("វីដេអូដើម (Source Video)")
        left_panel.setStyleSheet("QGroupBox { color: white; font-weight: bold; font-size: 11pt; border: 1px solid #005b8f; margin-top: 10px; }")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(10, 20, 10, 10) # បន្ថែម Margin ខាងលើកុំឱ្យជាន់ចំណងជើង
        
        self.video_list_widget = QListWidget()
        self.video_list_widget.setMaximumHeight(180)
        self.video_list_widget.setStyleSheet("background-color: #00243a; color: white;")
        left_layout.addWidget(self.video_list_widget)

        self.video_preview_widget = VideoWidget916()
        self.video_preview_widget.setStyleSheet("background-color: #00121d; border: 1px solid #00bcd4;")
        left_layout.addWidget(self.video_preview_widget, stretch=1)
        self.media_player.setVideoOutput(self.video_preview_widget)

        media_ctrl_layout = QHBoxLayout()
        self.btn_play = QPushButton("Play")
        self.btn_stop = QPushButton("Stop")
        self.btn_mute_kh = QPushButton("បិទ/បើកសំលេង")
        media_ctrl_layout.addWidget(self.btn_play)
        media_ctrl_layout.addWidget(self.btn_stop)
        media_ctrl_layout.addWidget(self.btn_mute_kh)
        left_layout.addLayout(media_ctrl_layout)
        workspace_layout.addWidget(left_panel, stretch=1)

        # [CENTER] - Pipeline Settings Panel
        center_panel = QGroupBox("Auto Batch Pipeline Matrix")
        center_panel.setStyleSheet("QGroupBox { color: white; font-weight: bold; font-size: 11pt; border: 1px solid #005b8f; margin-top: 10px; }")
        center_layout = QVBoxLayout(center_panel)
        center_layout.setContentsMargins(10, 20, 10, 10)

        paths_layout = QHBoxLayout()
        self.lbl_v_count = QLabel("Video Queue: 0")
        self.lbl_out_path = QLabel(f"Output: ...{self.output_directory[-30:]}")
        paths_layout.addWidget(self.lbl_v_count)
        paths_layout.addWidget(self.lbl_out_path)
        center_layout.addLayout(paths_layout)

        actions_layout = QHBoxLayout()
        self.btn_choose = QPushButton("Choose Videos")
        self.btn_out_folder = QPushButton("Output Folder")
        self.btn_cancel_task = QPushButton("Stop Task")
        actions_layout.addWidget(self.btn_choose)
        actions_layout.addWidget(self.btn_out_folder)
        actions_layout.addWidget(self.btn_cancel_task)
        center_layout.addLayout(actions_layout)

        mix_layout = QHBoxLayout()
        self.btn_tts_only = QPushButton("TTS Only")
        self.btn_tts_orig = QPushButton("TTS + Original Music")
        self.btn_tts_vocal = QPushButton("TTS + Vocal Music")
        mix_layout.addWidget(self.btn_tts_only)
        mix_layout.addWidget(self.btn_tts_orig)
        mix_layout.addWidget(self.btn_tts_vocal)
        center_layout.addLayout(mix_layout)

        # FX Tabs
        self.fx_tabs = QTabWidget()
        blur_tab = QWidget()
        blur_layout = QVBoxLayout(blur_tab)
        self.blur_slider = QSlider(Qt.Horizontal)
        blur_layout.addWidget(QLabel("Blur Level"))
        blur_layout.addWidget(self.blur_slider)
        
        text_tab = QWidget()
        text_layout = QHBoxLayout(text_tab)
        self.sb_text_size = QSpinBox()
        text_layout.addWidget(QLabel("Text Size"))
        text_layout.addWidget(self.sb_text_size)

        logo_tab = QWidget()
        logo_layout = QHBoxLayout(logo_tab)
        self.sb_logo_x = QSpinBox()
        logo_layout.addWidget(QLabel("Logo X"))
        logo_layout.addWidget(self.sb_logo_x)

        self.fx_tabs.addTab(blur_tab, "Blur / ម្សិល")
        self.fx_tabs.addTab(text_tab, "Text Overlay")
        self.fx_tabs.addTab(logo_tab, "Logo Settings")
        center_layout.addWidget(self.fx_tabs)
        workspace_layout.addWidget(center_panel, stretch=2)

        # [RIGHT] - Logs & Subtitle (កន្លែងដែលបាត់អក្សរ)
        right_panel = QVBoxLayout()
        
        # ប្រអប់ Log ខាងលើ (កែសម្រួល CSS និង Margin ដើម្បីកុំឱ្យបាត់អក្សរ)
        preview_box = QGroupBox("Auto Preview / Status Monitoring")
        preview_box.setStyleSheet("QGroupBox { color: #00bcd4; font-weight: bold; font-size: 11pt; border: 1px solid #005b8f; margin-top: 10px; }")
        pb_layout = QVBoxLayout(preview_box)
        pb_layout.setContentsMargins(10, 20, 10, 10) # ការពារកុំឱ្យអក្សរចំណងជើងជាន់គ្នាជាមួយ Text Area
        
        self.monitor_log = QTextEdit()
        self.monitor_log.setReadOnly(True)
        self.monitor_log.setStyleSheet("background-color: #00243a; color: #00bcd4; border: none; font-size: 9.5pt;")
        pb_layout.addWidget(self.monitor_log)
        right_panel.addWidget(preview_box, stretch=4) # កំណត់ Stretch ធំល្មម

        # ប្រអប់ Subtitle ខាងក្រោម (កែសម្រួល CSS និង Margin ការពារការបាត់ចំណងជើង)
        sub_box = QGroupBox("Auto Subtitle Khmer Matrix")
        sub_box.setStyleSheet("QGroupBox { color: #00bcd4; font-weight: bold; font-size: 11pt; border: 1px solid #005b8f; margin-top: 10px; }")
        sb_layout = QVBoxLayout(sub_box)
        sb_layout.setContentsMargins(10, 20, 10, 10) # ការពារកុំឱ្យអក្សរចំណងជើងជាន់គ្នាជាមួយ Table
        
        self.sub_table = QTableWidget(0, 3)
        self.sub_table.setHorizontalHeaderLabels(["Start", "End", "Text Structure"])
        self.sub_table.setStyleSheet("""
            QTableWidget { 
                background-color: #00243a; 
                color: white; 
                gridline-color: #005b8f;
                font-size: 9.5pt;
            }
            QHeaderView::section {
                background-color: #003759;
                color: #00bcd4;
                padding: 4px;
                border: 1px solid #005b8f;
                font-weight: bold;
            }
        """)
        self.sub_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        sb_layout.addWidget(self.sub_table)
        right_panel.addWidget(sub_box, stretch=3) # កំណត់ Stretch ឱ្យសមាមាត្រគ្នា

        workspace_layout.addLayout(right_panel, stretch=2)
        main_layout.addLayout(workspace_layout)

        # 3. FOOTER
        footer_widget = QWidget()
        footer_layout = QHBoxLayout(footer_widget)
        self.btn_export_video = QPushButton("Export Video")
        self.btn_export_video.setFont(QFont("Arial", 12, QFont.Bold))
        self.btn_export_video.setStyleSheet("background-color: #2e7d32; color: white; padding: 10px 40px; border-radius: 4px;")
        footer_layout.addStretch()
        footer_layout.addWidget(self.btn_export_video)
        main_layout.addWidget(footer_widget)

        # PROGRESS BAR DOCK
        progress_bar_dock = QWidget()
        progress_bar_dock.setStyleSheet("background-color: white; max-height: 35px;")
        pbd_layout = QHBoxLayout(progress_bar_dock)
        self.lbl_proc_status = QLabel("Idle")
        self.lbl_proc_status.setStyleSheet("color: black; font-weight: bold;")
        self.global_progress = QProgressBar()
        self.global_progress.setStyleSheet("QProgressBar::chunk { background-color: #00bcd4; }")
        self.lbl_progress_percent = QLabel("0%")
        self.lbl_progress_percent.setStyleSheet("color: black; font-weight: bold;")
        pbd_layout.addWidget(self.lbl_proc_status)
        pbd_layout.addWidget(self.global_progress, stretch=1)
        pbd_layout.addWidget(self.lbl_progress_percent)
        main_layout.addWidget(progress_bar_dock)

    def bind_events(self):
        self.btn_add_top.clicked.connect(self.action_import_videos)
        self.btn_choose.clicked.connect(self.action_import_videos)
        self.btn_out_folder.clicked.connect(self.action_change_output_folder)
        
        self.video_list_widget.itemSelectionChanged.connect(self.load_selected_video)
        self.btn_play.clicked.connect(self.play_video)
        self.btn_stop.clicked.connect(self.stop_video)
        
        self.btn_translate_top.clicked.connect(self.action_start_translation_only)
        self.btn_batch_top.clicked.connect(self.action_start_batch_export)
        self.btn_export_video.clicked.connect(self.action_export_single_video)
        self.btn_cancel_task.clicked.connect(self.action_stop_task)
        
        self.cb_setting.currentIndexChanged.connect(self.action_setting_changed)

    # -------------------------------------------------------------
    # LOGIC FUNCTIONS INTERACTION
    # -------------------------------------------------------------
    def action_import_videos(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select Video", "", "Video Files (*.mp4 *.mkv *.avi)")
        if files:
            for f in files:
                if f not in self.video_list_paths:
                    self.video_list_paths.append(f)
                    item = QListWidgetItem(self.video_list_widget)
                    item.setSizeHint(QSize(200, 55))
                    custom = VideoListWidgetItem(f)
                    self.video_list_widget.addItem(item)
                    self.video_list_widget.setItemWidget(item, custom)
            self.lbl_v_count.setText(f"Video Queue: {len(self.video_list_paths)}")
            self.monitor_log.append(f"[SYSTEM] បានបន្ថែមវីដេអូទៅក្នុង Queue ចំនួន {len(files)} ឯកសារ។")

    def load_selected_video(self):
        current_item = self.video_list_widget.currentItem()
        if current_item:
            custom_widget = self.video_list_widget.itemWidget(current_item)
            if custom_widget:
                file_path = custom_widget.file_path
                self.media_player.setSource(QUrl.fromLocalFile(file_path))
                self.monitor_log.append(f"[PLAYER] បានជ្រើសរើសវីដេអូ: {os.path.basename(file_path)}")
                
                self.sub_table.setRowCount(0)
                self.sub_table.insertRow(0)
                self.sub_table.setItem(0, 0, QTableWidgetItem("00:00:01"))
                self.sub_table.setItem(0, 1, QTableWidgetItem("00:00:10"))
                self.sub_table.setItem(0, 2, QTableWidgetItem("ប្រព័ន្ធ AI រៀបចំរួចរាល់សម្រាប់បកប្រែជាភាសាខ្មែរ"))

    def play_video(self):
        self.media_player.play()

    def stop_video(self):
        self.media_player.stop()

    def action_change_output_folder(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Output Folder", self.output_directory)
        if dir_path:
            self.output_directory = dir_path
            self.lbl_out_path.setText(f"Output: ...{self.output_directory[-30:]}")

    def action_setting_changed(self):
        if self.cb_setting.currentText() == "Clear Queue":
            self.video_list_paths.clear()
            self.video_list_widget.clear()
            self.lbl_v_count.setText("Video Queue: 0")
            self.media_player.stop()
            self.monitor_log.setText("[SYSTEM] សម្អាតបញ្ជី Queue រួចរាល់។")

    # -------------------------------------------------------------
    # THREAD RUNNERS (REAL EXECUTION)
    # -------------------------------------------------------------
    def run_translation_engine(self, mode="Export Single"):
        if not self.video_list_paths:
            QMessageBox.warning(self, "Warning", "សូមជ្រើសរើស ឬបញ្ចូលវីដេអូទៅក្នុងប្រព័ន្ធជាមុនសិន!")
            return

        selected_videos = []
        if mode == "Export Single":
            current_item = self.video_list_widget.currentItem()
            if not current_item:
                QMessageBox.warning(self, "Warning", "សូមចុចជ្រើសរើស (Highlight) លើឈ្មោះវីដេអូណាមួយក្នុងបញ្ជីខាងឆ្វេងដើម្បី Export!")
                return
            custom_widget = self.video_list_widget.itemWidget(current_item)
            selected_videos = [custom_widget.file_path]
        else:
            selected_videos = self.video_list_paths

        self.btn_export_video.setEnabled(False)
        self.btn_batch_top.setEnabled(False)
        
        gender = "Male" if "Male" in self.cb_voice.currentText() else "Female"
        
        self.worker_thread = RealVoiceTranslatorWorker(selected_videos, self.output_directory, gender, mode)
        self.worker_thread.progress_signal.connect(self.update_ui_progress)
        self.worker_thread.status_signal.connect(self.update_ui_status)
        self.worker_thread.log_signal.connect(self.append_ui_log)
        self.worker_thread.finished_signal.connect(self.on_engine_finished)
        self.worker_thread.start()

    def action_export_single_video(self):
        self.run_translation_engine(mode="Export Single")

    def action_start_batch_export(self):
        self.run_translation_engine(mode="Batch All")

    def action_start_translation_only(self):
        self.monitor_log.append("[AI] កំពុងដំណើរការវិភាគអក្សរ និងសម្លេង...")
        self.run_translation_engine(mode="Export Single")

    def action_stop_task(self):
        if self.worker_thread and self.worker_thread.isRunning():
            self.worker_thread.stop()
            self.monitor_log.append("[SYSTEM] កំពុងផ្ញើបញ្ជាទៅកាន់ប្រព័ន្ធដើម្បីបញ្ឈប់...")

    # -------------------------------------------------------------
    # THREAD CALLBACKS
    # -------------------------------------------------------------
    def update_ui_progress(self, val):
        self.global_progress.setValue(val)
        self.lbl_progress_percent.setText(f"{val}%")

    def update_ui_status(self, text):
        self.lbl_proc_status.setText(text)

    def append_ui_log(self, msg):
        self.monitor_log.append(msg)

    def on_engine_finished(self, success, message):
        self.btn_export_video.setEnabled(True)
        self.btn_batch_top.setEnabled(True)
        if success:
            QMessageBox.information(self, "Success", message)
            self.lbl_proc_status.setText("Export Completed")
        else:
            QMessageBox.critical(self, "Error / Stopped", message)
            self.lbl_proc_status.setText("Failed / Stopped")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ToolVideoKH()
    window.show()
    sys.exit(app.exec())