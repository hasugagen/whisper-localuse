# transcribe.py の仕様

## 1. 概要

`transcribe.py` スクリプトは、音声ファイルからテキストへの文字起こしを行うために設計されたコマンドラインツールです。オプションで話者ダイアライゼーションを実行し、音声中の異なる話者を識別できます。

## 2. 機能

*   **音声文字起こし**: 音声コンテンツを書き言葉のテキストに変換します。
*   **話者ダイアライゼーション**: 音声中の異なる話者を識別し、ラベル付けします。
*   **フォーマット変換**: FFmpeg を利用して、様々な音声入力フォーマットを WAV に変換することで対応します。
*   **カスタマイズ可能なモデル**: 文字起こし用に異なる Whisper モデルを選択できます。
*   **言語指定**: 様々な言語での文字起こしをサポートします。
*   **柔軟な出力**: 文字起こし結果を指定されたファイルまたは標準出力に出力します。

## 3. 依存関係

### Python ライブラリ

*   **whisper**: 音声文字起こし用。
*   **pyannote.audio**: 話者ダイアライゼーション用。
*   **pydub**: 音声操作および変換用。
*   **torch**: whisper と pyannote.audio の両方で必要。
*   **torchaudio**: pyannote.audio で必要。
*   **typer**: コマンドラインインターフェース作成用。
*   **pyyaml**: 設定読み込み用 (`config.yaml` は `transcribe.py` で直接使用されませんが、`pyannote` によって間接的に使用されます)。

### 外部ツール

*   **FFmpeg**: 音声フォーマットを WAV に変換するために必要です。システムにインストールされ、システムの PATH でアクセス可能である必要があります。

### 設定ファイル

*   `transcribe.py` 自体は `config.yaml` を直接使用しませんが、`pyannote.audio` は独自のキャッシュメカニズムを介して管理される可能性のある独自の設定ファイルに依存しています。Hugging Face のアセットはキャッシュされることが想定されています。

## 4. セットアップとインストール

*   **Python 依存関係**: 必要な Python ライブラリを pip を使用してインストールします:
    ```bash
    pip install whisper pyannote.audio pydub torch torchaudio typer pyyaml
    ```
*   **FFmpeg**: FFmpeg がシステムにインストールされており、その実行可能ファイルがシステムの PATH 環境変数に含まれていることを確認してください。
*   **Hugging Face アセット**: `pyannote.audio` と `whisper` は、Hugging Face Hub からモデルやその他のアセットをダウンロードします。スクリプトは `HUGGINGFACE_HUB_CACHE` を `./tmp/assets` に設定するため、これらのアセットはそこにダウンロードされ、期待されます。

## 5. 使用方法

スクリプトはコマンドラインから実行します:

```bash
python transcribe.py [OPTIONS] FILE
```

### コマンドライン引数

*   **`FILE`** (必須): 文字起こしする音声ファイルのパス。
*   **`--model`** (オプション): 文字起こしに使用する Whisper モデル (例: `tiny`, `base`, `small`, `medium`, `large`)。デフォルトは `base` です。
*   **`--language`** (オプション): 音声の言語。指定しない場合、Whisper は言語を自動検出します。(例: `en`, `es`, `fr`)。
*   **`--diarize`** (オプション): 話者ダイアライゼーションを有効または無効にするブール値フラグ (true/false)。デフォルトは `false` です。
*   **`--output_file`** (オプション): 文字起こし出力を保存するファイルへのパス。指定しない場合、出力は標準出力に表示されます。
*   **`--output_dir`** (オプション): 出力ファイルを保存するディレクトリ。`output_file` がフルパスの場合、これは無視されます。デフォルトはカレントディレクトリです。
*   **`--debug`** (オプション): より詳細な出力を表示する可能性があるデバッグモードを有効または無効にするブール値フラグ (true/false)。デフォルトは `false` です。

## 6. コアコンポーネント (クラス)

### `Config` クラス

*   **役割**: 主に Typer を使用してコマンドライン引数を解析することにより、スクリプトの設定を管理します。モデル名、言語、ダイアライゼーション設定、入出力パス、デバッグモードなどの設定を保持します。

### `AudioProcessor` クラス

