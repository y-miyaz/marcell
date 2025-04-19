# marcell.ps1 - マークダウン変換ツール

# スクリプトの絶対パスを取得
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Definition
# プロジェクトのルートディレクトリ（スクリプトの親ディレクトリ）
$projectRoot = Split-Path -Parent $scriptPath

# パスをPythonの形式に変換
$env:PYTHONPATH = "$projectRoot;$env:PYTHONPATH"

# main.pyを実行し、すべての引数を渡す
& python "$projectRoot\src\app.py" $args
