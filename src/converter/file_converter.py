import os
import logging
from markitdown import MarkItDown
from converter.converter_interface import ConverterInterface
from utils.logging_config import setup_logging

# ロガーの取得
logger = logging.getLogger(__name__)


class FileToMarkdownConverter(ConverterInterface):
    def __init__(self):
        self.markitdown = MarkItDown()

    def convert_file_to_markdown(self, file_path):
        """
        ファイルをマークダウン形式に変換する

        Args:
            file_path: 変換するファイルのパス

        Returns:
            str: マークダウン形式のテキスト
        """
        if not os.path.exists(file_path):
            logger.error(f"File does not exist: {file_path}")
            return None

        file_ext = os.path.splitext(file_path)[1].lower()

        try:
            # マークダウンファイルの場合はそのまま返す
            if file_ext == ".md":
                with open(file_path, "r", encoding="utf-8") as f:
                    return f.read()

            # その他のサポートされているファイル形式
            else:
                logger.info(f"Converting file using markitdown: {file_path}")
                result = self.markitdown.convert(file_path)
                return result.text_content

        except Exception as e:
            logger.error(f"Error converting file to Markdown: {e}")
            return None

    def save_markdown(self, markdown_content, output_path):
        """
        マークダウンコンテンツをファイルに保存する

        Args:
            markdown_content: 保存するマークダウンコンテンツ
            output_path: 出力ファイルパス

        Returns:
            bool: 保存が成功したかどうか
        """
        if not markdown_content:
            logger.error("No markdown content to save")
            return False

        try:
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)

            logger.info(f"Markdown saved to {output_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving markdown to file: {e}")
            return False
