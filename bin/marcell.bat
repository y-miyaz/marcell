@echo off
REM marcell - マークダウン変換ツール

REM スクリプトの絶対パスを取得
SET SCRIPT_DIR=%~dp0
REM プロジェクトのルートディレクトリ（スクリプトの親ディレクトリ）
SET PROJECT_ROOT=%SCRIPT_DIR%..

REM main.pyを実行し、すべての引数を渡す
python "%PROJECT_ROOT%\src\app.py" %*
