import argparse
import os
import glob
import sys

# プロジェクトのルートディレクトリをPYTHONPATHに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from converter.file_converter import FileToMarkdownConverter
from converter.excel_converter import ExcelToMarkdownConverter
from formatter.openai_formatter import OpenAIMarkdownFormatter
from formatter.deepseek_formatter import DeepseekMarkdownFormatter
from dotenv import load_dotenv
from utils.logging_config import setup_logging
from concurrent.futures import ProcessPoolExecutor
import multiprocessing

# 環境変数の読み込み
load_dotenv()

# ロギング設定
logger = setup_logging()

# サポートされているファイル拡張子
SUPPORTED_EXTENSIONS = [
    ".xlsx",
    ".xls",
    ".xlsm",
    ".docx",
    ".pptx",
    ".pdf",
    ".md",
]

# 生成AIでサポートする拡張子を環境変数から読み込む
AI_SUPPORTED_EXTENSIONS = os.getenv(
    "AI_SUPPORTED_EXTENSIONS", ".xlsx,.xls,.xlsm"
).split(",")


def create_output_dir_structure(input_dir, output_base_dir):
    """
    出力ディレクトリの構造を作成する
    """
    if not os.path.exists(output_base_dir):
        os.makedirs(output_base_dir)
        logger.info(f"Created output directory: {output_base_dir}")


def process_single_file(
    file_path,
    output_path,
    use_ai=False,
    ai_provider=None,
    ai_model=None,
    rate_limit_delay=1.0,
    max_tokens=3000,
):
    """
    単一ファイルを処理してマークダウンに変換する共通処理

    Args:
        file_path: 入力ファイルパス
        output_path: 出力先のパス
        use_ai: AIフォーマットを使用するかどうか
        ai_provider: 使用するAIプロバイダ（"openai"または"deepseek"）
        ai_model: 使用するAIモデル
        rate_limit_delay: APIリクエスト間の待機時間
        max_tokens: 最大トークン数

    Returns:
        bool: 処理が成功したかどうか
    """
    # ファイルの存在チェック
    if not os.path.exists(file_path):
        logger.error(f"Error: Input file '{file_path}' does not exist.")
        return False

    # Office一時ファイル（~$で始まるファイル）をチェック
    if os.path.basename(file_path).startswith("~$"):
        logger.info(f"Skipping temporary Office file: {file_path}")
        return False

    # ファイル拡張子のチェック
    _, file_ext = os.path.splitext(file_path)
    if file_ext.lower() not in SUPPORTED_EXTENSIONS:
        logger.error(f"Error: Unsupported file format '{file_ext}'")
        logger.info(f"Supported formats: {', '.join(SUPPORTED_EXTENSIONS)}")
        return False

    # 適切なコンバーターを選択
    if file_ext.lower() in [".xlsx", ".xls", ".xlsm"]:
        converter = ExcelToMarkdownConverter()
    else:
        converter = FileToMarkdownConverter()

    # ファイルをマークダウンに変換
    markdown_content = converter.convert_file_to_markdown(file_path)

    # 変換に失敗した場合はエラーを表示して終了
    if not markdown_content:
        logger.error(f"Failed to convert file to markdown: {file_path}")
        return False

    # AIを使用してマークダウンをフォーマット
    # 環境変数で指定された拡張子のみ生成AIによる処理を行う
    is_ai_supported = file_ext.lower() in AI_SUPPORTED_EXTENSIONS
    if use_ai and markdown_content and is_ai_supported:
        api_key = (
            os.getenv("OPENAI_API_KEY")
            if ai_provider == "openai"
            else os.getenv("DEEPSEEK_API_KEY")
        )

        # AIフォーマッターを初期化
        if ai_provider == "deepseek":
            ai_formatter = DeepseekMarkdownFormatter(
                model=ai_model,
                api_key=api_key,
                prompts_file="prompts.yaml",
                max_tokens=max_tokens,
                rate_limit_delay=rate_limit_delay,
            )
        else:  # デフォルトはOpenAI
            ai_formatter = OpenAIMarkdownFormatter(
                model=ai_model,
                api_key=api_key,
                prompts_file="prompts.yaml",
                max_tokens=max_tokens,
                rate_limit_delay=rate_limit_delay,
            )

        # マークダウンをフォーマット
        logger.info(f"Applying AI formatting to {file_path}")
        markdown_content = ai_formatter.format_markdown(
            markdown_content, file_ext=file_ext
        )
    elif use_ai and not is_ai_supported:
        logger.info(
            f"Skipping AI formatting for {file_path} (extension {file_ext} not in AI_SUPPORTED_EXTENSIONS)"
        )

    # マークダウンをファイルに保存
    if not converter.save_markdown(markdown_content, output_path):
        logger.error(f"Error saving Markdown file to: {output_path}")
        return False

    return True


