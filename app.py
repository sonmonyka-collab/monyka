import sys
import os
import signal
from PySide6.QtCore import Qt, QSize, QUrl
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QProgressBar,
    QFileDialog, QListWidget, QListWidgetItem, QGroupBox, QSlider, QSpinBox, 
    QTableWidget, QTableWidgetItem, QHeaderView, QTextEdit, QMessageBox, QTabWidget
)
from PySide6.QtGui import QFont, QColor, QPalette
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

# Import project files
from widgets import VideoWidget916, VideoListWidgetItem
from workers import ASRWorker, TranslationWorker, ExportWorker

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
        self.btn_recognize = QPushButton("Auto Recognize Voice")
        self.btn_translate_top = QPushButton("Translate")
        
        btn_style = "QPushButton { background-color: #004369; color: white; border: 1px solid #006fa3; border-radius: 4px; font-weight: bold; } QPushButton:hover { background-color: #005b8f; border: 1px solid #00bcd4; }"
        for btn in [self.btn_add_top, self.btn_recognize, self.btn_translate_top]:
            btn.setFixedSize(170 if btn == self.btn_recognize else 125, 36)
            btn.setStyleSheet(btn_style)
            top_layout.addWidget(btn)
        
        self.btn_recognize.setStyleSheet("QPushButton { background-color: #f57c00; color: white; border-radius: 4px; font-weight: bold; } QPushButton:hover { background-color: #ff9800; }")

        self.cb_source_lang = QComboBox()
        self.cb_source_lang.addItems([
            "Original: English",
            "Original: Chinese",
            "Original: Thai",
            "Original: Vietnamese",
            "Original: French",
            "Original: Spanish",
            "Original: Japanese",
            "Original: Korean"
        ])
        self.cb_source_lang.setFixedSize(160, 36)
        self.cb_source_lang.setStyleSheet("QComboBox { background-color: #00243a; color: white; padding-left: 8px; border: 1px solid #005b8f; }")
        top_layout.addWidget(self.cb_source_lang)

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
        left_layout.setContentsMargins(10, 20, 10, 10)
        
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

        # [RIGHT] - Logs & Subtitle
        right_panel = QVBoxLayout()
        
        preview_box = QGroupBox("Auto Preview / Status Monitoring")
        preview_box.setStyleSheet("QGroupBox { color: #00bcd4; font-weight: bold; font-size: 11pt; border: 1px solid #005b8f; margin-top: 10px; }")
        pb_layout = QVBoxLayout(preview_box)
        pb_layout.setContentsMargins(10, 20, 10, 10)
        
        self.monitor_log = QTextEdit()
        self.monitor_log.setReadOnly(True)
        self.monitor_log.setStyleSheet("background-color: #00243a; color: #00bcd4; border: none; font-size: 9.5pt;")
        pb_layout.addWidget(self.monitor_log)
        right_panel.addWidget(preview_box, stretch=4)

        sub_box = QGroupBox("Auto Subtitle Khmer Matrix")
        sub_box.setStyleSheet("QGroupBox { color: #00bcd4; font-weight: bold; font-size: 11pt; border: 1px solid #005b8f; margin-top: 10px; }")
        sb_layout = QVBoxLayout(sub_box)
        sb_layout.setContentsMargins(10, 20, 10, 10)
        
        self.sub_table = QTableWidget(0, 4)
        self.sub_table.setHorizontalHeaderLabels(["Start", "End", "Original Text", "Khmer Text"])
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
        right_panel.addWidget(sub_box, stretch=3)

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

        self.select_pipeline_mode("TTS Only")

    def bind_events(self):
        self.btn_add_top.clicked.connect(self.action_import_videos)
        self.btn_choose.clicked.connect(self.action_import_videos)
        self.btn_out_folder.clicked.connect(self.action_change_output_folder)
        
        self.video_list_widget.itemSelectionChanged.connect(self.load_selected_video)
        self.btn_play.clicked.connect(self.play_video)
        self.btn_stop.clicked.connect(self.stop_video)
        
        self.btn_translate_top.clicked.connect(self.action_translate_text)
        self.btn_recognize.clicked.connect(self.action_recognize_voice)
        self.btn_export_video.clicked.connect(self.action_export_single_video)
        self.btn_cancel_task.clicked.connect(self.action_stop_task)
        
        self.cb_setting.currentIndexChanged.connect(self.action_setting_changed)

        # Bind Pipeline Mix Buttons
        self.btn_tts_only.clicked.connect(lambda: self.select_pipeline_mode("TTS Only"))
        self.btn_tts_orig.clicked.connect(lambda: self.select_pipeline_mode("TTS + Original Music"))
        self.btn_tts_vocal.clicked.connect(lambda: self.select_pipeline_mode("TTS + Vocal Music"))

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
    def action_recognize_voice(self):
        current_item = self.video_list_widget.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Warning", "សូមជ្រើសរើសវីដេអូពីបញ្ជីខាងឆ្វេងជាមុនសិន!")
            return

        custom_widget = self.video_list_widget.itemWidget(current_item)
        video_path = custom_widget.file_path

        self.set_buttons_enabled(False)
        self.sub_table.setRowCount(0)

        lang_map = {
            "Original: English": "en-US",
            "Original: Chinese": "zh-CN",
            "Original: Thai": "th-TH",
            "Original: Vietnamese": "vi-VN",
            "Original: French": "fr-FR",
            "Original: Spanish": "es-ES",
            "Original: Japanese": "ja-JP",
            "Original: Korean": "ko-KR"
        }
        selected_lang_text = self.cb_source_lang.currentText()
        source_lang = lang_map.get(selected_lang_text, "en-US")

        self.worker_thread = ASRWorker(video_path, source_lang, self.output_directory)
        self.worker_thread.progress_signal.connect(self.update_ui_progress)
        self.worker_thread.status_signal.connect(self.update_ui_status)
        self.worker_thread.log_signal.connect(self.append_ui_log)
        self.worker_thread.chunk_signal.connect(self.add_asr_chunk_row)
        self.worker_thread.finished_signal.connect(self.on_asr_finished)
        self.worker_thread.start()

    def add_asr_chunk_row(self, start, end, text):
        row = self.sub_table.rowCount()
        self.sub_table.insertRow(row)
        
        item_start = QTableWidgetItem(start)
        item_start.setFlags(item_start.flags() | Qt.ItemIsEditable)
        self.sub_table.setItem(row, 0, item_start)
        
        item_end = QTableWidgetItem(end)
        item_end.setFlags(item_end.flags() | Qt.ItemIsEditable)
        self.sub_table.setItem(row, 1, item_end)
        
        item_orig = QTableWidgetItem(text)
        item_orig.setFlags(item_orig.flags() | Qt.ItemIsEditable)
        self.sub_table.setItem(row, 2, item_orig)
        
        item_khmer = QTableWidgetItem("")
        item_khmer.setFlags(item_khmer.flags() | Qt.ItemIsEditable)
        self.sub_table.setItem(row, 3, item_khmer)

    def on_asr_finished(self, success, message):
        self.set_buttons_enabled(True)
        if success:
            QMessageBox.information(self, "Success", message)
            self.lbl_proc_status.setText("ASR Completed")
        else:
            QMessageBox.critical(self, "Error / Stopped", message)
            self.lbl_proc_status.setText("ASR Failed / Stopped")

    def action_translate_text(self):
        row_count = self.sub_table.rowCount()
        if row_count == 0:
            QMessageBox.warning(self, "Warning", "គ្មានអក្សរសម្រាប់បកប្រែទេ។ សូមដំណើរការ 'Auto Recognize Voice' ជាមុនសិន!")
            return

        rows_to_translate = []
        for r in range(row_count):
            item = self.sub_table.item(r, 2)
            orig_text = item.text() if item else ""
            rows_to_translate.append({'row_index': r, 'original_text': orig_text})

        self.set_buttons_enabled(False)

        self.worker_thread = TranslationWorker(rows_to_translate)
        self.worker_thread.progress_signal.connect(self.update_ui_progress)
        self.worker_thread.status_signal.connect(self.update_ui_status)
        self.worker_thread.log_signal.connect(self.append_ui_log)
        self.worker_thread.result_signal.connect(self.update_translation_row)
        self.worker_thread.finished_signal.connect(self.on_translation_finished)
        self.worker_thread.start()

    def update_translation_row(self, row_idx, translated_text):
        item = QTableWidgetItem(translated_text)
        item.setFlags(item.flags() | Qt.ItemIsEditable)
        self.sub_table.setItem(row_idx, 3, item)

    def on_translation_finished(self, success, message):
        self.set_buttons_enabled(True)
        if success:
            QMessageBox.information(self, "Success", message)
            self.lbl_proc_status.setText("Translation Completed")
        else:
            QMessageBox.critical(self, "Error / Stopped", message)
            self.lbl_proc_status.setText("Translation Failed / Stopped")

    def action_export_single_video(self):
        current_item = self.video_list_widget.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Warning", "សូមជ្រើសរើសវីដេអូពីបញ្ជីខាងឆ្វេងជាមុនសិន!")
            return

        row_count = self.sub_table.rowCount()
        if row_count == 0:
            QMessageBox.warning(self, "Warning", "គ្មានទិន្នន័យចំណងជើងសម្រាប់បង្កើតសំឡេងខ្មែរទេ។ សូមប្រាកដថាអ្នកបានដំណើរការ Recognize និង Translate រួចរាល់!")
            return

        custom_widget = self.video_list_widget.itemWidget(current_item)
        video_path = custom_widget.file_path

        def time_str_to_sec(time_str):
            try:
                parts = time_str.split(':')
                if len(parts) == 3:
                    return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
                return 0.0
            except:
                return 0.0

        subtitles_data = []
        for r in range(row_count):
            start_item = self.sub_table.item(r, 0)
            end_item = self.sub_table.item(r, 1)
            khmer_item = self.sub_table.item(r, 3)
            
            start_str = start_item.text() if start_item else "00:00:00"
            end_str = end_item.text() if end_item else "00:00:00"
            khmer_text = khmer_item.text() if khmer_item else ""
            
            subtitles_data.append({
                'start_sec': time_str_to_sec(start_str),
                'end_sec': time_str_to_sec(end_str),
                'khmer_text': khmer_text
            })

        self.set_buttons_enabled(False)
        gender = "Male" if "Male" in self.cb_voice.currentText() else "Female"

        self.worker_thread = ExportWorker(
            video_path=video_path,
            output_dir=self.output_directory,
            subtitles=subtitles_data,
            pipeline_mode=self.pipeline_mode,
            gender=gender
        )
        self.worker_thread.progress_signal.connect(self.update_ui_progress)
        self.worker_thread.status_signal.connect(self.update_ui_status)
        self.worker_thread.log_signal.connect(self.append_ui_log)
        self.worker_thread.finished_signal.connect(self.on_export_finished)
        self.worker_thread.start()

    def on_export_finished(self, success, message):
        self.set_buttons_enabled(True)
        if success:
            QMessageBox.information(self, "Success", message)
            self.lbl_proc_status.setText("Export Completed")
        else:
            QMessageBox.critical(self, "Error / Stopped", message)
            self.lbl_proc_status.setText("Export Failed / Stopped")

    def action_stop_task(self):
        if self.worker_thread and self.worker_thread.isRunning():
            self.worker_thread.stop()
            self.monitor_log.append("[SYSTEM] កំពុងផ្ញើបញ្ជាទៅកាន់ប្រព័ន្ធដើម្បីបញ្ឈប់...")

    def update_ui_progress(self, val):
        self.global_progress.setValue(val)
        self.lbl_progress_percent.setText(f"{val}%")

    def update_ui_status(self, text):
        self.lbl_proc_status.setText(text)

    def append_ui_log(self, msg):
        self.monitor_log.append(msg)

    def select_pipeline_mode(self, mode):
        self.pipeline_mode = mode
        self.monitor_log.append(f"[SYSTEM] របៀបសំឡេងត្រូវបានផ្លាស់ប្តូរទៅជា: {mode}")
        
        active_style = "QPushButton { background-color: #00bcd4; color: black; font-weight: bold; border-radius: 4px; } QPushButton:hover { background-color: #00acc1; }"
        normal_style = "QPushButton { background-color: #004369; color: white; border: 1px solid #006fa3; border-radius: 4px; } QPushButton:hover { background-color: #005b8f; }"
        
        self.btn_tts_only.setStyleSheet(active_style if mode == "TTS Only" else normal_style)
        self.btn_tts_orig.setStyleSheet(active_style if mode == "TTS + Original Music" else normal_style)
        self.btn_tts_vocal.setStyleSheet(active_style if mode == "TTS + Vocal Music" else normal_style)

    def set_buttons_enabled(self, enabled):
        self.btn_add_top.setEnabled(enabled)
        self.btn_recognize.setEnabled(enabled)
        self.btn_translate_top.setEnabled(enabled)
        self.btn_export_video.setEnabled(enabled)
        self.btn_choose.setEnabled(enabled)
        self.btn_out_folder.setEnabled(enabled)

if __name__ == "__main__":
    # Allow Ctrl+C to terminate the application immediately
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    
    app = QApplication(sys.argv)
    window = ToolVideoKH()
    window.show()
    sys.exit(app.exec())