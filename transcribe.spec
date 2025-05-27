# -*- mode: python ; coding: utf-8 -*-

import os
import site
import sys
import glob
import importlib
import importlib.util

block_cipher = None

# --- ネームスペースパッケージを処理するためのヘルパー関数 ---
def get_namespace_package_paths(namespace):
    """ネームスペースパッケージの全てのパスを取得する"""
    paths = []
    
    # 全てのサイトパッケージディレクトリを調べる
    for site_dir in site.getsitepackages() + [site.getusersitepackages()]:
        namespace_dir = os.path.join(site_dir, namespace)
        if os.path.isdir(namespace_dir):
            paths.append(namespace_dir)
    
    return paths

def get_package_path(package_name):
    """指定されたパッケージの site-packages 内のパスを取得"""
    # ネームスペースパッケージの可能性をチェック
    if '.' in package_name:
        namespace = package_name.split('.')[0]
        sub_package = package_name[len(namespace)+1:]
        
        for namespace_path in get_namespace_package_paths(namespace):
            potential_path = os.path.join(namespace_path, sub_package)
            if os.path.isdir(potential_path):
                return potential_path
        
        # pyannote.audio のような特殊な形式をチェック
        spec = importlib.util.find_spec(package_name)
        if spec and spec.submodule_search_locations:
            for loc in spec.submodule_search_locations:
                if os.path.isdir(loc):
                    return loc
        
        # インポートして __path__ を直接確認する方法も試す
        try:
            module = importlib.import_module(package_name)
            if hasattr(module, '__path__') and module.__path__:
                # __path__ が通常リストであるため、最初の要素を取得
                return module.__path__[0]
        except ImportError:
            pass
    
    # 通常のパッケージ検索
    for site_packages_dir in site.getsitepackages() + [site.getusersitepackages()]:
        potential_path = os.path.join(site_packages_dir, package_name)
        if os.path.isdir(potential_path):
            return potential_path
    
    return None

# --- パッケージの全Pythonファイルを再帰的に収集する関数 ---
def collect_package_data(package_name, exclude_dirs=None):
    """パッケージの全Pythonファイルとデータファイルを再帰的に収集"""
    if exclude_dirs is None:
        exclude_dirs = []
    
    result = []
    pkg_path = get_package_path(package_name)
    
    if not pkg_path:
        # 直接インポートからパスを取得する試み
        try:
            module = importlib.import_module(package_name)
            if hasattr(module, '__path__') and module.__path__:
                pkg_path = module.__path__[0]
                print(f"INFO: インポートから取得した {package_name} のパス: {pkg_path}")
        except ImportError:
            print(f"警告: パッケージ {package_name} が見つかりません")
            return result
        except Exception as e:
            print(f"警告: {package_name} のインポート中にエラー: {e}")
            return result
    
    if not pkg_path:
        print(f"警告: パッケージ {package_name} のパスが見つかりません")
        return result
        
    print(f"INFO: {package_name} のパス: {pkg_path}")
    
    # パッケージのルートディレクトリ内のすべてのファイルを再帰的にスキャン
    for root, dirs, files in os.walk(pkg_path):
        # 除外ディレクトリをスキップ
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        # 各ファイルを処理
        for file in files:
            file_path = os.path.join(root, file)
            # パッケージルートからの相対パスを計算
            rel_dir = os.path.relpath(root, pkg_path)
            # ターゲットディレクトリを構築
            if rel_dir == '.':
                target_dir = package_name
            else:
                target_dir = os.path.join(package_name, rel_dir)
            
            # データのタプルを結果リストに追加
            result.append((file_path, target_dir))
            
    return result

# --- pyannote.audio 特有のファイル収集関数 ---
def collect_pyannote_data():
    result = []
    
    # pyannote 関連の全ネームスペースを探索
    namespaces = ["pyannote"]
    for namespace in namespaces:
        namespace_paths = get_namespace_package_paths(namespace)
        
        if not namespace_paths:
            print(f"警告: {namespace} ネームスペースが見つかりません")
            continue
            
        print(f"INFO: {namespace} ネームスペースのパス: {namespace_paths}")
        
        # 各ネームスペースパス内のサブパッケージを収集
        for namespace_path in namespace_paths:
            for item in os.listdir(namespace_path):
                subpkg_path = os.path.join(namespace_path, item)
                if os.path.isdir(subpkg_path) and not item.startswith('__'):
                    subpkg_name = f"{namespace}.{item}"
                    print(f"INFO: サブパッケージを検出: {subpkg_name} @ {subpkg_path}")
                    
                    # このサブパッケージのすべてのファイルを収集
                    for root, dirs, files in os.walk(subpkg_path):
                        # __pycache__ をスキップ
                        dirs[:] = [d for d in dirs if d != '__pycache__']
                        
                        for file in files:
                            file_path = os.path.join(root, file)
                            # ターゲットパスを構築
                            rel_path = os.path.relpath(root, namespace_path)
                            target_dir = os.path.join(namespace, rel_path)
                            result.append((file_path, target_dir))
    
    return result

