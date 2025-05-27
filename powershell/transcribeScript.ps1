# --- �ݒ荀�� ---
$SourceFolder = "C:\whisperTranscribe\TranscribeInput"      # �R�s�[���̃t�H���_�p�X
$DestinationFolder = "C:\whisperTranscribe\Transcribing" # �R�s�[��̃t�H���_�p�X
$EndFolder = "C:\whisperTranscribe\TranscribeEnd"      # ����������̃t�@�C���ړ���t�H���_
# �g�p����^�C���X�^���v�̎��: "LastWriteTime" (�ŏI�X�V����) �܂��� "CreationTime" (�쐬����)
$TimestampProperty = "LastWriteTime"

# transcribe �R�}���h�֘A�̐ݒ�
$TranscribeCommandName = "C:\whisperTranscribe\transcribe_onefile.exe" # transcribe�R�}���h�̃t�@�C���� (�K�v�ɉ����Ċg���q .exe �Ȃǂ�)
$TranscribeOutputDir = "C:\whisperTranscribe\TranscribeOutput"

# �ݒ荀�ڂ̒ǉ�
$LogFolder = "C:\whisperTranscribe\Logs"  # ���O�t�@�C���̕ۑ���t�H���_
$LogFilePrefix = "transcribe_log_"          # ���O�t�@�C���̃v���t�B�b�N�X

# ������ �܂߂����g���q�̃��X�g (�h�b�g�Ȃ��ŏ������Ŏw��) ������
$IncludedExtensions = @("wav", "mp3", "m4a", "ogg", "flac", "aac", "wma", "mp4") 
# --- �ݒ荀�ڂ����܂� ---


# �e��t�H���_�̑��݊m�F�ƍ쐬
if (-not (Test-Path $DestinationFolder)) {
    New-Item -ItemType Directory -Path $DestinationFolder | Out-Null
    Write-Host "�R�s�[��t�H���_���쐬���܂���: $DestinationFolder"
}
if (-not (Test-Path $TranscribeOutputDir)) {
    try {
        New-Item -ItemType Directory -Path $TranscribeOutputDir -Force -ErrorAction Stop | Out-Null
        Write-Host "transcribe�o�̓f�B���N�g�����쐬���܂���: $TranscribeOutputDir"
    } catch {
        Write-Error "�G���[: transcribe�o�̓f�B���N�g�� '$TranscribeOutputDir' �̍쐬�Ɏ��s���܂����B�X�N���v�g���I�����܂��B"
        exit 1
    }
}
if (-not (Test-Path $EndFolder)) {
    try {
        New-Item -ItemType Directory -Path $EndFolder -Force -ErrorAction Stop | Out-Null
        Write-Host "���������t�@�C���i�[�f�B���N�g�����쐬���܂���: $EndFolder"
    } catch {
        Write-Error "�G���[: ���������t�@�C���i�[�f�B���N�g�� '$EndFolder' �̍쐬�Ɏ��s���܂����B�X�N���v�g���I�����܂��B"
        exit 1
    }
}
if (-not (Test-Path $LogFolder)) {
    New-Item -ItemType Directory -Path $LogFolder | Out-Null
    Write-Host "���O�t�H���_���쐬���܂���: $LogFolder"
}

$FilesToCopy = Get-ChildItem -Path $SourceFolder -File | Sort-Object -Property $TimestampProperty

if ($FilesToCopy.Count -eq 0) {
    Write-Host "�R�s�[���t�H���_�Ƀt�@�C����������܂���: $SourceFolder"
    exit
}

Write-Host "�ȉ��̃t�@�C�����Â����ɏ������܂�:"
$FilesToCopy | ForEach-Object { Write-Host ("  " + $_.Name + " (" + ($_.($TimestampProperty)) + ")") }
Write-Host "---"

