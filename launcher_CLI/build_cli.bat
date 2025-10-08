@echo off
chcp 65001 > nul

REM ===== 설정 =====
set "MAIN_SCRIPT=cli_launcher.py"
set "OUTPUT_DIR=dist"
set "PYTHON_VER=python"

REM ===== 빌드 시작 =====
echo [INFO] 빌드를 시작합니다...

%PYTHON_VER% -m nuitka ^
--standalone ^
--onefile ^
--run ^
--assume-yes-for-downloads ^
--enable-plugin=multiprocessing ^
--enable-plugin=numpy ^
--include-package=cv2 ^
--include-module=mutagen ^
--include-module=PIL ^
--include-module=tqdm ^
--include-module=pyogg ^
--output-dir=%OUTPUT_DIR% ^
--output-filename=Malie_UnRePacker_Tool_CLI.exe ^
--remove-output ^
--windows-console-mode=force ^
--show-progress ^
--show-memory ^
%MAIN_SCRIPT%

REM ===== 실행 로그 저장 =====
echo [INFO] 빌드 완료!
if exist "%OUTPUT_DIR%\Malie_UnRePacker_Tool_CLI.exe" (
    echo [INFO] EXE 실행 중... 로그는 runlog.txt에 저장됩니다
    "%OUTPUT_DIR%\Malie_UnRePacker_Tool_CLI.exe" > runlog.txt 2>&1
) else (
    echo [ERROR] 빌드 실패! 실행 파일이 존재하지 않습니다.
)

echo [INFO] runlog.txt를 확인하세요.
pause
