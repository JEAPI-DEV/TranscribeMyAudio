# Transcribe your voice or system audio to text.

A simple tool to transcribe your voice or system audio to text.

## Features

- Speech recognition with Whisper
- Recording from microphone or system audio
- Multi-language support (English/German)
- Local processing for privacy

## Usage

1. Recording mode (microphone/system audio)
2. Select language (English/German)
3. Select audio output (speaker/headphones)
4. Start recording
5. Stop recording
6. View transcription
7. Go back to 4

## Setup

### Clone Repository

```bash
git clone https://github.com/JEAPI-DEV/TranscribeMyAudio
cd local-talking-llm
```

### Create conda env

```bash
conda env create -f environment.yml
conda activate voice-assistant
```

### Install dependencies

```bash
sudo apt-get install puleaudio-utils sox
```

### Install NLTK data

```bash
python -c "import nltk; nltk.download('punkt')"
```

### Run the application

```bash
python app.py
```


