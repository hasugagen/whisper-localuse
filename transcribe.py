#!/usr/bin/env python3
"""
Whisperを使用した音声文字起こしスクリプト (m4a形式対応版) - 最適化版
"""

import os
import pathlib
import argparse
import sys
from datetime import datetime
import logging
import tempfile
from typing import List, Dict, Optional
import subprocess
import numpy as np
from pydub import AudioSegment

# 依存ライブラリのインポート
try:
    import whisper
    from pyannote.audio import Pipeline
except ImportError as e:
    print(f"エラー: 必要なライブラリがインストールされていません: {e}")
    print("pip install whisper pyannote.audio pydub soundfile numpy")
    sys.exit(1)

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def setup_encoding():
    """文字コード設定を行う"""
    # 環境変数の設定
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    os.environ["PYTHONUTF8"] = "1"
    os.environ['HUGGINGFACE_HUB_CACHE'] = str(pathlib.Path("./tmp/assets").absolute())
    
    # # Windows環境での文字コード対応
    # if sys.platform.startswith('win'):
    #     try:
    #         import ctypes
    #         if hasattr(ctypes, 'windll') and hasattr(ctypes.windll, 'kernel32'):
    #             ctypes.windll.kernel32.SetConsoleCP(65001)
    #             ctypes.windll.kernel32.SetConsoleOutputCP(65001)
    #             logger.info("コンソールの文字コードをUTF-8に設定しました")
    #     except Exception as e:
    #         logger.warning(f"コンソールの文字コード設定に失敗しました: {e}")
    
    # # Python 3.7+ で標準入出力のエンコーディングをUTF-8に設定
    # if sys.version_info >= (3, 7):
    #     sys.stdout.reconfigure(encoding='utf-8')
    #     sys.stderr.reconfigure(encoding='utf-8')

class Config:
    """アプリケーションの設定を管理するクラス"""
    
    def __init__(self):
        self.models = ["tiny", "base", "small", "medium", "large"]
        self.default_model = "base"
        self.output_dir = "output"
        self.config_file = "./tmp/assets/config.yaml"  # 話者分離用設定ファイル
        
    def get_available_models(self) -> List[str]:
        """利用可能なモデルの一覧を返す"""
        return self.models