# --- 主要なデータファイルの直接収集 ---
datas = []

# --- lightning_fabric の version.info を直接検索して追加 ---
lightning_fabric_path = get_package_path('lightning_fabric')
if lightning_fabric_path:
    version_info_path = os.path.join(lightning_fabric_path, 'version.info')
    if os.path.isfile(version_info_path):
        datas.append((version_info_path, 'lightning_fabric'))
        print(f"INFO: lightning_fabric/version.info を追加: {version_info_path}")
    else:
        print(f"警告: lightning_fabric/version.info ファイルが見つかりません: {version_info_path}")
        # 代替方法として、globパターンで検索
        version_files = glob.glob(os.path.join(lightning_fabric_path, '**/version.info'), recursive=True)
        if version_files:
            for vf in version_files:
                rel_path = os.path.relpath(vf, lightning_fabric_path)
                target_dir = os.path.join('lightning_fabric', os.path.dirname(rel_path))
                datas.append((vf, target_dir))
                print(f"INFO: 代替方法で lightning_fabric の version.info を追加: {vf} -> {target_dir}")
        else:
            print("エラー: lightning_fabricのversion.infoが見つかりません。ビルドを中止します。")
            sys.exit(1)
else:
    print("エラー: lightning_fabricパッケージが見つかりません。ビルドを中止します。")
    sys.exit(1)

# --- Whisperのアセットを追加 ---
whisper_path = get_package_path('whisper')
if whisper_path:
    assets_path = os.path.join(whisper_path, 'assets')
    if os.path.isdir(assets_path):
        # 全アセットを 'whisper/assets' ディレクトリにコピー
        for asset_file in glob.glob(os.path.join(assets_path, '*')):
            if os.path.isfile(asset_file):
                datas.append((asset_file, 'whisper/assets'))
                print(f"INFO: Whisperアセット追加: {asset_file}")
    else:
        print(f"警告: Whisperのassetsディレクトリが見つかりません: {assets_path}")
        sys.exit(1)
else:
    print("警告: Whisperパッケージが見つかりません。")
    sys.exit(1)

# --- pyannote.audio パッケージの全ファイルを収集（改良版） ---
try:
    # まず pyannote パッケージがインストールされているか確認
    # ネームスペースパッケージのため特別な処理が必要
    print("INFO: pyannote ネームスペースパッケージの検索を開始...")
    
    # pyannote 関連のすべてのモジュールとファイルを収集
    pyannote_files = collect_pyannote_data()
    if pyannote_files:
        datas.extend(pyannote_files)
        print(f"INFO: pyannote から合計 {len(pyannote_files)} ファイルを追加しました")
    else:
        print("警告: pyannote ファイルが見つかりませんでした")
        
        # インポートできるかどうかを確認
        try:
            import pyannote.audio
            print(f"INFO: pyannote.audio をインポートできました。パス: {pyannote.audio.__path__}")
        except ImportError as e:
            print(f"エラー: pyannote.audio をインポートできません: {e}")
        except Exception as e:
            print(f"エラー: pyannote.audio のチェック中に例外が発生: {e}")
    
    # 個別モジュールのインポートテストとパス表示
    pyannote_modules = [
        'pyannote.audio',
        'pyannote.core',
        'pyannote.pipeline',
        'pyannote.database'
    ]
    
    for module_name in pyannote_modules:
        try:
            module = importlib.import_module(module_name)
            print(f"INFO: {module_name} をインポートできました")
            if hasattr(module, '__path__'):
                print(f"INFO: {module_name}.__path__ = {module.__path__}")
                
                # パスが存在する場合、そのディレクトリ内のファイルも追加
                if module.__path__:
                    module_path = module.__path__[0]
                    for root, dirs, files in os.walk(module_path):
                        # __pycache__ をスキップ
                        dirs[:] = [d for d in dirs if d != '__pycache__']
                        
                        for file in files:
                            file_path = os.path.join(root, file)
                            rel_path = os.path.relpath(root, os.path.dirname(module_path))
                            target_dir = os.path.join(os.path.dirname(module_name.replace('.', os.sep)), rel_path)
                            datas.append((file_path, target_dir))
                            print(f"INFO: モジュールパスから追加: {file_path} -> {target_dir}")
        except ImportError:
            print(f"警告: {module_name} をインポートできません")
        except Exception as e:
            print(f"警告: {module_name} のチェック中にエラー: {e}")

