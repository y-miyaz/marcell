import abc
import logging

logger = logging.getLogger(__name__)


class ConverterInterface(abc.ABC):
    """
    ファイルをマークダウンに変換するコンバーターのインターフェイス
    """

    @abc.abstractmethod
    def convert_file_to_markdown(self, file_path):
        """
        ファイルをマークダウン形式に変換する

        Args:
            file_path: 変換するファイルのパス

        Returns:
            str: マークダウン形式のテキスト、失敗時はNone
        """
        pass

    @abc.abstractmethod
    def save_markdown(self, markdown_content, output_path):
        """
        マークダウンコンテンツをファイルに保存する

        Args:
            markdown_content: 保存するマークダウンコンテンツ
            output_path: 出力ファイルパス

        Returns:
            bool: 保存が成功したかどうか
        """
        pass