# 1�t�@�C��������
foreach ($File in $FilesToCopy) {
    $FileName = $File.Name
    $FileExtension = $File.Extension.TrimStart('.').ToLower()

    if ($IncludedExtensions -contains $FileExtension) {
        Write-Host "�����Ώ� (�g���q '$FileExtension' ����v): $FileName ..."

        $RobocopyArgs = @(
            $SourceFolder,
            $DestinationFolder,
            "`"$FileName`"",
            "/MOV",
            "/NFL", "/NDL", "/NJH", "/NJS",
            "/R:3", "/W:5"
        )
        
        Write-Host "Robocopy���s�R�}���h: robocopy.exe $($RobocopyArgs -join ' ')"
        
        $robocopyProcess = Start-Process -FilePath "robocopy.exe" -ArgumentList $RobocopyArgs -Wait -NoNewWindow -PassThru
        
        if ($robocopyProcess.ExitCode -lt 8) {
            Write-Host "Robocopy�ɂ��ړ����� (�I���R�[�h: $($robocopyProcess.ExitCode)): $FileName"
            Write-Host "---"

            # --- �㑱��transcribe�R�}���h�����s ---
            Write-Host "transcribe�R�}���h�����s���܂� (�Ώۃt�@�C��: $FileName)..."
            
            # ���O�t�@�C�����̐���
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
            Write-Host "Transcribe���s�R�}���h: $TranscribeCommandFullPath $($TranscribeArgs -join ' ')"
            try {
                # �ꎞ�t�@�C�����쐬
                $stdOutFile = [System.IO.Path]::GetTempFileName()
                $stdErrFile = [System.IO.Path]::GetTempFileName()
                
                # �W���o�͂ƕW���G���[��ʁX�̃t�@�C���Ƀ��_�C���N�g
                $processInfo = New-Object System.Diagnostics.ProcessStartInfo
                $processInfo.FileName = $TranscribeCommandFullPath
                $processInfo.Arguments = $TranscribeArgs
                $processInfo.RedirectStandardOutput = $true
                $processInfo.RedirectStandardError = $true
                $processInfo.UseShellExecute = $false
                $processInfo.CreateNoWindow = $true
                
                $process = New-Object System.Diagnostics.Process
                $process.StartInfo = $processInfo
                $process.Start() | Out-Null
                
                # �񓯊��ŏo�͂��t�@�C���Ƀ��_�C���N�g
                $stdOutTask = $process.StandardOutput.ReadToEndAsync()
                $stdErrTask = $process.StandardError.ReadToEndAsync()
                
                # �v���Z�X�̏I����ҋ@
                $process.WaitForExit()
                
                # �񓯊��^�X�N�̊�����ҋ@
                [System.Threading.Tasks.Task]::WaitAll($stdOutTask, $stdErrTask)
                
                # �o�͂��t�@�C���ɕۑ�
                [System.IO.File]::WriteAllText($stdOutFile, $stdOutTask.Result)
                [System.IO.File]::WriteAllText($stdErrFile, $stdErrTask.Result)
                
                # ���O�t�@�C���ɏo�͂��}�[�W
                $stdOutContent = [System.IO.File]::ReadAllText($stdOutFile)
                $stdErrContent = [System.IO.File]::ReadAllText($stdErrFile)
                
                # ���O�t�@�C���ɏ�������
                "=== �W���o�� ===" | Out-File -FilePath $LogFile -Encoding utf8
                $stdOutContent | Out-File -FilePath $LogFile -Encoding utf8 -Append
                "`n=== �W���G���[�o�� ===" | Out-File -FilePath $LogFile -Encoding utf8 -Append
                $stdErrContent | Out-File -FilePath $LogFile -Encoding utf8 -Append
                
                # �ꎞ�t�@�C�����폜
                Remove-Item $stdOutFile, $stdErrFile -ErrorAction SilentlyContinue
                
                if ($process.ExitCode -eq 0) {
                    Write-Host "transcribe�R�}���h�̎��s���������܂��� (�I���R�[�h: $($process.ExitCode))."
                    Write-Host "���O�t�@�C�����쐬����܂���: $LogFile"
                    
                    # ���������������t�@�C����TranscribeEnd�t�H���_�Ɉړ�
                    try {
                        $endFilePath = Join-Path -Path $EndFolder -ChildPath $FileName
                        Move-Item -Path $TranscribeInputFile -Destination $endFilePath -Force -ErrorAction Stop
                        Write-Host "���������t�@�C�����ړ����܂���: $endFilePath"
                    } catch {
                        Write-Warning "�t�@�C���̈ړ����ɃG���[���������܂���: $($_.Exception.Message)"
                    }
                } else {
                    Write-Warning "transcribe�R�}���h�̎��s���I�����܂������A�G���[�R�[�h $($process.ExitCode) ��Ԃ��܂����B"
                    Write-Host "�G���[���O�� $LogFile �ɋL�^����Ă��܂��B"
                }
            } catch {
                Write-Error "transcribe�R�}���h�̎��s�Ɏ��s���܂���: $($_.Exception.Message)"
                Write-Error "���s�����R�}���h�p�X: $TranscribeCommandFullPath"
                
                # �G���[���b�Z�[�W�𒼐ڃ��O�t�@�C���ɏ�������
                "���s�G���[: $($_.Exception.Message)" | Out-File -FilePath $LogFile -Encoding utf8 -Force
                "���s�����R�}���h�p�X: $TranscribeCommandFullPath" | Out-File -FilePath $LogFile -Encoding utf8 -Append -Force
                
                Write-Host "�G���[���O�� $LogFile �ɋL�^����Ă��܂��B"
            }
            Write-Host "---"

        } else {
            Write-Warning "Robocopy�ŃG���[�܂��͖�肪�������܂��� (�I���R�[�h: $($robocopyProcess.ExitCode)): $FileName"
            Write-Host "---"
        }
    } else {
        Write-Host "�X�L�b�v (�g���q '$FileExtension' ���ΏۊO): $FileName"
        Write-Host "---"
    }
}

Write-Host "���ׂẴt�@�C���̏������������܂����B"
