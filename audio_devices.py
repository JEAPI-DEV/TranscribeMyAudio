import re
import subprocess
from utils import console

def select_language():
    """
    Allows the user to select a language for transcription.
    
    Returns:
        dict: Language code and corresponding Whisper model
    """
    console.print("[yellow]Available languages:")
    console.print("[cyan]1: English (fast)")
    console.print("[cyan]2: English (accurate)")
    console.print("[cyan]3: German (fast)")
    console.print("[cyan]4: German (accurate)")
    
    try:
        selection = input("Select language option (1-4) > ")
        if selection.strip() == "2":
            console.print("[green]Selected language: English (accurate)")
            return {"code": "en", "model": "medium"}
        elif selection.strip() == "3":
            console.print("[green]Selected language: German (fast)")
            return {"code": "de", "model": "small"}
        elif selection.strip() == "4":
            console.print("[green]Selected language: German (accurate)")
            return {"code": "de", "model": "medium"}
        else:
            console.print("[green]Selected language: English (fast)")
            return {"code": "en", "model": "base.en"}
    except ValueError:
        console.print("[yellow]Invalid input, using English (fast) as default")
        return {"code": "en", "model": "base.en"}

def select_microphone():
    """
    Selects a microphone using ALSA directly.
    
    Returns:
        tuple: (device_id, sample_rate) for recording
    """
    # First get ALSA devices directly
    try:
        result = subprocess.run(['arecord', '-l'], capture_output=True, text=True)
        console.print("[magenta]ALSA devices from arecord -l:")
        console.print(result.stdout)
        
        # Parse output to find microphones
        devices = []
        pattern = re.compile(r'card (\d+): (\w+) \[(.*?)\], device (\d+): (.*)')
        
        for line in result.stdout.split('\n'):
            match = pattern.search(line)
            if match:
                card_num, card_id, card_name, device_num, device_name = match.groups()
                device_id = f"hw:{card_num},{device_num}"
                devices.append({
                    'card_num': card_num,
                    'device_num': device_num,
                    'name': f"{card_name}: {device_name}",
                    'id': device_id
                })
        
        if devices:
            # Look for Trust microphone first
            for idx, device in enumerate(devices):
                if "Trust" in device['name'] or "GXT" in device['name'] or "Microphone" in device['name']:
                    console.print(f"[green]Found Trust microphone: {device['name']}")
                    # For PipeWire systems, use "default" instead of "hw:"
                    return "default", 44100  # Use the default device which should map to the right one in PipeWire
            
            # If no Trust mic found, let user select
            console.print("[yellow]Please select a microphone:")
            for idx, device in enumerate(devices):
                console.print(f"[yellow]{idx}: {device['name']} ({device['id']})")
            
            try:
                selection = int(input("Select microphone number > "))
                if 0 <= selection < len(devices):
                    device = devices[selection]
                    console.print(f"[green]Selected: {device['name']}")
                    return "default", 44100  # Use default for PipeWire compatibility
            except ValueError:
                console.print("[red]Invalid input, using default device")
                return "default", 44100
        else:
            console.print("[red]No ALSA devices found!")
    
    except Exception as e:
        console.print(f"[red]Error detecting ALSA devices: {e}")
    
    # Fallback
    console.print("[yellow]Using default audio device")
    return "default", 44100

def select_audio_output():
    """
    Selects an audio output device for monitoring/recording.
    
    Returns:
        str: Device ID for monitoring audio output
    """
    # Try to get PulseAudio/PipeWire monitor sources
    try:
        result = subprocess.run(['pactl', 'list', 'sources'], capture_output=True, text=True)
        console.print("[magenta]PulseAudio/PipeWire sources:")
        
        # Parse output to find monitor sources
        sources = []
        current_source = {}
        monitor_pattern = re.compile(r'monitor.*of.*')
        
        for line in result.stdout.split('\n'):
            if line.startswith('Source #'):
                if current_source and 'index' in current_source and 'name' in current_source:
                    sources.append(current_source)
                current_source = {'index': line.split('#')[1].strip()}
            elif 'Name:' in line and current_source:
                current_source['name'] = line.split('Name:')[1].strip()
            elif 'Description:' in line and current_source:
                current_source['description'] = line.split('Description:')[1].strip()
        
        # Add the last source
        if current_source and 'index' in current_source and 'name' in current_source:
            sources.append(current_source)
        
        # Filter to find monitor sources
        monitor_sources = []
        for source in sources:
            if 'description' in source and (
                monitor_pattern.search(source['description'].lower()) or 
                'monitor' in source['name'].lower()
            ):
                monitor_sources.append(source)
        
        if monitor_sources:
            console.print("[yellow]Available audio output monitors:")
            for idx, source in enumerate(monitor_sources):
                console.print(f"[yellow]{idx}: {source.get('description', source['name'])}")
            
            try:
                selection = int(input("Select output monitor number > "))
                if 0 <= selection < len(monitor_sources):
                    source = monitor_sources[selection]
                    console.print(f"[green]Selected: {source.get('description', source['name'])}")
                    return source['name']
            except ValueError:
                console.print("[red]Invalid input, using default monitor")
        else:
            console.print("[yellow]No monitor sources found, checking all sources...")
            # If no monitor sources found, show all sources
            if sources:
                console.print("[yellow]Available audio sources (may not all be monitors):")
                for idx, source in enumerate(sources):
                    console.print(f"[yellow]{idx}: {source.get('description', source['name'])}")
                
                try:
                    selection = int(input("Select source number > "))
                    if 0 <= selection < len(sources):
                        source = sources[selection]
                        console.print(f"[green]Selected: {source.get('description', source['name'])}")
                        return source['name']
                except ValueError:
                    console.print("[red]Invalid input, trying to find default monitor")
    
    except Exception as e:
        console.print(f"[red]Error detecting PulseAudio sources: {e}")
    
    # Try to find default monitor
    try:
        # Check for common default monitor names
        result = subprocess.run(['pactl', 'list', 'short', 'sources'], capture_output=True, text=True)
        console.print("[cyan]Available sources from 'pactl list short sources':")
        console.print(result.stdout)
        
        monitors = []
        for line in result.stdout.split('\n'):
            if 'monitor' in line.lower():
                device = line.split('\t')[1]
                monitors.append(device)
                console.print(f"[green]Found monitor source: {device}")
        
        if monitors:
            # Select the first monitor
            return monitors[0]
    except Exception as e:
        console.print(f"[red]Error finding default monitor: {e}")
    
    # Final fallback
    console.print("[yellow]Using default monitor source")
    return "alsa_output.pci-0000_00_1f.3.analog-stereo.monitor"  # Common default monitor

def select_recording_mode():
    """
    Allows the user to select whether to record from microphone or system audio output.
    
    Returns:
        str: Recording mode ('microphone' or 'output')
    """
    console.print("[yellow]Select recording source:")
    console.print("[cyan]1: Microphone (record your voice)")
    console.print("[cyan]2: System Audio (record computer sound output)")
    
    try:
        selection = input("Select recording source (1-2) > ")
        if selection.strip() == "2":
            console.print("[green]Selected recording source: System Audio Output")
            return "output"
        else:
            console.print("[green]Selected recording source: Microphone")
            return "microphone"
    except ValueError:
        console.print("[yellow]Invalid input, using Microphone as default")
        return "microphone" 