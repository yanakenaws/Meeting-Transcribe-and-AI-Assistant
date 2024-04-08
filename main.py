"""
    This Python script provides a graphical user interface (GUI) for real-time speech recognition and transcription using Amazon Transcribe service.
    It utilizes the soundcard library to capture audio from the microphone and system speaker, and streams the audio data to Amazon Transcribe for transcription.
    The transcribed text is displayed in the GUI, with microphone and speaker audio distinguished by different colors.
"""
import os
import tkinter as tk
from tkinter import ttk
import asyncio
import threading
import soundcard as sc
import numpy as np
from amazon_transcribe.client import TranscribeStreamingClient
from amazon_transcribe.handlers import TranscriptResultStreamHandler
from amazon_transcribe.model import TranscriptEvent
from datetime import datetime
import logging
import wave
import configparser
from make_summary import make_summary

# Set up logging
logging.basicConfig(filename='app.log', level=logging.ERROR)

# Reads the configuration file.
inifile = configparser.ConfigParser()
inifile.read('settings.ini', encoding='utf-8')

# Use the settings
LANGUAGE_CODE = inifile.get('DEFAULT', 'language_code')
TRANSCRIBE_REGION = inifile.get('DEFAULT', 'transcribe_region')
FILE_PATH = inifile.get('DEFAULT', 'file_path')
SAVE_AUDIO_ENABLED = inifile.getboolean('DEFAULT', 'save_audio_enabled')
MAKE_SUMMARY_ENABLED = inifile.getboolean('DEFAULT', 'make_summary_enabled')
BEDROCK_REGION = inifile.get('DEFAULT', 'bedrock_region')
CUSTOM_VOCABULARY_ENABLED = inifile.getboolean('DEFAULT', 'custom_vocabulary_enabled')
VOCABULARY_NAME = inifile.get('DEFAULT', 'vocabulary_name', fallback=None)  # fallback to None if vocabulary_name is not set
LLM_MODEL_NAME = inifile.get('DEFAULT', 'llm_model_name', fallback=None)  # fallback to None if llm_model_name is not set

# Amazon Transcribe settings
SAMPLE_RATE = 16000  # Sample rate: 16kHz
CHUNK_DURATION_MS = 10  # Chunk duration: 10 milliseconds
CHUNK_SIZE = int(CHUNK_DURATION_MS / 1000 * SAMPLE_RATE * 2)  # Calculate chunk size in number of samples
BYTES_PER_SAMPLE = 2  # Bytes per sample: 2 bytes for 16-bit PCM

# Create the output file directory if it doesn't exist
if not os.path.exists(FILE_PATH):
    os.makedirs(FILE_PATH)

async def write_to_wave_file(wav_file, data):
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, wav_file.writeframes, data)

