#!/usr/bin/env python3
"""
Whisperを使用した音声文字起こしスクリプト (ローカル環境向けリファクタリング版)
"""

import os
import pathlib
import argparse
import sys
from datetime import datetime
import logging
import json
from typing import List, Dict, Optional
import subprocess
import numpy as np
from pydub import AudioSegment

# 依存ライブラリのインポート (エラーハンドリングのためtry-exceptで囲むことを検討)
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

# 環境変数の設定
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ["PYTHONUTF8"] = "1"
os.environ['HUGGINGFACE_HUB_CACHE'] = str(pathlib.Path("./tmp/assets").absolute())

# Python 3.7+ で標準入出力のエンコーディングをUTF-8に設定
if sys.version_info >= (3, 7):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

class Config:
    """アプリケーションの設定を管理するクラス"""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file or "./tmp/assets/config.yaml"
        self.models = ["tiny", "base", "small", "medium", "large"]
        self.default_model = "base"
        self.output_dir = "output"
        
    def get_available_models(self) -> List[str]:
        """利用可能なモデルの一覧を返す"""
        return self.models

class AudioProcessor:
    """音声ファイルの処理を担当するクラス"""
    
    def __init__(self, config: Config):
        self.config = config
        self.model = None
        self.pipeline = None
        
    def load_model(self, model_name: str) -> bool:
        """Whisperモデルを読み込む"""
        try:
            self.model = whisper.load_model(model_name)
            return True
        except Exception as e:
            logger.error(f"モデルの読み込みに失敗しました: {e}")
            return False
            
    def load_diarization_pipeline(self) -> bool:
        """話者分離パイプラインを読み込む"""
        try:
            pipeline = Pipeline.from_pretrained(self.config.config_file)
            self.pipeline = pipeline
            return True
        except Exception as e:
            logger.error(f"話者分離パイプラインの読み込みに失敗しました: {e}")
            return False
            
    def transcribe(self, file_path: str, language: Optional[str] = None) -> str:
        """音声ファイルを文字起こしする"""
        try:
            logger.info(f"音声ファイル '{file_path}' の読み込みを開始します...")
            audio = AudioSegment.from_file(file_path)
            logger.info(f"音声ファイル '{file_path}' の読み込みが完了しました")
            
            # Whisperが期待する16kHzモノラルのオーディオに変換
            audio = audio.set_frame_rate(16000).set_channels(1)
            
            logger.info("文字起こしを開始します...")
            result = self.model.transcribe(
                audio=audio,  # whisperに直接オーディオデータを渡す
                language=language,
                fp16=False  # CPU使用時はFalse推奨
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
                    
            logger.info("話者分離の実行を開始します...")
            diarization = self.pipeline(audio_path)
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
            logger.info(f"話者セグメントの処理が完了しました。検出された話者数: {len(segments)}")
            return segments
        except Exception as e:
            logger.error(f"話者分離に失敗しました: {e}")
            return []

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
                logger.info("話者分離を開始します...")
                speaker_segments = self.audio_processor.diarize_speakers(file_path)
                logger.info("話者分離が完了しました")
                
                if not speaker_segments:
                    logger.warning("話者分離に失敗したため、通常の文字起こしにフォールバックします")
                    return self.audio_processor.transcribe(file_path, language)
                    
                # 音声ファイルを読み込み
                logger.info(f"音声ファイル '{file_path}' の読み込みを開始します...")
                audio = AudioSegment.from_file(file_path)
                logger.info(f"音声ファイル '{file_path}' の読み込みが完了しました")
                
                # Whisperが期待する16kHzモノラルのオーディオに変換
                audio = audio.set_frame_rate(16000).set_channels(1)
                
                logger.info("話者別の文字起こしを開始します...")
                results = []
                
                # 各話者のセグメントについて文字起こしを実行
                for i, segment_info in enumerate(speaker_segments, 1):
                    start_time_ms = segment_info['start']
                    end_time_ms = segment_info['end']
                    speaker = segment_info['speaker']
                    
                    # セグメントを切り出し
                    segment_audio = audio[start_time_ms:end_time_ms]
                    
                    # 文字起こし実行
                    logger.info(f"話者 {speaker} のセグメント {i}/{len(speaker_segments)} の文字起こしを開始します...")
                    transcription_result = self.audio_processor.model.transcribe(
                        np.array(segment_audio.get_array_of_samples()).astype(np.float32) / 32768.0,
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
                
                logger.info("話者別の文字起こしが完了しました")
                
                # 結果を整形して返す
                return "\n".join(
                    f"話者 {r['speaker']} [{r['start_s']:.2f}s - {r['end_s']:.2f}s]: {r['text']}"
                    for r in results
                )
                
            else:
                logger.info("通常の文字起こしを開始します...")
                transcription_text = self.audio_processor.transcribe(file_path, language)
                logger.info("通常の文字起こしが完了しました")
                return transcription_text
                
        except Exception as e:
            logger.error(f"文字起こし処理中にエラーが発生しました: {e}")
            return ""

def check_ffmpeg() -> bool:
    """FFmpegの存在を確認する"""
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True, text=True)
        logger.info("FFmpegが正常に動作します")
        return True
    except Exception as e:
        logger.error(f"FFmpegの確認に失敗しました: {e}")
        return False

def save_transcription(text: str, output_file: Optional[str], output_dir: str) -> bool:
    """文字起こし結果をファイルに保存する"""
    try:
        if output_file:
            output_dir_for_file = os.path.dirname(output_file)
            if output_dir_for_file and not os.path.exists(output_dir_for_file):
                os.makedirs(output_dir_for_file, exist_ok=True)
        else:
            os.makedirs(output_dir, exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            base_filename = os.path.splitext(os.path.basename(file))[0]
            output_file = os.path.join(output_dir, f'{base_filename}_transcript_{timestamp}.txt')
            
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(text)
            logger.info(f"結果が {output_file} に保存されました")
        return True
    except Exception as e:
        logger.error(f"結果の保存に失敗しました: {e}")
        return False

def main():
    """メイン関数"""
    config = Config()
    transcriber = Transcriber(config)
    
    parser = argparse.ArgumentParser(description='Whisperを使用した音声文字起こしツール (ローカル環境版)')
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
        help='結果を保存するファイルパス。指定しない場合は標準出力に表示。'
    )
    parser.add_argument(
        '--output_dir',
        type=str,
        default=config.output_dir,
        help=f'出力ディレクトリ (デフォルト: {config.output_dir}/)'
    )
    
    args = parser.parse_args()
    
    # FFmpegの確認
    if not check_ffmpeg():
        sys.exit(1)
    
    # 文字起こしの実行
    transcription_text = transcriber.transcribe_audio(
        file_path=args.file,
        model_name=args.model,
        language=args.language,
        diarize=args.diarize
    )
    
    # 結果の保存
    if transcription_text:
        if args.output_file:
            if save_transcription(transcription_text, args.output_file, args.output_dir):
                logger.info(f"文字起こし結果が {args.output_file} に保存されました")
        else:
            # デフォルトのファイル名で保存
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            base_filename = os.path.splitext(os.path.basename(args.file))[0]
            output_file = os.path.join(args.output_dir, f'{base_filename}_transcript_{timestamp}.txt')
            if save_transcription(transcription_text, output_file, args.output_dir):
                logger.info(f"文字起こし結果が {output_file} に保存されました")
    else:
        logger.error("文字起こし結果が空です")

if __name__ == "__main__":
    main()