class AudioProcessor:
    """音声ファイルの処理を担当するクラス"""
    
    def __init__(self, config: Config):
        self.config = config
        self.model = None
        self.pipeline = None
        self._temp_files = []  # 一時ファイル管理用
        
    def load_model(self, model_name: str) -> bool:
        """Whisperモデルを読み込む"""
        try:
            self.model = whisper.load_model(model_name)
            return True
        except Exception as e:
            logger.error(f"モデルの読み込みに失敗しました: {e}")
            return False
            
    def load_diarization_pipeline(self, config_file: str = "./tmp/assets/config.yaml") -> bool:
        """話者分離パイプラインを読み込む"""
        try:
            pipeline = Pipeline.from_pretrained(config_file)
            self.pipeline = pipeline
            return True
        except Exception as e:
            logger.error(f"話者分離パイプラインの読み込みに失敗しました: {e}")
            return False
    
    def convert_to_wav(self, file_path: str) -> str:
        """音声ファイルをWAV形式に変換する"""
        file_ext = os.path.splitext(file_path)[1].lower()
        
        # wavファイルならそのまま返す
        if file_ext == '.wav':
            return file_path
            
        # 一時ファイルを作成
        temp_wav = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        temp_wav_path = temp_wav.name
        temp_wav.close()
        self._temp_files.append(temp_wav_path)
        
        logger.info(f"ファイル形式 {file_ext} を WAV に変換しています...")
        
        try:
            # FFmpegを使用して変換
            cmd = [
                "ffmpeg", "-y", "-i", file_path,
                "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le",
                temp_wav_path
            ]
            
            subprocess.run(cmd, capture_output=True, check=True)
            logger.info(f"WAV変換が完了しました: {temp_wav_path}")
            return temp_wav_path
            
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpegでの変換に失敗しました")
            return file_path
        except Exception as e:
            logger.error(f"ファイル変換中にエラーが発生しました: {e}")
            return file_path
    
    def load_audio_data(self, wav_path: str) -> np.ndarray:
        """音声データを読み込む（共通処理）"""
        try:
            audio = whisper.load_audio(wav_path)
            logger.info("whisper.load_audioでの読み込みが完了しました")
            return audio
        except Exception as e:
            logger.error(f"whisper.load_audioでの読み込みに失敗しました: {e}")
            logger.info("AudioSegment.from_fileによる読み込みを試みます...")
            
            # 代替手段としてpydubを使用
            audio_segment = AudioSegment.from_file(wav_path)
            audio = np.array(audio_segment.get_array_of_samples()).astype(np.float32) / 32768.0
            logger.info("AudioSegmentでの読み込みが完了しました")
            return audio
            
    def transcribe(self, file_path: str, language: Optional[str] = None) -> str:
        """音声ファイルを文字起こしする"""
        try:
            logger.info(f"音声ファイル '{file_path}' の処理を開始します...")
            
            # 音声ファイルをWAV形式に変換（必要な場合）
            wav_path = self.convert_to_wav(file_path)
            
            # 音声データを読み込む
            logger.info(f"音声ファイル '{wav_path}' の読み込みを開始します...")
            audio = self.load_audio_data(wav_path)
            
            logger.info("文字起こしを開始します...")
            result = self.model.transcribe(
                audio=audio,
                language=language,
                fp16=False
            )
            logger.info("文字起こしが完了しました")
            
            return result.get("text", "")
        except Exception as e:
            logger.error(f"文字起こしに失敗しました: {e}")
            return ""
            
    def diarize_speakers(self, audio_path: str) -> List[Dict]:
        """音声ファイルから話者分離を行う"""
        try:
            logger.info("話者分離パイプラインの読み込みを開始します...")
            if not self.pipeline:
                if not self.load_diarization_pipeline():
                    logger.error("話者分離パイプラインの読み込みに失敗しました")
                    return []
            logger.info("話者分離パイプラインの読み込みが完了しました")
            
            # 音声ファイルをWAV形式に変換（必要な場合）
            wav_path = self.convert_to_wav(audio_path)
            
            logger.info("話者分離の実行を開始します...")
            diarization = self.pipeline(wav_path)
            logger.info("話者分離の実行が完了しました")
            
            logger.info("話者セグメントの処理を開始します...")
            segments = []
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                start_ms = int(turn.start * 1000)
                end_ms = int(turn.end * 1000)
                segments.append({
                    'start': start_ms,
                    'end': end_ms,
                    'speaker': speaker
                })
            logger.info(f"話者セグメントの処理が完了しました。検出された話者数: {len(set(seg['speaker'] for seg in segments))}")
            
            return segments
        except Exception as e:
            logger.error(f"話者分離に失敗しました: {e}")
            return []
    
    def cleanup_temp_files(self):
        """一時ファイルをクリーンアップ"""
        for temp_file in self._temp_files:
            if os.path.exists(temp_file):
                try:
                    os.unlink(temp_file)
                    logger.info(f"一時ファイル {temp_file} を削除しました")
                except Exception as e:
                    logger.warning(f"一時ファイルの削除に失敗しました: {e}")
        self._temp_files.clear()