class MyTranscriptResultStreamHandler(TranscriptResultStreamHandler):
    def __init__(self, ui, file_name, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ui = ui
        self.file_name = file_name

    async def handle_transcript_event(self, transcript_event: TranscriptEvent):
        # Handle transcript events
        for result in transcript_event.transcript.results:
            if not result.is_partial:
                text = f"{result.channel_id}: {result.alternatives[0].transcript}\n"
                with open(f"{FILE_PATH}/{self.file_name}", "a", encoding="utf-8") as file:
                    file.write(text)
                # Schedule UI update on the UI thread
                self.ui.master.after(0, self.ui.update_transcription, text)

class TranscribeUI:
    def __init__(self, master):
        self.master = master
        self.wav_file = None  # Hold the WAV file handle
        self.audio_buffer = bytearray()  # Buffer for audio data
        self.buffer_limit = 1024 * 100  # Buffer size limit (e.g., 100KB)
        self.mic_enabled = tk.BooleanVar(value=True)  # Variable for enabling microphone
        self.speaker_enabled = tk.BooleanVar(value=True)  # Variable for enabling speaker
        self.file_name = ""  # Variable to store the file name
        self.setup_ui(master)

    def setup_ui(self, master):
        # Set up the UI
        master.title("Meeting Transcribe and AI Assistant")
        # Create frames for laying out widgets in a grid
        left_frame = tk.Frame(master)
        left_frame.grid(row=0, column=0, sticky="ns")
        right_frame = tk.Frame(master)
        right_frame.grid(row=0, column=1, sticky="nsew")

        master.grid_columnconfigure(1, weight=1)  # Allow the right frame to expand/shrink with window resize
        master.grid_rowconfigure(0, weight=1)  # Allow vertical resizing

        self.setup_buttons(left_frame)
        self.setup_transcription_text(right_frame)
        self.setup_file_name_entry(left_frame)
        self.setup_device_selection(left_frame)
        master.protocol("WM_DELETE_WINDOW", self.on_close)

    def setup_buttons(self, master):
        # Set up the start/stop button
        self.start_stop_button = ttk.Button(master, text="Start", command=self.toggle_start_stop)
        self.start_stop_button.grid(row=0, column=0, pady=5, sticky="ew")  # Use grid for layout

    def setup_transcription_text(self, master):
        # Set up the transcription text box
        self.transcription_text = tk.Text(master, height=15, width=50)
        self.transcription_text.pack(expand=True, fill=tk.BOTH, side=tk.LEFT)

    def setup_file_name_entry(self, master):
        # Set up the output file name entry
        ttk.Label(master, text="File Name:").grid(row=1, column=0, sticky="w")  # Use grid for layout
        self.file_name_entry = ttk.Entry(master)
        self.file_name_entry.grid(row=2, column=0, pady=5, sticky="ew")  # Use grid for layout
        self.file_name_entry.insert(0, datetime.now().strftime("%Y%m%d-%H%M") + ".txt")

    def setup_device_selection(self, master):
        # Set up device selection
        self.async_loop = None
        self.transcribe_task = None
        self.mic_var = tk.StringVar(master)
        self.speaker_var = tk.StringVar(master)
        mics = [mic.name for mic in sc.all_microphones(include_loopback=True)]
        speakers = [speaker.name for speaker in sc.all_speakers()]
        self.mic_var.set(sc.default_microphone().name)
        self.speaker_var.set(sc.default_speaker().name)

        # Set up device selection
        ttk.Label(master, text="Microphone:").grid(row=3, column=0, sticky="w")  # Use grid for layout
        self.mic_menu = ttk.Combobox(master, textvariable=self.mic_var, values=mics, state="readonly")
        self.mic_menu.grid(row=4, column=0, pady=5, sticky="ew")  # Use grid for layout
        # Add a checkbox to enable microphone
        ttk.Checkbutton(master, text="Enable Microphone", variable=self.mic_enabled).grid(row=5, column=0, sticky="w", pady=5)

        ttk.Label(master, text="Speaker:").grid(row=6, column=0, sticky="w")  # Use grid for layout
        self.speaker_menu = ttk.Combobox(master, textvariable=self.speaker_var, values=speakers, state="readonly")
        self.speaker_menu.grid(row=7, column=0, pady=5, sticky="ew")  # Use grid for layout
        # Add a checkbox to enable speaker
        ttk.Checkbutton(master, text="Enable Speaker", variable=self.speaker_enabled).grid(row=8, column=0, sticky="w", pady=5)

    def on_close(self):
        # Handle window close event
        if self.transcribe_task and not self.transcribe_task.done():
            self.transcribe_task.cancel()
            print("Canceled speech recognition process.")
        if self.async_loop:
            self.async_loop.call_soon_threadsafe(self.async_loop.stop)
            print("Stopped event loop.")
        self.master.destroy()
        print("Closed window and exiting program.")

    def toggle_start_stop(self):
        # Toggle the start/stop button
        if self.start_stop_button["text"] == "Start":
            self.start_stop_button["text"] = "Stop"
            self.file_name_entry.config(state="disabled")
            self.mic_menu.config(state="disabled")
            self.speaker_menu.config(state="disabled")
            self.file_name = self.file_name_entry.get()  # Get the file name
            # Set up and open the WAV file
            if SAVE_AUDIO_ENABLED:
                wav_file_name = self.file_name + ".wav"
                wav_file_path = f"{FILE_PATH}/{wav_file_name}"
                self.wav_file = wave.open(wav_file_path, 'wb')
                self.wav_file.setnchannels(2)  # Stereo
                self.wav_file.setsampwidth(BYTES_PER_SAMPLE)
                self.wav_file.setframerate(SAMPLE_RATE)
            self.audio_buffer = bytearray()  # Clear the buffer when starting
            if not self.async_loop:
                self.async_loop = asyncio.new_event_loop()
                threading.Thread(target=self.start_asyncio_loop, args=(self.async_loop,)).start()
            self.transcribe_task = asyncio.run_coroutine_threadsafe(self.transcribe_stream(), self.async_loop)
        else:
            self.start_stop_button["text"] = "Start"
            self.file_name_entry.config(state="normal")
            self.file_name_entry.delete(0, tk.END)
            self.file_name_entry.insert(0, datetime.now().strftime("%Y%m%d-%H%M") + ".txt")
            self.mic_menu.config(state="readonly")
            self.speaker_menu.config(state="readonly")
            if self.transcribe_task and not self.transcribe_task.done():
                self.transcribe_task.cancel()
                print("Canceled speech recognition process.")
            if self.wav_file:
                if self.audio_buffer:
                    self.wav_file.writeframes(self.audio_buffer)  # Write remaining buffer
                self.wav_file.close()
                self.wav_file = None
                self.audio_buffer = bytearray()
            # Generate summary
            if MAKE_SUMMARY_ENABLED:
                if self.async_loop:
                    self.async_loop.run_in_executor(None, make_summary, f"{FILE_PATH}/{self.file_name}", LLM_MODEL_NAME, BEDROCK_REGION)

    def start_asyncio_loop(self, loop):
        asyncio.set_event_loop(loop)
        loop.run_forever()

    async def audio_stream_generator(self, stream):
        # Send audio from microphone and speaker to the stream
        selected_mic = sc.get_microphone(self.mic_var.get())
        selected_speaker = sc.get_speaker(self.speaker_var.get())
        with selected_mic.recorder(samplerate=SAMPLE_RATE) as mic_recorder, \
             sc.get_microphone(id=str(selected_speaker.id), include_loopback=True).recorder(samplerate=SAMPLE_RATE) as speaker_mic_recorder:
            while True:
                mic_data = mic_recorder.record(numframes=CHUNK_SIZE) if self.mic_enabled.get() else np.zeros((CHUNK_SIZE, 1), dtype=np.float32)
                speaker_data = speaker_mic_recorder.record(numframes=CHUNK_SIZE) if self.speaker_enabled.get() else np.zeros((CHUNK_SIZE, 1), dtype=np.float32)
                stereo_data = np.zeros((CHUNK_SIZE, 2), dtype=np.int16)
                stereo_data[:, 0] = np.round(mic_data[:, 0] * 32767).astype(np.int16)
                stereo_data[:, 1] = np.round(speaker_data[:, 0] * 32767).astype(np.int16)
                pcm_data = stereo_data.flatten().astype(np.int16).tobytes()
                # Add to the buffer
                if SAVE_AUDIO_ENABLED and self.wav_file:
                    self.audio_buffer += pcm_data
                    if len(self.audio_buffer) > self.buffer_limit:
                        # Call asynchronous write
                        await write_to_wave_file(self.wav_file, self.audio_buffer)
                        self.audio_buffer = bytearray()  # Clear the buffer

                await stream.input_stream.send_audio_event(audio_chunk=pcm_data)

    async def transcribe_stream(self):
        # Speech recognition and transcription using Amazon Transcribe
        client = TranscribeStreamingClient(region=TRANSCRIBE_REGION)
        transcribe_kwargs = {
            "language_code": LANGUAGE_CODE,
            "media_sample_rate_hz": SAMPLE_RATE,
            "media_encoding": "pcm",
            "number_of_channels": 2,
            "enable_channel_identification": True,
        }
        # Enable custom vocabulary
        if CUSTOM_VOCABULARY_ENABLED:
            transcribe_kwargs["vocabulary_name"] = VOCABULARY_NAME

        stream = await client.start_stream_transcription(**transcribe_kwargs)

        handler = MyTranscriptResultStreamHandler(self, self.file_name, stream.output_stream)
        try:
            await asyncio.gather(
                self.audio_stream_generator(stream),
                handler.handle_events(),
            )
        except asyncio.CancelledError:
            await stream.input_stream.end_stream()
            print("Stream ended.")
        except Exception as e:
            print(f"Unexpected error: {e}")

    def update_transcription(self, text):
        self.transcription_text.tag_configure("ch_0_color", foreground="#800000")  # Dark orange
        self.transcription_text.tag_configure("ch_1_color", foreground="#006400")  # Dark green

        # Update the transcription text box in the UI
        tag = "ch_0_color" if text.startswith("ch_0:") else "ch_1_color"
        text = text[6:]  # Remove channel information
        text = text.replace("。", "。\r\n")  # Add a newline at the end of each sentence
        self.transcription_text.insert("end", text, tag)
        self.transcription_text.see(tk.END)

if __name__ == "__main__":
    root = tk.Tk()
    ui = TranscribeUI(root)
    root.geometry("600x300")
    root.wm_minsize(400, 250)

    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("Exiting program due to keyboard interrupt.")
    finally:
        if ui.transcribe_task and not ui.transcribe_task.done():
            ui.transcribe_task.cancel()
            print("Canceled speech recognition process.")
        if ui.async_loop:
            ui.async_loop.call_soon_threadsafe(ui.async_loop.stop)
            print("Stopped event loop.")
        try:
            if root.winfo_exists():
                root.destroy()
                print("Closed window and exiting program.")
        except tk.TclError:
            pass