except Exception as e:
    print(f"警告: pyannote パッケージの処理中にエラーが発生しました: {e}")

# --- SpeechBrainのデータを追加 ---
speechbrain_files = collect_package_data('speechbrain', exclude_dirs=['__pycache__'])
if speechbrain_files:
    datas.extend(speechbrain_files)
    print(f"INFO: SpeechBrain から {len(speechbrain_files)} ファイルを追加しました")
else:
    print("警告: SpeechBrainファイルが見つかりませんでした")

# --- Analysis ブロック ---
a = Analysis(
    ['transcribe.py'],
    pathex=[],
    binaries=[],
    datas=datas,  # 上記で収集したデータファイル
    hiddenimports=[
        # pyannote 関連 - 完全なサブモジュールリスト
        'pyannote',
        'pyannote.audio',
        'pyannote.audio.core',
        'pyannote.audio.pipelines',  # 明示的に追加
        'pyannote.audio.pipelines.speaker_verification',
        'pyannote.audio.pipelines.voice_activity_detection',
        'pyannote.audio.features',
        'pyannote.audio.models',
        'pyannote.audio.tasks',
        'pyannote.audio.utils',
        'pyannote.core',
        'pyannote.database',
        'pyannote.metrics',
        'pyannote.pipeline',
        
        # pyannote の依存関係
        'pytorch_metric_learning',
        'torch_audiomentations',
        'einops',
        'asteroid_filterbanks',
        
        # Whisper 関連
        'whisper',
        'whisper.tokenizer',
        'whisper.decoding',
        'whisper.model',
        'whisper.audio',
        'tiktoken',
        
        # lightning_fabric 関連
        'lightning_fabric',
        'lightning_fabric.utilities',
        'lightning_fabric.accelerators',
        'lightning_fabric.plugins',
        'lightning_fabric.strategies',
        
        # PyTorch 関連
        'torch',
        'torch.nn',
        'torch.nn.functional',
        'torch.optim',
        'torch.utils',
        'torch.utils.data',
        'torchaudio',
        'torchaudio.functional',
        'torchaudio.transforms',
        
        # 数値計算・データ処理
        'numpy',
        'scipy',
        'pandas',
        'sklearn',
        'numba',
        
        # 音声処理
        'librosa',
        'soundfile',
        'pydub',
        'audioread',
        
        # Hugging Face
        'huggingface_hub',
        'transformers',
        
        # タイムゾーン関連
        'tzdata',
        
        # その他の依存関係
        'charset_normalizer',
        'yaml',
        'requests',
        'filelock',
        'packaging',
        'tqdm',
        
        # SpeechBrain 関連 - 詳細なサブモジュール
        'speechbrain',
        'speechbrain.utils',
        'speechbrain.utils.data_utils',
        'speechbrain.utils.distributed',
        'speechbrain.utils.epoch_loop',
        'speechbrain.utils.fetching',
        'speechbrain.utils.hparams',
        'speechbrain.utils.metric_stats',
        'speechbrain.utils.parameter_transfer',
        'speechbrain.utils.train_logger',
        'speechbrain.pretrained',
        'speechbrain.pretrained.interfaces',
        'speechbrain.dataio',
        'speechbrain.decoders',
        'speechbrain.lobes',
        'speechbrain.nnet',
        'speechbrain.processing',
    ],
    hookspath=[],
    runtime_hooks=['.\\runtime_hooks\\set_pythonutf8.py'],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# --- PYZ (Python Archive) の作成 ---
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# --- EXE の作成 ---
exe = EXE(
    pyz,
    a.scripts,
    [],  # バイナリは COLLECT で処理するため空に
    exclude_binaries=True,  # バイナリ等はCOLLECTで扱う
    name='transcribe',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # アイコンが必要なら指定
)

# --- COLLECT ブロック: パッケージの収集 ---
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='transcribe'
)

# --- 単一ファイル形式のEXE作成 (オプション) ---
# 以下のコメントを外せば、1つのEXEファイルでもビルドできる
exe_onefile = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='transcribe_onefile',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,  # 一時ディレクトリ
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
