# --- 設定項目 ---
$SourceFolder = "C:\whisperTranscribe\TranscribeInput"      # コピー元のフォルダパス
$DestinationFolder = "C:\whisperTranscribe\Transcribing" # コピー先のフォルダパス
# 使用するタイムスタンプの種類: "LastWriteTime" (最終更新日時) または "CreationTime" (作成日時)
$TimestampProperty = "LastWriteTime"

# transcribe コマンド関連の設定
$TranscribeCommandName = "C:\whisperTranscribe\transcribe.exe" # transcribeコマンドのファイル名 (必要に応じて拡張子 .exe なども)
$TranscribeOutputDir = "C:\whisperTranscribe\TranscribeOutput"

# 設定項目の追加
$LogFolder = "C:\whisperTranscribe\Logs"  # ログファイルの保存先フォルダ
$LogFilePrefix = "transcribe_log_"          # ログファイルのプレフィックス

# ★★★ 含めたい拡張子のリスト (ドットなしで小文字で指定) ★★★
$IncludedExtensions = @("wav", "mp3", "m4a", "ogg", "flac", "aac", "wma", "mp4") 
# --- 設定項目ここまで ---


# 各種フォルダの存在確認と作成
if (-not (Test-Path $DestinationFolder)) {
    New-Item -ItemType Directory -Path $DestinationFolder | Out-Null
    Write-Host "コピー先フォルダを作成しました: $DestinationFolder"
}
if (-not (Test-Path $TranscribeOutputDir)) {
    try {
        New-Item -ItemType Directory -Path $TranscribeOutputDir -Force -ErrorAction Stop | Out-Null
        Write-Host "transcribe出力ディレクトリを作成しました: $TranscribeOutputDir"
    } catch {
        Write-Error "エラー: transcribe出力ディレクトリ '$TranscribeOutputDir' の作成に失敗しました。スクリプトを終了します。"
        exit 1
    }
}
if (-not (Test-Path $LogFolder)) {
    New-Item -ItemType Directory -Path $LogFolder | Out-Null
    Write-Host "ログフォルダを作成しました: $LogFolder"
}

$FilesToCopy = Get-ChildItem -Path $SourceFolder -File | Sort-Object -Property $TimestampProperty

if ($FilesToCopy.Count -eq 0) {
    Write-Host "コピー元フォルダにファイルが見つかりません: $SourceFolder"
    exit
}

Write-Host "以下のファイルを古い順に処理します:"
$FilesToCopy | ForEach-Object { Write-Host ("  " + $_.Name + " (" + ($_.($TimestampProperty)) + ")") }
Write-Host "---"

# 1ファイルずつ処理
foreach ($File in $FilesToCopy) {
    $FileName = $File.Name
    $FileExtension = $File.Extension.TrimStart('.').ToLower()

    if ($IncludedExtensions -contains $FileExtension) {
        Write-Host "処理対象 (拡張子 '$FileExtension' が一致): $FileName ..."

        $RobocopyArgs = @(
            $SourceFolder,
            $DestinationFolder,
            "`"$FileName`"",
            "/MOV",
            "/NFL", "/NDL", "/NJH", "/NJS",
            "/R:3", "/W:5"
        )
        
        Write-Host "Robocopy実行コマンド: robocopy.exe $($RobocopyArgs -join ' ')"
        
        $robocopyProcess = Start-Process -FilePath "robocopy.exe" -ArgumentList $RobocopyArgs -Wait -NoNewWindow -PassThru
        
        if ($robocopyProcess.ExitCode -lt 8) {
            Write-Host "Robocopyによる移動完了 (終了コード: $($robocopyProcess.ExitCode)): $FileName"
            Write-Host "---"

            # --- 後続のtranscribeコマンドを実行 ---
            Write-Host "transcribeコマンドを実行します (対象ファイル: $FileName)..."
            
            # ログファイル名の生成
            $timestamp = (Get-Date).ToString("yyyyMMdd_HHmmss")
            $LogFile = Join-Path -Path $LogFolder -ChildPath "${LogFilePrefix}${timestamp}.txt"
            
            $TranscribeCommandFullPath = $TranscribeCommandName
            
            $TranscribeInputFile = Join-Path -Path $DestinationFolder -ChildPath $FileName
            $TranscribeArgs = @(
                "$TranscribeInputFile",
                "--model", "base",
                "--language", "ja",
                "--diarize",
                "--output_dir", "$TranscribeOutputDir"
            )
            Write-Host "Transcribe実行コマンド: $TranscribeCommandFullPath $($TranscribeArgs -join ' ')"
            try {
                # 修正: RedirectStandardOutputとRedirectStandardErrorに同じファイルを使わない
                $stdOutFile = Join-Path -Path $LogFolder -ChildPath "${LogFilePrefix}${timestamp}_stdout.txt"
                $stdErrFile = Join-Path -Path $LogFolder -ChildPath "${LogFilePrefix}${timestamp}_stderr.txt"
                
                $transcribeRunProcess = Start-Process -FilePath $TranscribeCommandFullPath -ArgumentList $TranscribeArgs -Wait -NoNewWindow -PassThru -RedirectStandardOutput $stdOutFile -RedirectStandardError $stdErrFile -ErrorAction Stop
                
                # 実行後にログをマージ
                Get-Content $stdOutFile, $stdErrFile | Set-Content $LogFile
                Remove-Item $stdOutFile, $stdErrFile -ErrorAction SilentlyContinue
                
                if ($transcribeRunProcess.ExitCode -eq 0) {
                    Write-Host "transcribeコマンドの実行が成功しました (終了コード: $($transcribeRunProcess.ExitCode))."
                    Write-Host "ログファイルが作成されました: $LogFile"
                } else {
                    Write-Warning "transcribeコマンドの実行が終了しましたが、エラーコード $($transcribeRunProcess.ExitCode) を返しました。"
                    Write-Host "エラーログは $LogFile に記録されています。"
                }
            } catch {
                Write-Error "transcribeコマンドの実行に失敗しました: $($_.Exception.Message)"
                Write-Error "試行したコマンドパス: $TranscribeCommandFullPath"
                Write-Host "エラーログは $LogFile に記録されています。"
            }
            Write-Host "---"

        } else {
            Write-Warning "Robocopyでエラーまたは問題が発生しました (終了コード: $($robocopyProcess.ExitCode)): $FileName"
            Write-Host "---"
        }
    } else {
        Write-Host "スキップ (拡張子 '$FileExtension' が対象外): $FileName"
        Write-Host "---"
    }
}

Write-Host "すべてのファイルの処理が完了しました。"