# Marcell - マークダウン変換ツール

Marcellは様々なファイル形式（Excel、Word、PowerPoint、PDF）をマークダウンに変換し、オプションでAI処理によって整形するツールです。

## 特徴

- 多様なファイル形式をマークダウンに一括変換
- OpenAI または Deepseek AIを使用したマークダウンの高度な整形
- 単一ファイルおよびディレクトリの一括処理に対応
- 並列処理による高速な変換とAI処理

## インストール

### 必要条件

- Python 3.12以上
- 必要なPythonパッケージ（requirements.txtからインストール可能）

```bash
pip install -r requirements.txt
```

### セットアップ

1. リポジトリをクローン:

```bash
git clone https://github.com/yourusername/marcell.git
cd marcell
```

2. 環境変数を設定（`.env`ファイルを作成するか、システム環境変数を設定）:

```
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4o-mini
OPENAI_RATE_LIMIT_DELAY=1.0
OPENAI_MAX_TOKENS=3000

DEEPSEEK_API_KEY=your_deepseek_api_key
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_RATE_LIMIT_DELAY=1.0
DEEPSEEK_MAX_TOKENS=3000
```

3. コマンドラインから実行できるようにする:

#### Unix/Linux/Mac:
```bash
chmod +x bin/marcell
ln -s "$(pwd)/bin/marcell" /usr/local/bin/marcell
```

#### Windows (PowerShell):
```powershell
# PowerShellプロファイルにパスを追加
Add-Content $profile "`$env:Path += ';$(pwd)\bin'"
```

## 使用方法

### 基本的な使い方

#### 単一ファイル変換:

```bash
marcell -i input.xlsx -o output.md
```

#### ディレクトリ内のファイルを一括変換:

```bash
marcell -d input_directory -o output_directory
```

### AIフォーマット機能

OpenAIまたはDeepseekのAIを使用してマークダウンを美しく整形できます:

```bash
marcell -i input.xlsx --use-ai --ai-provider openai
```

```bash
marcell -d input_directory --use-ai --ai-provider deepseek
```

### コマンドラインオプション

```
引数:
  -h, --help            ヘルプメッセージを表示して終了
  -i INPUT, --input INPUT
                        入力ファイルパス
  -d DIRECTORY, --directory DIRECTORY
                        変換するファイルを含むディレクトリ
  -o OUTPUT, --output OUTPUT
                        出力先のパス。ファイルの場合: 出力マークダウンファイルのパス。
                        ディレクトリの場合: 出力ディレクトリのパス。
                        ディレクトリで指定されない場合、'{directory_name}_md'が使用されます
  --no-titles           マークダウンにシート/データ名をタイトルとして含めない
  --use-ai              AIを使用してマークダウン出力を拡張・整形する
  --ai-provider {openai,deepseek}
                        フォーマットに使用するAIプロバイダ (デフォルト: openai)
  --prompts-file PROMPTS_FILE
                        異なるファイルタイプのプロンプトを含むYAMLファイルへのパス
  --max-tokens MAX_TOKENS
                        AI使用時のチャンクあたりの最大トークン数 (デフォルト: 3000)
  --rate-limit-delay RATE_LIMIT_DELAY
                        APIリクエスト間の待機秒数 (デフォルト: .envファイルから、または1.0秒)
```

## サポートされているファイル形式

- Excel (.xlsx, .xls, .xlsm)
- Word (.docx)
- PowerPoint (.pptx)
- PDF (.pdf)
- Markdown (.md) - フォーマットのみ

## プロジェクト構造

```
src/
├── app.py                   # メインアプリケーション
├── bin/                      # コマンドラインツール
│   ├── marcell              # Unix用シェルスクリプト
│   ├── marcell.ps1          # Windows用PowerShellスクリプト
│   └── marcell.bat          # Windows用バッチファイル
├── converter/                # ファイル変換モジュール
│   ├── converter_interface.py  # コンバーターインターフェース
│   ├── file_converter.py       # 一般ファイル変換器
│   └── excel_converter.py      # Excel専用変換器
├── formatter/                # マークダウン整形モジュール
│   ├── formatter_interface.py  # フォーマッターインターフェース
│   ├── openai_formatter.py     # OpenAI用フォーマッター
│   └── deepseek_formatter.py   # Deepseek用フォーマッター
└── utils/                    # ユーティリティ関数
    ├── logging_config.py     # ロギング設定
    └── formatter_utils.py    # フォーマッター共通ユーティリティ
```

## プロンプト設定

`prompts.yaml`ファイルにファイル拡張子ごとのAIプロンプトを定義できます:

```yaml
default:
  system: "You are a markdown formatting expert."
  user: "Format the following markdown content:\n\n{content}"

excel:
  system: "You are an expert in formatting Excel data as clean markdown tables."
  user: "Format the following Excel data as a well-structured markdown document, ensuring tables are properly aligned:\n\n{content}"

docx:
  system: "You are an expert in formatting Word documents as clean markdown."
  user: "Convert this Word document content to well-structured markdown, preserving headings, lists, and emphasis:\n\n{content}"
```

## 開発者向け

### 新しいコンバーターの追加

新しいファイル形式のコンバーターを追加するには:

1. `converter/converter_interface.py`で定義されたインターフェースを実装する
2. 必要なメソッドを実装:
   - `convert_file_to_markdown(file_path)`
   - `save_markdown(markdown_content, output_path)`
3. `converter/__init__.py`に新しいコンバーターを追加

### 新しいフォーマッターの追加

新しいAIフォーマッターを追加するには:

1. `formatter/formatter_interface.py`で定義されたインターフェースを実装する
2. 必要なメソッドを実装:
   - `format_markdown(markdown_content, file_ext, max_workers)`
3. `formatter/__init__.py`に新しいフォーマッターを追加

## ライセンス

MITライセンス (LICENSE.txtを参照)