class Transcriber:
    """文字起こし処理を管理するクラス"""
    
    def __init__(self, config: Config):
        self.config = config
        self.audio_processor = AudioProcessor(config)
        
    def transcribe_audio(
        self,
        file_path: str,
        model_name: str = "base",
        language: Optional[str] = None,
        diarize: bool = False
    ) -> str:
        """音声ファイルを文字起こしする"""
        try:
            logger.info(f"モデル '{model_name}' の読み込みを開始します...")
            if not self.audio_processor.load_model(model_name):
                logger.error(f"モデル '{model_name}' の読み込みに失敗しました")
                return ""
            logger.info(f"モデル '{model_name}' の読み込みが完了しました")
                
            if diarize:
                return self._transcribe_with_diarization(file_path, language)
            else:
                logger.info("通常の文字起こしを開始します...")
                transcription_text = self.audio_processor.transcribe(file_path, language)
                logger.info("通常の文字起こしが完了しました")
                return transcription_text
                
        except Exception as e:
            logger.error(f"文字起こし処理中にエラーが発生しました: {e}", exc_info=True)
            return ""
        finally:
            # 一時ファイルのクリーンアップ
            self.audio_processor.cleanup_temp_files()
    
    def _transcribe_with_diarization(self, file_path: str, language: Optional[str]) -> str:
        """話者分離付き文字起こしを実行"""
        logger.info("話者分離を開始します...")
        speaker_segments = self.audio_processor.diarize_speakers(file_path)
        logger.info("話者分離が完了しました")
        
        if not speaker_segments:
            logger.warning("話者分離に失敗したため、通常の文字起こしにフォールバックします")
            return self.audio_processor.transcribe(file_path, language)
        
        # 音声ファイルをWAV形式に変換（必要な場合）
        wav_path = self.audio_processor.convert_to_wav(file_path)
        
        # 音声データを読み込む
        logger.info(f"音声ファイル '{wav_path}' の読み込みを開始します...")
        audio = self.audio_processor.load_audio_data(wav_path)
        
        logger.info("話者別の文字起こしを開始します...")
        results = []
        
        # 各話者のセグメントについて文字起こしを実行
        for i, segment_info in enumerate(speaker_segments, 1):
            start_time_ms = segment_info['start']
            end_time_ms = segment_info['end']
            speaker = segment_info['speaker']
            
            # セグメントの開始・終了時間をサンプル数に変換
            start_sample = int(start_time_ms * 16)  # 16kHzなので1msあたり16サンプル
            end_sample = int(end_time_ms * 16)
            
            # 音声データのセグメントを切り出し
            if start_sample < len(audio) and end_sample <= len(audio):
                segment_audio = audio[start_sample:end_sample]
            else:
                logger.warning(f"セグメント範囲が音声データの範囲外です: {start_sample}:{end_sample}, len={len(audio)}")
                continue
            
            # セグメントが短すぎる場合はスキップ
            if len(segment_audio) < 1600:  # 100ms未満はスキップ
                logger.info(f"セグメント {i} は短すぎるためスキップします（{len(segment_audio)} サンプル）")
                continue
            
            # 文字起こし実行
            logger.info(f"話者 {speaker} のセグメント {i}/{len(speaker_segments)} の文字起こしを開始します...")
            try:
                transcription_result = self.audio_processor.model.transcribe(
                    segment_audio,
                    language=language,
                    verbose=None,
                    fp16=False
                )
                logger.info(f"話者 {speaker} のセグメント {i}/{len(speaker_segments)} の文字起こしが完了しました")
                
                # 結果を追加
                text = transcription_result['text'].strip()
                if text:
                    results.append({
                        'speaker': speaker,
                        'start_s': start_time_ms / 1000.0,
                        'end_s': end_time_ms / 1000.0,
                        'text': text
                    })
            except Exception as e:
                logger.error(f"セグメント {i} の文字起こしに失敗しました: {e}")
        
        logger.info("話者別の文字起こしが完了しました")
        
        # 結果が空の場合は通常の文字起こしにフォールバック
        if not results:
            logger.warning("話者別文字起こしの結果が空のため、通常の文字起こしにフォールバックします")
            return self.audio_processor.transcribe(file_path, language)
        
        # 結果を開始時間でソート
        results.sort(key=lambda x: x['start_s'])
        
        # 結果を整形して返す
        return "\n".join(
            f"話者 {r['speaker']} [{r['start_s']:.2f}s - {r['end_s']:.2f}s]: {r['text']}"
            for r in results
        )

def check_ffmpeg() -> bool:
    """FFmpegの存在を確認する"""
    try:
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        logger.info("FFmpegが正常に動作します")
        # FFmpegのバージョン情報を表示
        version_line = result.stdout.split(b'\n')[0].decode('utf-8', errors='ignore') if result.stdout else "バージョン情報なし"
        logger.info(f"FFmpeg version: {version_line}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpegの実行に失敗しました: {e}")
        return False
    except Exception as e:
        logger.error(f"FFmpegの確認中にエラーが発生しました: {e}")
        return False

def check_dependencies() -> bool:
    """依存ライブラリの確認"""
    try:
        dependencies = [
            ("pydub", "音声ファイルの読み込みと処理"),
            ("whisper", "音声文字起こし"),
            ("pyannote.audio", "話者分離")
        ]
        
        missing = []
        for package, purpose in dependencies:
            try:
                __import__(package)
                logger.info(f"{package} がインストールされています")
            except ImportError:
                missing.append(f"{package} ({purpose})")
        
        if missing:
            logger.error(f"以下のライブラリがインストールされていません: {', '.join(missing)}")
            logger.error("pip install whisper pyannote.audio pydub soundfile numpy コマンドを実行してください")
            return False
        
        return True
    except Exception as e:
        logger.error(f"依存関係の確認中にエラーが発生しました: {e}")
        return False