def process_directory(
    input_dir,
    output_base_dir,
    use_ai=False,
    ai_provider=None,
    ai_model=None,
    rate_limit_delay=1.0,
    max_tokens=3000,
):
    """
    指定されたディレクトリ内のサポートされているファイルを処理し、
    同じディレクトリ構造でマークダウンに変換する
    """
    # 入力ディレクトリ内のすべてのサポートされているファイルを検索
    input_files = []
    for ext in SUPPORTED_EXTENSIONS:
        input_files.extend(
            glob.glob(os.path.join(input_dir, "**", f"*{ext}"), recursive=True)
        )

    if not input_files:
        logger.warning(f"No supported files found in {input_dir}")
        return

    # 並列処理のためのライブラリをインポート

    # 並列処理に使用するCPUコア数（利用可能なコアの75%を使用）
    num_workers = max(1, int(multiprocessing.cpu_count() * 0.75))
    logger.info(f"Using {num_workers} worker processes for parallel processing")

    # 処理するファイルの情報をリストにまとめる
    process_jobs = []
    for file_path in input_files:
        # 相対パスを取得
        rel_path = os.path.relpath(file_path, input_dir)
        # 出力パスを作成
        output_dir = os.path.join(output_base_dir, os.path.dirname(rel_path))
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # 出力ファイル名を作成
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        output_file = os.path.join(output_dir, f"{base_name}.md")

        # 処理ジョブをリストに追加
        process_jobs.append(
            (
                file_path,
                output_file,
                use_ai,
                ai_provider,
                ai_model,
                rate_limit_delay,
                max_tokens,
            )
        )

    # 並列処理を実行
    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        # プロセスプールにジョブを投入
        futures = [executor.submit(process_single_file, *job) for job in process_jobs]

        # 結果を収集
        for i, future in enumerate(futures):
            try:
                result = future.result()
                logger.info(
                    f"Processed {i + 1}/{len(process_jobs)}: {process_jobs[i][0]} - {'Success' if result else 'Failed'}"
                )
            except Exception as e:
                logger.error(f"Error processing {process_jobs[i][0]}: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Convert various file formats to Markdown."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-i", "--input", help="Input file path")
    group.add_argument(
        "-d", "--directory", help="Directory containing files to convert"
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Output path. For files: output markdown file path. "
        "For directories: output directory path. "
        "If not specified for a directory, '{directory_name}_md' will be used",
    )
    parser.add_argument(
        "--no-titles",
        action="store_true",
        help="Do not include sheet/data names as titles in the Markdown",
    )
    parser.add_argument(
        "--use-ai",
        action="store_true",
        help="Use AI to enhance and format the Markdown output",
    )
    parser.add_argument(
        "--ai-provider",
        choices=["openai", "deepseek"],
        default="openai",
        help="AI provider to use for formatting (default: openai)",
    )
    parser.add_argument(
        "--prompts-file",
        default="prompts.yaml",
        help="Path to YAML file containing prompts for different file types",
    )
    parser.add_argument(
        "--list-ai-extensions",
        action="store_true",
        help="List file extensions that will be processed by AI",
    )

    args = parser.parse_args()

    # AI対応の拡張子一覧表示
    if args.list_ai_extensions:
        logger.info(
            f"AI processing is enabled for the following extensions: {', '.join(AI_SUPPORTED_EXTENSIONS)}"
        )
        return

    # AI使用の設定
    use_ai = args.use_ai
    ai_provider = args.ai_provider
    ai_model = (
        os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        if ai_provider == "openai"
        else os.getenv("DEEPSEEK_MODEL", "")
    )
    rate_limit_delay = (
        float(os.getenv("OPENAI_RATE_LIMIT_DELAY", 1.0))
        if ai_provider == "openai"
        else float(os.getenv("DEEPSEEK_RATE_LIMIT_DELAY", 1.0))
    )
    max_tokens = (
        int(os.getenv("OPENAI_MAX_TOKENS", 3000))
        if ai_provider == "openai"
        else int(os.getenv("DEEPSEEK_MAX_TOKENS", 3000))
    )

    # ディレクトリモード
    if args.directory:
        if not os.path.isdir(args.directory):
            logger.error(f"Error: Directory '{args.directory}' does not exist.")
            return

        # 出力ディレクトリ名を作成
        dir_name = os.path.basename(os.path.normpath(args.directory))
        output_dir = (
            args.output
            if args.output
            else f"{os.path.dirname(os.path.abspath(args.directory))}/{dir_name}_md"
        )
        logger.info(f"Output directory set to: {output_dir}")

        # ディレクトリ処理を実行
        create_output_dir_structure(args.directory, output_dir)
        process_directory(
            args.directory,
            output_dir,
            use_ai,
            ai_provider,
            ai_model,
            rate_limit_delay,
            max_tokens,
        )

    # 単一ファイルモード
    else:
        # 出力パスが指定されていない場合、入力ファイル名を基に生成
        output_path = args.output
        if not output_path:
            base_name = os.path.splitext(os.path.basename(args.input))[0]
            output_path = f"{base_name}.md"

        # ファイル処理を実行
        success = process_single_file(
            args.input,
            output_path,
            use_ai,
            ai_provider,
            ai_model,
            rate_limit_delay,
            max_tokens,
        )

        if not success:
            logger.error("File processing failed.")
            return


if __name__ == "__main__":
    main()
