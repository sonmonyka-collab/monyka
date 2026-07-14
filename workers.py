import os
from PySide6.QtCore import QThread, Signal
from gtts import gTTS
import speech_recognition as sr
from moviepy import VideoFileClip, AudioFileClip, CompositeAudioClip
from translator import Translator

# -------------------------------------------------------------------------
# WORKER 1: SPEECH RECOGNITION (ASR)
# -------------------------------------------------------------------------
class ASRWorker(QThread):
    progress_signal = Signal(int)
    status_signal = Signal(str)
    log_signal = Signal(str)
    chunk_signal = Signal(str, str, str)
    finished_signal = Signal(bool, str)

    def __init__(self, video_path, source_lang, output_dir):
        super().__init__()
        self.video_path = video_path
        self.source_lang = source_lang
        self.output_dir = output_dir
        self._is_running = True

    def stop(self):
        self._is_running = False

    def format_time(self, seconds):
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds % 1) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"

    def run(self):
        self.status_signal.emit("កំពុងទាញយកសំឡេង...")
        self.progress_signal.emit(5)
        
        temp_full_wav = os.path.join(self.output_dir, f"temp_full_audio_{os.path.basename(self.video_path)}.wav")
        
        try:
            self.log_signal.emit(f"[ASR] 🎬 កំពុងបើកវីដេអូ៖ {os.path.basename(self.video_path)}")
            video_clip = VideoFileClip(self.video_path)
            duration = video_clip.duration
            self.log_signal.emit(f"[INFO] ⏱️ រយៈពេលវីដេអូសរុប: {duration:.2f} វិនាទី")
            
            if not video_clip.audio:
                video_clip.close()
                self.finished_signal.emit(False, "វីដេអូគ្មានសំឡេងសម្រាប់ស្កេនទេ។")
                return

            self.log_signal.emit("[ASR] 🎙️ កំពុងទាញយកសំឡេងចេញពីវីដេអូ...")
            video_clip.audio.write_audiofile(temp_full_wav, codec="pcm_s16le", fps=16000, logger=None)
            video_clip.close()

            r = sr.Recognizer()
            chunk_duration = 3.0
            start_time = 0.0
            chunk_index = 0

            with sr.AudioFile(temp_full_wav) as source:
                while start_time < duration:
                    if not self._is_running:
                        break
                    
                    rem = duration - start_time
                    if rem < 0.5:
                        break
                        
                    current_chunk_dur = min(chunk_duration, rem)
                    end_time = start_time + current_chunk_dur
                    
                    self.log_signal.emit(f"[ASR] 🎙️ កំពុងស្កេនសំឡេងចន្លោះ {self.format_time(start_time)} - {self.format_time(end_time)}...")
                    
                    audio_data = r.record(source, duration=current_chunk_dur)
                    
                    recognized_text = ""
                    try:
                        recognized_text = r.recognize_google(audio_data, language=self.source_lang)
                        self.log_signal.emit(f"[ASR] 🗣️ Chunk {chunk_index+1}: \"{recognized_text}\"")
                    except sr.UnknownValueError:
                        self.log_signal.emit(f"[ASR] 🔇 គ្មានការនិយាយនៅ Chunk {chunk_index+1} ទេ។")
                    except Exception as err:
                        self.log_signal.emit(f"[ASR ERROR] ❌ កំហុសស្កេន៖ {str(err)}")

                    start_str = self.format_time(start_time)
                    end_str = self.format_time(end_time)
                    self.chunk_signal.emit(start_str, end_str, recognized_text)

                    progress_pct = int(5 + (start_time / duration) * 90)
                    self.progress_signal.emit(progress_pct)
                    
                    start_time += current_chunk_dur
                    chunk_index += 1

            if os.path.exists(temp_full_wav):
                os.remove(temp_full_wav)

            self.progress_signal.emit(100)
            if self._is_running:
                self.finished_signal.emit(True, "ស្កេនសំឡេងក្នុងវីដេអូបានជោគជ័យ!")
            else:
                self.finished_signal.emit(False, "ដំណើរការត្រូវបានបោះបង់។")

        except Exception as e:
            if os.path.exists(temp_full_wav):
                try:
                    os.remove(temp_full_wav)
                except:
                    pass
            self.finished_signal.emit(False, f"កំហុស ASR៖ {str(e)}")


# -------------------------------------------------------------------------
# WORKER 2: TRANSLATION
# -------------------------------------------------------------------------
class TranslationWorker(QThread):
    progress_signal = Signal(int)
    status_signal = Signal(str)
    log_signal = Signal(str)
    result_signal = Signal(int, str)
    finished_signal = Signal(bool, str)

    def __init__(self, rows_to_translate):
        super().__init__()
        self.rows = rows_to_translate
        self.translator = Translator()
        self._is_running = True

    def stop(self):
        self._is_running = False

    def run(self):
        total = len(self.rows)
        if total == 0:
            self.finished_signal.emit(True, "គ្មានខ្លឹមសារសម្រាប់បកប្រែទេ។")
            return

        self.status_signal.emit("កំពុងបកប្រែ...")
        self.progress_signal.emit(10)

        for i, item in enumerate(self.rows):
            if not self._is_running:
                break
            
            row_idx = item['row_index']
            orig_text = item['original_text']
            
            if orig_text.strip():
                try:
                    trans_obj = self.translator.translate(orig_text, dest='km')
                    translated_text = trans_obj.text
                    self.log_signal.emit(f"[TRANSLATION] Row {row_idx+1}: \"{orig_text}\" -> \"{translated_text}\"")
                    self.result_signal.emit(row_idx, translated_text)
                except Exception as e:
                    self.log_signal.emit(f"[TRANSLATION ERROR] ❌ Row {row_idx+1}: {str(e)}")
                    self.result_signal.emit(row_idx, "")
            else:
                self.result_signal.emit(row_idx, "")

            pct = int(10 + (i + 1) / total * 90)
            self.progress_signal.emit(pct)

        self.progress_signal.emit(100)
        if self._is_running:
            self.finished_signal.emit(True, "បកប្រែខ្លឹមសារបានជោគជ័យ!")
        else:
            self.finished_signal.emit(False, "ដំណើរការត្រូវបានបោះបង់។")


