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
--output-filename=Malie_UnRePacker_Tool_CIL.exe^
--remove-output ^
--windows-console-mode=force ^
--show-progress ^
--show-memory ^
%MAIN_SCRIPT%


REM ===== 실행 로그 저장 =====
echo [INFO] 빌드 완료!
echo [INFO] 빌드된 EXE 실행 중... 로그는 runlog.txt에 저장됨
"%OUTPUT_DIR%\Malie_UnRePacker_Tool_CIL.exe" > runlog.txt 2>&1

echo [INFO] runlog.txt 확인하세요.
pause
