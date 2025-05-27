# Specifications for transcribe.py

## 1. Overview

The `transcribe.py` script is a command-line tool designed to transcribe audio files into text. It can optionally perform speaker diarization to identify different speakers in the audio.

## 2. Features

*   **Audio Transcription**: Converts audio content into written text.
*   **Speaker Diarization**: Identifies and labels different speakers in the audio.
*   **Format Conversion**: Utilizes FFmpeg to handle various audio input formats by converting them to WAV.
*   **Customizable Models**: Allows selection of different Whisper models for transcription.
*   **Language Specification**: Supports transcription in various languages.
*   **Flexible Output**: Outputs transcription to a specified file or to standard output.

## 3. Dependencies

### Python Libraries

*   **whisper**: For audio transcription.
*   **pyannote.audio**: For speaker diarization.
*   **pydub**: For audio manipulation and conversion.
*   **torch**: Required by both whisper and pyannote.audio.
*   **torchaudio**: Required by pyannote.audio.
*   **typer**: For creating the command-line interface.
*   **pyyaml**: For loading configuration (though `config.yaml` is not directly used by `transcribe.py` but by `pyannote` indirectly).

### External Tools

*   **FFmpeg**: Required for audio format conversion to WAV. Must be installed and accessible in the system's PATH.

### Configuration Files

*   While `transcribe.py` itself doesn't directly use a `config.yaml`, `pyannote.audio` relies on its own configuration files which might be managed via its caching mechanism. Hugging Face assets are expected to be cached.

## 4. Setup & Installation

*   **Python Dependencies**: Install the required Python libraries using pip:
    ```bash
    pip install whisper pyannote.audio pydub torch torchaudio typer pyyaml
    ```
*   **FFmpeg**: Ensure FFmpeg is installed on your system and that its executable is included in your system's PATH environment variable.
*   **Hugging Face Assets**: `pyannote.audio` and `whisper` download models and other assets from Hugging Face Hub. The script sets `HUGGINGFACE_HUB_CACHE` to `./tmp/assets`, so these assets will be downloaded and expected there.

## 5. Usage

The script is run from the command line:

```bash
python transcribe.py [OPTIONS] FILE
```

### Command-Line Arguments

*   **`FILE`** (required): Path to the audio file to be transcribed.
*   **`--model`** (optional): The Whisper model to use for transcription (e.g., `tiny`, `base`, `small`, `medium`, `large`). Defaults to `base`.
*   **`--language`** (optional): The language of the audio. If not specified, Whisper will attempt to auto-detect the language. (e.g., `en`, `es`, `fr`).
*   **`--diarize`** (optional): A boolean flag (true/false) to enable or disable speaker diarization. Defaults to `false`.
*   **`--output_file`** (optional): Path to the file where the transcription output will be saved. If not provided, the output will be printed to standard output.
*   **`--output_dir`** (optional): Directory where the output file will be saved. If `output_file` is a full path, this is ignored. Defaults to the current directory.
*   **`--debug`** (optional): A boolean flag (true/false) to enable or disable debug mode, which may print more verbose output. Defaults to `false`.

## 6. Core Components (Classes)

### `Config` Class

*   **Role**: Manages the script's configuration, primarily by parsing command-line arguments using Typer. It holds settings like the model name, language, diarization preference, input/output paths, and debug mode.

### `AudioProcessor` Class

*   **Role**: Handles all audio-related operations.
*   **Main Methods/Responsibilities**:
    *   `load_model()`: Loads the specified Whisper model.
    *   `_ensure_wav_format()`: Converts the input audio file to WAV format using FFmpeg if it's not already a WAV file. It creates a temporary WAV file for processing.
    *   `_load_audio()`: Loads the (potentially temporary) WAV audio file for transcription.
    *   `transcribe_audio()`: Performs the actual transcription using the loaded Whisper model.
    *   `diarize_audio()`: Performs speaker diarization using `pyannote.audio`. This involves loading a diarization pipeline and processing the audio to get speaker segments.
    *   `cleanup_temp_files()`: Removes any temporary WAV files created during processing.

### `Transcriber` Class

*   **Role**: Orchestrates the overall transcription and diarization process.
*   **Main Methods/Responsibilities**:
    *   Initializes with a `Config` object.
    *   Creates an `AudioProcessor` instance.
    *   `_check_dependencies()`: Verifies that FFmpeg is installed and accessible.
    *   `run()`: The main method that executes the transcription workflow. It calls methods for dependency checking, model loading, audio processing, transcription, and optionally diarization. It then formats and saves (or prints) the output.
    *   Handles the logic of combining transcription results with diarization segments if diarization is enabled.

## 7. Workflow

1.  **Argument Parsing**: The script starts by parsing command-line arguments using the `Config` class and Typer.
2.  **Dependency Checks**: The `Transcriber` checks if FFmpeg is installed.
3.  **Model Loading**: The `AudioProcessor` loads the specified Whisper transcription model. If diarization is enabled, the relevant `pyannote.audio` models are loaded when `diarize_audio` is called.
4.  **Audio Processing**:
    *   The input audio file is converted to WAV format if necessary (a temporary WAV file might be created).
    *   The WAV audio is loaded.
5.  **Transcription**:
    *   The `AudioProcessor` transcribes the audio using the Whisper model.
    *   If diarization (`--diarize`) is enabled:
        *   The `AudioProcessor` performs speaker diarization to get speaker segments with timestamps.
        *   The `Transcriber` then aligns the transcription results with the speaker segments, adding speaker labels and timestamps to the output.
    *   If diarization is disabled, the output is the plain text transcription.
6.  **Output Saving**: The final transcription (with or without speaker labels) is either saved to the specified output file or printed to the standard output.
7.  **Cleanup**: Any temporary files (e.g., temporary WAV files) are removed.

## 8. Input

*   **Primary Input**: A single audio file.
*   **Supported Audio Formats**: Any audio format that FFmpeg can read and convert to WAV. This includes common formats like MP3, M4A, FLAC, OGG, etc.

## 9. Output

*   **Format**:
    *   **Without Diarization**: Plain text transcription of the audio.
    *   **With Diarization**: Text transcription where each segment is prefixed with a speaker label (e.g., `[SPEAKER_00]`) and a timestamp indicating the start and end of the speaker's utterance (e.g., `[00:00:01.234 --> 00:00:05.678]`).
        Example with diarization:
        ```
        [SPEAKER_00] [00:00:00.500 --> 00:00:03.200] Hello, this is speaker one.
        [SPEAKER_01] [00:00:03.500 --> 00:00:05.800] And this is speaker two.
        ```
*   **Location**:
    *   If `--output_file` is specified, the transcription is saved to that file. The `--output_dir` argument can be used to specify the directory for this file if `--output_file` is just a filename.
    *   If `--output_file` is not specified, the transcription is printed to the standard output.