# -------------------------------------------------------------------------
# WORKER 3: TTS GENERATION AND AUDIO MERGING
# -------------------------------------------------------------------------
class ExportWorker(QThread):
    progress_signal = Signal(int)
    status_signal = Signal(str)
    log_signal = Signal(str)
    finished_signal = Signal(bool, str)

    def __init__(self, video_path, output_dir, subtitles, pipeline_mode="TTS Only", gender="Male"):
        super().__init__()
        self.video_path = video_path
        self.output_dir = output_dir
        self.subtitles = subtitles
        self.pipeline_mode = pipeline_mode
        self.gender = gender
        self._is_running = True

    def stop(self):
        self._is_running = False

    def run(self):
        from moviepy import VideoFileClip, AudioFileClip, CompositeAudioClip
        from gtts import gTTS
        
        self.status_signal.emit("កំពុង Render វីដេអូ...")
        self.progress_signal.emit(5)

        video_name = os.path.basename(self.video_path)
        name_without_ext = os.path.splitext(video_name)[0]
        output_video_path = os.path.join(self.output_dir, f"{name_without_ext}_KH_Version.mp4")
        
        temp_files = []
        khmer_clips = []

        try:
            self.log_signal.emit(f"[EXPORT] 🎬 កំពុងបើកវីដេអូដើម៖ {video_name}")
            video_clip = VideoFileClip(self.video_path)
            original_audio = video_clip.audio

            total_subs = len(self.subtitles)
            self.log_signal.emit(f"[EXPORT] 🎙️ កំពុងបង្កើតសំឡេងនិយាយភាសាខ្មែរ (TTS)...")

            for idx, sub in enumerate(self.subtitles):
                if not self._is_running:
                    break
                
                start_sec = sub['start_sec']
                kh_text = sub['khmer_text']
                
                if kh_text.strip():
                    temp_mp3 = os.path.join(self.output_dir, f"temp_tts_export_{idx}.mp3")
                    temp_files.append(temp_mp3)
                    
                    try:
                        tts = gTTS(text=kh_text, lang='km', slow=False)
                        tts.save(temp_mp3)
                        
                        audio_clip = AudioFileClip(temp_mp3)
                        audio_clip = audio_clip.with_start(start_sec)
                        khmer_clips.append(audio_clip)
                    except Exception as err:
                        self.log_signal.emit(f"[TTS ERROR] ❌ ជួរទី {idx+1}: {str(err)}")

                pct = int(5 + (idx + 1) / total_subs * 60)
                self.progress_signal.emit(pct)

            if not self._is_running:
                raise Exception("ដំណើរការត្រូវបានបោះបង់ដោយអ្នកប្រើប្រាស់។")

            self.progress_signal.emit(70)
            self.log_signal.emit("[MIXER] 🎛️ កំពុងផ្គុំសំឡេងខ្មែរ ចូលទៅកាន់វីដេអូ...")

            final_audio_clips = []

            if self.pipeline_mode == "TTS Only":
                if khmer_clips:
                    final_audio = CompositeAudioClip(khmer_clips)
                    video_clip.audio = final_audio
                else:
                    self.log_signal.emit("[WARNING] ⚠️ គ្មានសំឡេងខ្មែរត្រូវបានបង្កើតទេ វីដេអូគ្មានសំឡេង។")
                    video_clip.audio = None
            elif self.pipeline_mode == "TTS + Original Music":
                if original_audio:
                    orig_music = original_audio.with_volume_scaled(0.15)
                    final_audio_clips.append(orig_music)
                final_audio_clips.extend(khmer_clips)
                if final_audio_clips:
                    video_clip.audio = CompositeAudioClip(final_audio_clips)
            else: # TTS + Vocal Music
                if original_audio:
                    orig_music = original_audio.with_volume_scaled(0.30)
                    final_audio_clips.append(orig_music)
                final_audio_clips.extend(khmer_clips)
                if final_audio_clips:
                    video_clip.audio = CompositeAudioClip(final_audio_clips)

            self.progress_signal.emit(85)
            self.log_signal.emit("[EXPORT] 🎥 កំពុង Render វីដេអូចុងក្រោយ (សូមរង់ចាំ)...")
            
            video_clip.write_videofile(
                output_video_path,
                codec="libx264",
                audio_codec="aac",
                logger=None
            )

            # Close clips
            video_clip.close()
            if original_audio:
                original_audio.close()
            for clip in khmer_clips:
                clip.close()

            # Clean up temp MP3 files
            self.log_signal.emit("[CLEANUP] 🧹 កំពុងលុបឯកសារបណ្ដោះអាសន្ន...")
            for tf in temp_files:
                try:
                    if os.path.exists(tf):
                        os.remove(tf)
                except:
                    pass

            self.progress_signal.emit(100)
            self.finished_signal.emit(True, f"ការ Export វីដេអូបានជោគជ័យ! រក្សាទុកនៅ៖\n{output_video_path}")

        except Exception as e:
            for tf in temp_files:
                try:
                    if os.path.exists(tf):
                        os.remove(tf)
                except:
                    pass
            self.finished_signal.emit(False, f"កំហុស Export៖ {str(e)}")
