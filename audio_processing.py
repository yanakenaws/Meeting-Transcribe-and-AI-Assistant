"""
This module provides functionality for audio processing using the soundcard library.
It includes asynchronous functions to handle audio streaming from a microphone and speaker,
convert the audio data to stereo PCM format, and optionally save the audio to a WAV file.
"""
import asyncio
import soundcard as sc
import numpy as np

async def write_to_wave_file(wav_file, data):
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, wav_file.writeframes, data)

async def audio_stream_generator(ui, stream, sample_rate, chunk_size, save_audio_enabled):
    selected_mic = sc.get_microphone(ui.mic_var.get())
    selected_speaker = sc.get_speaker(ui.speaker_var.get())
    with selected_mic.recorder(samplerate=sample_rate) as mic_recorder, \
         sc.get_microphone(id=str(selected_speaker.id), include_loopback=True).recorder(samplerate=sample_rate) as speaker_mic_recorder:
        while True:
            mic_data = mic_recorder.record(numframes=chunk_size) if ui.mic_enabled.get() else np.zeros((chunk_size, 1), dtype=np.float32)
            speaker_data = speaker_mic_recorder.record(numframes=chunk_size) if ui.speaker_enabled.get() else np.zeros((chunk_size, 1), dtype=np.float32)
            stereo_data = np.zeros((chunk_size, 2), dtype=np.int16)
            stereo_data[:, 0] = np.round(mic_data[:, 0] * 32767).astype(np.int16)
            stereo_data[:, 1] = np.round(speaker_data[:, 0] * 32767).astype(np.int16)
            pcm_data = stereo_data.flatten().astype(np.int16).tobytes()
            # Add to the buffer
            if save_audio_enabled and ui.wav_file:
                ui.audio_buffer += pcm_data
                if len(ui.audio_buffer) > ui.buffer_limit:
                    # Call asynchronous write
                    await write_to_wave_file(ui.wav_file, ui.audio_buffer)
                    ui.audio_buffer = bytearray()  # Clear the buffer

            await stream.input_stream.send_audio_event(audio_chunk=pcm_data)