import numpy as np
import whisper
from scipy import signal
from datetime import datetime
from utils import console

def transcribe(audio_np: np.ndarray, orig_sample_rate: int = 16000, language_config=None) -> str:
    """
    Transcribes the given audio data using the Whisper speech recognition model.

    Args:
        audio_np (numpy.ndarray): The audio data to be transcribed.
        orig_sample_rate (int): The sample rate of the audio data.
        language_config (dict): Configuration with language code and model

    Returns:
        str: The transcribed text.
    """
    # Default language if none provided
    if language_config is None:
        language_config = {"code": "en", "model": "base.en"}
    
    # Whisper expects 16kHz audio
    target_sample_rate = 16000
    
    # Resample if necessary
    if orig_sample_rate != target_sample_rate:
        console.print(f"[blue]Resampling audio from {orig_sample_rate}Hz to {target_sample_rate}Hz for transcription")
        # Calculate resampled length
        new_length = int(len(audio_np) * target_sample_rate / orig_sample_rate)
        audio_np = signal.resample(audio_np, new_length)
    
    # Make sure audio is in correct shape and format
    # Whisper expects float32 in range [-1, 1]
    if audio_np.dtype != np.float32:
        audio_np = audio_np.astype(np.float32)
        
    if np.max(np.abs(audio_np)) > 1.0:
        audio_np = audio_np / 32768.0
    
    # Apply some pre-processing to improve speech recognition
    # Normalize audio levels
    max_val = np.max(np.abs(audio_np))
    if max_val > 0:
        # Normalize to use full range, which improves Whisper's performance
        audio_np = audio_np / max_val
    
    console.print(f"[blue]Audio for transcription - samples: {len(audio_np)}, mean abs: {np.abs(audio_np).mean():.4f}")
    
    # Use the global stt model which should be loaded by the caller
    stt = whisper.load_model(language_config["model"])
    
    if language_config["code"] == "de":
        result = stt.transcribe(audio_np, language="de", fp16=False)
    else:
        result = stt.transcribe(audio_np, fp16=False) 
        
    text = result["text"].strip()
    return text


def save_transcription(text, source_file=None):
    """
    Save the transcription to a text file
    
    Args:
        text (str): The transcribed text to save
        source_file (str, optional): Path to the source audio file
        
    Returns:
        str: Path to the saved transcription file
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"./cache/transcription_{timestamp}.txt"
    
    with open(filename, 'w') as f:
        if source_file:
            f.write(f"Source audio: {source_file}\n\n")
        f.write(text)
    
    console.print(f"[green]Transcription saved to {filename}")
    return filename 