def save_transcription(text: str, output_file: str, output_dir: str) -> bool:
    """文字起こし結果をファイルに保存する"""
    try:
        if output_file:
            output_dir_for_file = os.path.dirname(output_file)
            if output_dir_for_file and not os.path.exists(output_dir_for_file):
                os.makedirs(output_dir_for_file, exist_ok=True)
        else:
            os.makedirs(output_dir, exist_ok=True)
            
        # UTF-8で書き込み、エラー時はシステムデフォルトエンコーディングを使用
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(text)
        except UnicodeEncodeError:
            with open(output_file, 'w', encoding=sys.getdefaultencoding(), errors='replace') as f:
                f.write(text)
                
        logger.info(f"結果が {output_file} に保存されました")
        return True
    except Exception as e:
        logger.error(f"結果の保存に失敗しました: {e}")
        return False

def main():
    """メイン関数"""
    # 文字コード設定の初期化
    setup_encoding()
    
    # 設定のロード
    config = Config()
    
    parser = argparse.ArgumentParser(description='Whisperを使用した音声文字起こしツール (m4a対応版)')
    parser.add_argument('file', type=str, help='文字起こしする音声ファイルのパス')
    parser.add_argument(
        '--model',
        type=str,
        default=config.default_model,
        choices=config.get_available_models(),
        help=f'使用するモデル (デフォルト: {config.default_model}, 利用可能: {", ".join(config.get_available_models())})'
    )
    parser.add_argument(
        '--language',
        type=str,
        default=None,
        help='音声の言語コード (例: ja, en, zh)。指定しない場合は自動検出。'
    )
    parser.add_argument(
        '--diarize',
        action='store_true',
        help='話者分離を有効にする (ローカルの話者分離モデルが必要です)'
    )
    parser.add_argument(
        '--output_file',
        type=str,
        default=None,
        help='結果を保存するファイルパス。指定しない場合はoutput_dirに保存。'
    )
    parser.add_argument(
        '--output_dir',
        type=str,
        default=config.output_dir,
        help=f'出力ディレクトリ (デフォルト: {config.output_dir}/)'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='デバッグモードを有効にする（詳細なログ出力）'
    )
    
    args = parser.parse_args()
    
    # デバッグモードが有効な場合はログレベルを変更
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logger.debug("デバッグモードが有効です")
    
    # ファイルの存在確認
    if not os.path.exists(args.file):
        logger.error(f"ファイル '{args.file}' が見つかりません")
        sys.exit(1)
    
    # 依存関係の確認
    if not check_dependencies():
        logger.error("必要な依存関係が満たされていません")
        sys.exit(1)
    
    # FFmpegの確認
    if not check_ffmpeg():
        logger.error("FFmpegが利用できません。インストールまたはパスの設定を確認してください。")
        sys.exit(1)
    
    # トランスクライバーの作成
    transcriber = Transcriber(config)
    
    # 文字起こしの実行
    transcription_text = transcriber.transcribe_audio(
        file_path=args.file,
        model_name=args.model,
        language=args.language,
        diarize=args.diarize
    )
    
    # 結果の処理
    if transcription_text:
        if args.output_file:
            # 指定されたファイルに保存
            if save_transcription(transcription_text, args.output_file, args.output_dir):
                logger.info(f"文字起こし結果が {args.output_file} に保存されました")
                print(f"文字起こし結果が {args.output_file} に保存されました")
            else:
                # 保存に失敗した場合は標準出力に表示
                print("文字起こし結果:")
                print(transcription_text)
        else:
            # デフォルトのファイル名で保存
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            base_filename = os.path.splitext(os.path.basename(args.file))[0]
            output_file = os.path.join(args.output_dir, f'{base_filename}_transcript_{timestamp}.txt')
            if save_transcription(transcription_text, output_file, args.output_dir):
                logger.info(f"文字起こし結果が {output_file} に保存されました")
                print(f"文字起こし結果が {output_file} に保存されました")
            else:
                # 保存に失敗した場合は標準出力に表示
                print("文字起こし結果:")
                print(transcription_text)
    else:
        logger.error("文字起こし結果が空です")
        print("エラー: 文字起こし結果が空です。ログを確認してください。")
        sys.exit(1)

if __name__ == "__main__":
    main()