*   **役割**: すべての音声関連操作を処理します。
*   **主なメソッド/責務**:
    *   `load_model()`: 指定された Whisper モデルをロードします。
    *   `_ensure_wav_format()`: 入力音声ファイルが WAV ファイルでない場合、FFmpeg を使用して WAV 形式に変換します。処理用の一時 WAV ファイルを作成します。
    *   `_load_audio()`: (潜在的に一時的な) WAV 音声ファイルを文字起こし用にロードします。
    *   `transcribe_audio()`: ロードされた Whisper モデルを使用して実際の文字起こしを実行します。
    *   `diarize_audio()`: `pyannote.audio` を使用して話者ダイアライゼーションを実行します。これには、ダイアライゼーションパイプラインをロードし、音声を処理して話者セグメントを取得することが含まれます。
    *   `cleanup_temp_files()`: 処理中に作成された一時 WAV ファイルを削除します。

### `Transcriber` クラス

*   **役割**: 全体的な文字起こしとダイアライゼーションのプロセスを調整します。
*   **主なメソッド/責務**:
    *   `Config` オブジェクトで初期化します。
    *   `AudioProcessor` インスタンスを作成します。
    *   `_check_dependencies()`: FFmpeg がインストールされ、アクセス可能であることを確認します。
    *   `run()`: 文字起こしワークフローを実行するメインメソッド。依存関係チェック、モデルのロード、音声処理、文字起こし、およびオプションでダイアライゼーションのメソッドを呼び出します。その後、出力をフォーマットして保存 (または表示) します。
    *   ダイアライゼーションが有効な場合、文字起こし結果とダイアライゼーションセグメントを組み合わせるロジックを処理します。

## 7. ワークフロー

1.  **引数解析**: スクリプトは、`Config` クラスと Typer を使用してコマンドライン引数を解析することから始まります。
2.  **依存関係チェック**: `Transcriber` は FFmpeg がインストールされていることを確認します。
3.  **モデルのロード**: `AudioProcessor` は指定された Whisper 文字起こしモデルをロードします。ダイアライゼーションが有効な場合、`diarize_audio` が呼び出されると、関連する `pyannote.audio` モデルがロードされます。
4.  **音声処理**:
    *   必要に応じて、入力音声ファイルが WAV 形式に変換されます (一時 WAV ファイルが作成される場合があります)。
    *   WAV 音声がロードされます。
5.  **文字起こし**:
    *   `AudioProcessor` は Whisper モデルを使用して音声を文字起こしします。
    *   ダイアライゼーション (`--diarize`) が有効な場合:
        *   `AudioProcessor` は話者ダイアライゼーションを実行して、タイムスタンプ付きの話者セグメントを取得します。
        *   `Transcriber` はその後、文字起こし結果を話者セグメントと照合し、話者ラベルとタイムスタンプを出力に追加します。
    *   ダイアライゼーションが無効な場合、出力はプレーンテキストの文字起こしです。
6.  **出力保存**: 最終的な文字起こし (話者ラベルの有無にかかわらず) は、指定された出力ファイルに保存されるか、標準出力に表示されます。
7.  **クリーンアップ**: 一時ファイル (例: 一時 WAV ファイル) は削除されます。

## 8. 入力

*   **主な入力**: 単一の音声ファイル。
*   **サポートされる音声フォーマット**: FFmpeg が読み取り、WAV に変換できるすべての音声フォーマット。これには、MP3, M4A, FLAC, OGG などの一般的なフォーマットが含まれます。

## 9. 出力

*   **フォーマット**:
    *   **ダイアライゼーションなし**: 音声のプレーンテキスト文字起こし。
    *   **ダイアライゼーションあり**: 各セグメントが話者ラベル (例: `[SPEAKER_00]`) と話者の発話の開始と終了を示すタイムスタンプ (例: `[00:00:01.234 --> 00:00:05.678]`) で始まるテキスト文字起こし。
        ダイアライゼーションありの例:
        ```
        [SPEAKER_00] [00:00:00.500 --> 00:00:03.200] こんにちは、こちらは話者1です。
        [SPEAKER_01] [00:00:03.500 --> 00:00:05.800] そして、こちらは話者2です。
        ```
*   **場所**:
    *   `--output_file` が指定されている場合、文字起こしはそのファイルに保存されます。`--output_file` がファイル名のみの場合、`--output_dir` 引数を使用してこのファイルのディレクトリを指定できます。
    *   `--output_file` が指定されていない場合、文字起こしは標準出力に表示されます。
```
