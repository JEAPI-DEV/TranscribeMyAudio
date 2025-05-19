import os
import time
import numpy as np
import subprocess
from datetime import datetime
from scipy.io import wavfile
from utils import console

def record_audio(stop_event, data_queue, recording_mode, selected_mic=None, mic_sample_rate=44100, selected_output=None):
    """
    Records audio from either microphone or system output
    
    Args:
        stop_event: Threading event to signal recording to stop
        data_queue: Queue to put recorded audio data
        recording_mode: 'microphone' or 'output' 
        selected_mic: Selected microphone device
        mic_sample_rate: Sample rate to record at
        selected_output: Selected output monitor for system audio
    """
    console.print(f"[green]Recording... {'Speak now' if recording_mode == 'microphone' else 'Playing audio'} and press Enter when finished.")
    
    # Create recording file with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"./cache/recording_{timestamp}.wav"
    if recording_mode != "microphone":
        cmd = [
            'parec', 
            f'--device={selected_output}', 
            '--file-format=wav', 
            '--channels=1', 
            f'--rate={mic_sample_rate}', 
            output_file
        ]
        
        console.print(f"[blue]Executing command: {' '.join(cmd)}")
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait for stop_event to be set (Enter is pressed again)
        while not stop_event.is_set() and process.poll() is None:
            time.sleep(0.1)
        
        # Kill the process if it's still running
        if process.poll() is None:
            console.print("[yellow]Stopping recording...")
            process.terminate()
            try:
                process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                process.kill()
                
        # Additional cleanup to make sure no processes are left hanging
        try:
            subprocess.run(['pkill', '-f', f"parec.*{selected_output}"], 
                          stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        except:
            pass
        
        if os.path.exists(output_file) and os.path.getsize(output_file) > 44:
            try:
                sr, audio_data = wavfile.read(output_file)
                if len(audio_data) > 0:
                    console.print(f"[green]Recording successful: {len(audio_data)} samples")
                    console.print(f"[blue]Audio stats - min: {np.min(audio_data)}, max: {np.max(audio_data)}, mean: {np.mean(np.abs(audio_data)):.2f}")
                    
                    data_queue.put(('audio_chunk', audio_data))
                    data_queue.put(('sample_rate', sr))
                    data_queue.put(('file_path', output_file))
                    return
                else:
                    console.print("[red]Recording file is empty (has header but no audio data)")
            except Exception as e:
                console.print(f"[red]Error reading WAV file: {e}")
        else:
            console.print(f"[red]Recording failed or file is empty. File size: {os.path.getsize(output_file) if os.path.exists(output_file) else 'File not found'}")
            
            # Try fallback approaches
            try:
                console.print("[yellow]Trying alternative recording method...")
                os.system(f"timeout 5s parecord '{output_file}' --device='{selected_output}'")
                
                if os.path.exists(output_file) and os.path.getsize(output_file) > 44:
                    sr, audio_data = wavfile.read(output_file)
                    console.print(f"[green]Alternative recording worked: {len(audio_data)} samples")
                    
                    data_queue.put(('audio_chunk', audio_data))
                    data_queue.put(('sample_rate', sr))
                    data_queue.put(('file_path', output_file))
                    return
            except Exception as e2:
                console.print(f"[red]Alternative recording method failed: {e2}")
        
        return  
    
    try:
        # Use arecord with default device for microphone (works well with PipeWire)
        process = subprocess.Popen([
            'arecord',
            '--device=default',
            '-f', 'S16_LE',
            '-c', '1',
            '-r', str(mic_sample_rate),
            '-t', 'wav',
            output_file
        ])
        
        # Wait until stop_event is set (user presses Enter again)
        while not stop_event.is_set() and process.poll() is None:
            time.sleep(0.1)
        
        console.print("[yellow]Stopping recording...")
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                console.print("[red]Process did not terminate gracefully, killing it")
                process.kill()
        
        if os.path.exists(output_file) and os.path.getsize(output_file) > 44:
            try:
                sr, audio_data = wavfile.read(output_file)
                if len(audio_data) > 0:
                    console.print(f"[green]Recording successful: {len(audio_data)} samples")
                    console.print(f"[blue]Audio stats - min: {np.min(audio_data)}, max: {np.max(audio_data)}, mean: {np.mean(np.abs(audio_data)):.2f}")
                    
                    data_queue.put(('audio_chunk', audio_data))
                    data_queue.put(('sample_rate', sr))
                    data_queue.put(('file_path', output_file))
                    return
                else:
                    console.print("[red]Recording file is empty (has header but no audio data)")
            except Exception as e:
                console.print(f"[red]Error reading WAV file: {e}")
        else:
            console.print(f"[red]Recording failed or file is empty. File size: {os.path.getsize(output_file) if os.path.exists(output_file) else 'File not found'}")
    except Exception as e:
        console.print(f"[red]Error with recording: {e}")
        
        # Simple fallback for microphone recording
        if recording_mode == "microphone":
            try:
                console.print("[yellow]Trying fallback recording (5 seconds)...")
                os.system(f"arecord -d 5 -f cd -t wav {output_file}")
                
                if os.path.exists(output_file) and os.path.getsize(output_file) > 44:
                    sr, audio_data = wavfile.read(output_file)
                    console.print(f"[green]Fallback recording worked: {len(audio_data)} samples")
                    
                    data_queue.put(('audio_chunk', audio_data))
                    data_queue.put(('sample_rate', sr))
                    data_queue.put(('file_path', output_file))
            except Exception as e2:
                console.print(f"[red]Fallback recording also failed: {e2}")
        # Fallback for system audio recording
        else:
            try:
                console.print("[yellow]Trying alternative system audio recording approach (5 seconds)...")
                os.system(f"timeout 5s parec --device='{selected_output}' --file-format=wav --channels=1 --rate={mic_sample_rate} '{output_file}'")
                
                if os.path.exists(output_file) and os.path.getsize(output_file) > 44:
                    sr, audio_data = wavfile.read(output_file)
                    console.print(f"[green]Alternative recording worked: {len(audio_data)} samples")
                    
                    data_queue.put(('audio_chunk', audio_data))
                    data_queue.put(('sample_rate', sr))
                    data_queue.put(('file_path', output_file))
                else:
                    console.print("[yellow]Trying final fallback recording...")
                    os.system(f"timeout 5s parecord '{output_file}' --device='{selected_output}'")
                    
                    if os.path.exists(output_file) and os.path.getsize(output_file) > 44:
                        sr, audio_data = wavfile.read(output_file)
                        console.print(f"[green]Final fallback recording worked: {len(audio_data)} samples")
                        
                        data_queue.put(('audio_chunk', audio_data))
                        data_queue.put(('sample_rate', sr))
                        data_queue.put(('file_path', output_file))
            except Exception as e2:
                console.print(f"[red]All system audio recording attempts failed: {e2}") 