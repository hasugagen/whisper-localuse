# Whisper ローカル文字起こしツール

このツールは、OpenAIのWhisperを使用して音声ファイルを文字起こしするためのPythonスクリプトです。話者分離機能も含まれており、複数人の会話の文字起こしにも対応しています。このアプリケーションにおいては、Whisperモデルをローカルで動作させるよう設計されています。そのため、HuggingFaceのトークンは不要です。

## セットアップ

### 1\. 必要なソフトウェアのインストール

#### a. Python

Python 3.8以上をインストールしてください。
[Python公式サイト](https://www.python.org/downloads/)からダウンロードできます。

#### b. FFmpeg

このツールは音声ファイルの処理にFFmpegを使用します。

  - Windowsの場合：
    1.  [FFmpeg公式サイト](https://ffmpeg.org/download.html)からWindows用のビルドをダウンロードしてください。
    2.  ダウンロード後、展開したフォルダ内の `bin` ディレクトリ（例: `C:\ffmpeg\bin`）にシステムの環境変数PATHを通してください。

    - winget を利用する場合は、以下のコマンドを実行してください。
    ```bash
    winget install Gyan.FFmpeg
    ```
    この場合、Pathを通す必要はありません。
    

### 2\. 仮想環境の作成と有効化

プロジェクトのルートディレクトリで以下のコマンドを実行し、仮想環境を作成して有効化します。

```bash
# 仮想環境の作成
python -m venv .venv

# 仮想環境の有効化
# Windowsの場合
.venv\Scripts\activate
# macOS/Linuxの場合
# source venv/bin/activate
```

作業が終了したら、以下のコマンドで仮想環境を無効化できます。

```bash
# deactivate
```

### 3\. 依存パッケージのインストール

作成した仮想環境内で、以下のコマンドを実行して必要なPythonパッケージをインストールします。

```bash
pip install -r requirements.txt
```

## 利用可能なWhisperモデル

以下のモデルが利用可能です。モデルサイズが大きいほど精度が向上しますが、処理時間と必要なリソースも増加します。

  - **tiny**: 最も軽量なモデル（処理速度は速いが精度は低い）
  - **base**: バランスの取れたデフォルトモデル
  - **small**: `base`より高精度（より多くのリソースが必要）
  - **medium**: 高精度モデル（多くのリソースが必要）
  - **large**: 最高精度モデル（最大のリソースが必要）

## 基本的な使い方

ツールのヘルプは以下のコマンドで確認できます。

```bash
python transcribe.py --help
```

### 主なオプション

  - `--file <ファイルパス>`: (必須) 処理する音声ファイルのパスを指定します。
  - `--model <モデル名>`: 使用するWhisperモデルを指定します。デフォルトは `"base"` です。（利用可能なモデルは上記参照）
  - `--language <言語コード>`: 文字起こしする言語のコード（例: `"ja"` で日本語）を指定します。指定しない場合は自動検出されます。
  - `--diarize`: 話者分離機能を有効にします。このオプションを指定しない場合、話者分離は行われません。

### サンプルコマンド

以下のコマンドは、`sample`ディレクトリ内の音声ファイル `サンプル会議音声１.wav` を、`small`モデルを使用して日本語で文字起こしし、話者分離を実行する例です。

```bash
python transcribe.py ./sample/サンプル会議音声１.wav --model small --language ja --diarize
```

## オフライン環境での利用

このツールは、インターネット接続がないオフライン環境でも動作するように設計されています。
オフラインで利用するためには、事前に必要なモデルファイルをダウンロードし、指定の場所に配置する必要があります。

### 1\. 必要なモデルファイルの準備と配置

以下のモデルファイルを事前にダウンロードし、プロジェクト内の `./tmp/assets/` ディレクトリに指定の構造で配置してください。

  - **Whisperモデル**:
      * 通常、初回実行時に自動的にダウンロードされ、`./tmp/assets/whisper/` にキャッシュされます。オフライン環境では、このキャッシュされたモデルファイル群（例: `small.pt` など、使用したいモデルのもの）を事前にここに配置します。
  - **話者分離関連ファイル** (話者分離機能 `--diarize` を使用する場合に必要):
      * **話者分離モデル設定ファイル**: `config.yaml`
      * **話者分離モデル本体**: `pytorch_model.bin`
      * これらを `./tmp/assets/` 直下に配置します。
  - **SpeechBrain 話者認識モデル** (話者分離機能で使用):
      * HuggingFace Hubの `speechbrain/spkrec-ecapa-voxceleb` からダウンロードされるファイル群です。
      * `models--speechbrain--spkrec-ecapa-voxceleb` というディレクトリ名で、このディレクトリごと `./tmp/assets/` 配下に配置します。 (つまり `./tmp/assets/models--speechbrain--spkrec-ecapa-voxceleb/`)

**期待されるディレクトリ構造の例:**

```
your_project_root/
├── transcribe.py
├── requirements.txt
└── tmp/
    └── assets/
        ├── config.yaml
        ├── pytorch_model.bin
        ├── whisper/
        │   └── (例: small.pt などWhisperモデルファイル)
        └── models--speechbrain--spkrec-ecapa-voxceleb/
            └── (SpeechBrainモデルファイル群)
```

### 2\. `config.yaml` の設定確認 (話者分離利用時)

話者分離機能を使用する場合、`./tmp/assets/config.yaml` の内容が、ローカルに配置したモデルファイルを指すように設定されているか確認してください。特に `segmentation` のパスが重要です。

```yaml
pipeline:
  name: pyannote.audio.pipelines.SpeakerDiarization
  params:
    clustering: AgglomerativeClustering
    embedding: speechbrain/spkrec-ecapa-voxceleb  # 通常はこのままでローカルキャッシュを参照
    segmentation: ./tmp/assets/pytorch_model.bin # ローカルのモデルファイルを指すように
    # embedding_batch_size: 32 # 必要に応じて調整
    # segmentation_batch_size: 32 # 必要に応じて調整
```

### 3\. 環境変数の設定 (HuggingFaceキャッシュの参照先変更)

HuggingFace Transformersや関連ライブラリがモデルをキャッシュするデフォルトの場所ではなく、プロジェクト内の `./tmp/assets/` を参照するように環境変数を設定します。

```bash
# Windows (コマンドプロンプト)
set HUGGINGFACE_HUB_CACHE=./tmp/assets
set HF_HOME=./tmp/assets
set WHISPER_CACHE_DIR=./tmp/assets/whisper

# Windows (PowerShell)
$env:HUGGINGFACE_HUB_CACHE = "./tmp/assets"
$env:HF_HOME = "./tmp/assets"
$env:WHISPER_CACHE_DIR = "./tmp/assets/whisper"

# Linux/macOS
export HUGGINGFACE_HUB_CACHE=./tmp/assets
export HF_HOME=./tmp/assets
export WHISPER_CACHE_DIR=./tmp/assets/whisper
```

### 4\. オフラインでの実行

上記設定後、通常通りスクリプトを実行します。

```bash
python transcribe.py <音声ファイルパス> --model <モデル名> --language <言語コード> --diarize
```

### 注意事項 (オフライン利用時)

  - オフライン環境ではモデルの自動ダウンロードは行われません。必要なモデルファイルはすべて事前にダウンロードし、正しい場所に配置する必要があります。
  - 指定されたパスにモデルファイルが存在しない、または破損している場合はエラーが発生します。

## 実行ファイル（.exe）の作成 (Windows向け)

PyInstallerを使用して、このPythonスクリプトを単一の実行可能ファイル（`.exe`）にバンドルできます。

### 1\. PyInstallerのインストール

仮想環境で以下のコマンドを実行してPyInstallerをインストールします。

```bash
pip install pyinstaller
```

### 2\. `.spec` ファイルの作成

以下のコマンドを実行して、ビルド設定ファイル（`.spec`ファイル）を生成します。

```bash
pyi-makespec --onefile --name=transcriber transcribe.py
```

*(注: このツールはコマンドラインインターフェース(CUI)のため、`--windowed` オプションは通常不要です。)*

### 3\. `.spec` ファイルの編集

生成された `transcriber.spec` ファイルを開き、実行ファイルに必要なデータファイル（モデルファイルなど）と、隠れたインポート（PyInstallerが自動検出できないモジュール）を指定します。

```python
# transcriber.spec

block_cipher = None

analysis = Analysis(
    ['transcribe.py'],
    pathex=[],
    binaries=[],
    datas=[],  # ここを修正
    hiddenimports=[],  # ここを修正
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# 必要なデータファイル（モデルファイルなど）を追加
# (実行ファイル内でのパス, 元のファイル/フォルダのパス)
added_datas = [
    ('./tmp/assets', './tmp/assets'),  # Whisperモデル、話者分離モデル、設定ファイルなど
]
analysis.datas.extend(added_datas)

# 必要な隠しインポートを追加
added_hiddenimports = [
    'whisper', 'torch', 'torchaudio', 'numpy', 'pandas', # 基本的なライブラリ
    'pyannote.audio', 'speechbrain', # 話者分離関連
    'soundfile', # 音声ファイル読み込みで whisper が内部的に使うことがある
    # その他、実行時に 'ModuleNotFound' エラーが出るモジュールがあれば追加
    # 元のREADMEに 'ffmpeg' がありましたが、ffmpeg-pythonラッパーを使用している場合に追加します。
    # FFmpeg本体は別途インストールが必要です。
]
analysis.hiddenimports.extend(added_hiddenimports)

pyz = PYZ(analysis.pure, analysis.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name='transcriber', # 出力されるexeファイル名
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True, # UPXで圧縮する場合 (UPXがインストールされている必要あり)
    console=True, # CUIアプリケーションなのでTrue
    runtime_tmpdir=None,
)
# --onefile の場合、COLLECTセクションは直接的な影響は少ないが、datasの処理のために記述を維持
coll = COLLECT(
    exe,
    analysis.binaries,
    analysis.zipfiles,
    analysis.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='transcriber_bundle', # --onedir の場合に出力されるフォルダ名
)
```

### 4\. 実行ファイルのビルド

編集した `.spec` ファイルを使用して、以下のコマンドで実行ファイルをビルドします。

```bash
pyinstaller transcriber.spec
```

### 5\. 実行ファイルの確認と使い方

ビルドが完了すると、`dist`フォルダ内に `transcriber.exe` が生成されます。この実行ファイルは、元のPythonスクリプトと同様にコマンドライン引数を受け付けます。

```bash
# distフォルダに移動してから実行する例
cd dist
transcriber.exe ../sample/サンプル会議音声１.wav --model small --language ja --diarize
```

### 6\. 配布時の注意

  - **モデルファイルのバンドル**: 上記 `.spec` ファイルの `datas` 設定により、`./tmp/assets` 内のモデルファイル群が `.exe` にバンドルされます。これにより、実行ファイル単体で（または指定されたフォルダ構造で）モデルファイルも一緒に配布できます。
  - **FFmpegの必要性**: **FFmpeg本体は `.exe` にはバンドルされません。** 実行ファイルを使用するユーザーの環境にも、FFmpegが別途インストールされ、PATHが通っている必要があります。
  - **初回実行**: モデルファイルを正しくバンドルした場合、初回実行時にオンラインからのモデルダウンロードは発生しません。

### 7\. トラブルシューティング (PyInstaller)

  - ビルドエラーや実行時エラー（例: `ModuleNotFoundError`）が発生した場合、`.spec` ファイルの `hiddenimports` に不足しているモジュールがないか確認してください。
  - `--log-level=DEBUG` (元のREADMEの記述) や `pyinstaller --debug=all transcriber.spec` のようにデバッグオプションを付けてビルドすると、詳細なログが出力され、問題解決の手がかりになることがあります。
  - モデルファイルなど、データファイルが見つからないエラーが発生する場合は、`.spec` ファイルの `datas` セクションのパス指定が正しいか確認してください。

## エラーハンドリングと一般的な注意事項

### エラーハンドリング

  - **Pythonパッケージの不足**: `requirements.txt` に記載されたパッケージが不足している場合、`ModuleNotFoundError` が発生します。セットアップ手順に従い、パッケージをインストールしてください。
  - **FFmpegの未検出**: FFmpegがインストールされていないかPATHが通っていない場合、音声処理時にエラーが発生します。FFmpegをインストールし、PATHを設定してください。
  - **話者分離モデル/設定ファイルの不備**: 話者分離機能利用時に `config.yaml` が見つからない、または内容に誤りがある場合、エラーが発生します。「オフライン環境での利用」セクションを参照し、ファイルを正しく配置・設定してください。

### 一般的な注意事項

  - **リソース**: 大きな音声ファイルや高精度モデル（`medium`, `large`）を使用する場合、十分なメモリとCPUが必要です。話者分離機能は追加のリソースと処理時間を要します。
  - **モデルファイルの場所**: 各種モデルは `./tmp/assets/` 以下に配置されることを前提としています。
  - **言語自動検出**: `--language` 未指定時の自動検出は、音声の冒頭部分に依存します。短い音声や多言語が混在する場合は、明示的に言語を指定することを推奨します。

