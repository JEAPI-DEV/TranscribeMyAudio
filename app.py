import threading
import numpy as np
import whisper
import subprocess
import os
from queue import Queue
from datetime import datetime

# Import from our modules
from utils import console
from audio_devices import (
    select_language, 
    select_microphone, 
    select_audio_output,
    select_recording_mode
)
from audio_recorder import record_audio
from transcription import transcribe, save_transcription

# Create cache directory for transcription files
os.makedirs("./cache", exist_ok=True)

# Global variables
selected_mic = None
mic_sample_rate = None
selected_output = None
selected_language = None
recording_mode = "microphone" 
stt = None  


if __name__ == "__main__":
    console.print("[cyan]Transcription Tool started! Press Ctrl+C to exit.")
    try:
        subprocess.run(['parec', '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        subprocess.run(['sox', '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        console.print("[green]Required tools (parec, sox) are available")
    except FileNotFoundError:
        console.print("[red]Warning: Missing required tools. Please install:")
        console.print("[yellow]sudo apt-get install pulseaudio-utils sox")

    recording_mode = select_recording_mode()
    selected_language = select_language()

    console.print(f"[yellow]Loading Whisper model '{selected_language['model']}'...")
    stt = whisper.load_model(selected_language["model"])
    console.print(f"[green]Whisper model loaded!")

    if recording_mode == "microphone":
        selected_mic, mic_sample_rate = select_microphone()
        console.print(f"[green]Microphone selected: {selected_mic} at {mic_sample_rate}Hz")
    else:
        mic_sample_rate = 44100
        selected_output = select_audio_output()
        console.print(f"[green]Audio output monitor selected: {selected_output} at {mic_sample_rate}Hz")

    transcriptions = []

    try:
        while True:
            if recording_mode == "microphone":
                console.print("[cyan]Press Enter to start recording, then speak and press Enter again to stop.")
            else:
                console.print("[cyan]Press Enter to start recording audio output, then press Enter again to stop.")
            
            input()  # Wait for first Enter press to start recording
            
            data_queue = Queue()
            stop_event = threading.Event()
            recording_thread = threading.Thread(
                target=record_audio,
                args=(
                    stop_event, 
                    data_queue, 
                    recording_mode,
                    selected_mic,
                    mic_sample_rate,
                    selected_output
                ),
            )
            recording_thread.start()
            
            # Wait for second Enter press
            input()
            console.print("[yellow]Stopping recording...")
            stop_event.set()
            recording_thread.join()

            audio_chunks = []
            sample_rate = 16000  # Default for Whisper
            file_path = None

            for item in list(data_queue.queue):
                if isinstance(item, tuple):
                    if item[0] == 'sample_rate':
                        sample_rate = item[1]
                    elif item[0] == 'audio_chunk':
                        audio_chunks.append(item[1])
                    elif item[0] == 'file_path':
                        file_path = item[1]

            if audio_chunks:
                audio_np = np.concatenate(audio_chunks, axis=0)
                # Convert to float normalized between -1 and 1
                audio_float = audio_np.astype(np.float32) / 32768.0
                console.print(f"[blue]Audio shape: {audio_np.shape}")
                console.print(f"[blue]Audio stats - min: {np.min(audio_np)}, max: {np.max(audio_np)}, mean: {np.mean(np.abs(audio_np)):.2f}")
                
                if audio_float.size > 100 and np.abs(audio_float).mean() > 0.001:
                    with console.status("Transcribing...", spinner="earth"):
                        text = transcribe(audio_float, sample_rate, selected_language)
                    
                    if text.strip():
                        console.print(f"[green]Transcription: [white]{text}")
                        transcriptions.append(text)
                        save_transcription(text, file_path)
                        if len(transcriptions) > 1:
                            console.print("\n[yellow]Session transcription history:")
                            for i, t in enumerate(transcriptions):
                                console.print(f"[blue]{i+1}. [white]{t}")
                            console.print("\n")
                    else:
                        console.print("[yellow]No speech detected in the transcription. Please try again and speak clearly.")
                else:
                    console.print(
                        "[red]Audio level too low. Please speak louder or check your microphone settings."
                    )
            else:
                console.print(
                    "[red]No audio chunks were recorded. Please check your microphone."
                )

    except KeyboardInterrupt:
        console.print("\n[red]Exiting...")
        if transcriptions:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"./cache/session_transcription_{timestamp}.txt"
            
            with open(filename, 'w') as f:
                f.write(f"# Transcription Session: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                for i, text in enumerate(transcriptions):
                    f.write(f"{i+1}. {text}\n\n")
            
            console.print(f"[green]All session transcriptions saved to {filename}")

    console.print("[blue]Transcription session ended.")
