import abc
import logging

logger = logging.getLogger(__name__)


class FormatterInterface(abc.ABC):
    """
    マークダウンフォーマッターのインターフェース
    """

    @abc.abstractmethod
    def __init__(
        self,
        model=None,
        api_key=None,
        prompts_file="prompts.yaml",
        max_tokens=3000,
        rate_limit_delay=None,
    ):
        """
        初期化

        Args:
            model: 使用するモデル名
            api_key: API Key
            prompts_file: プロンプト設定ファイルのパス
            max_tokens: 最大トークン数
            rate_limit_delay: APIリクエスト間の待機時間
        """
        pass

    @abc.abstractmethod
    def format_markdown(self, markdown_content, file_ext=None, max_workers=4):
        """
        マークダウンをフォーマットする

        Args:
            markdown_content: フォーマットするマークダウンコンテンツ
            file_ext: ファイル拡張子
            max_workers: 同時実行ワーカー数

        Returns:
            str: フォーマット済みのマークダウンコンテンツ
        """
        pass

    @abc.abstractmethod
    def _load_prompts(self, prompts_file):
        """
        プロンプト設定ファイルを読み込む

        Args:
            prompts_file: プロンプトファイルのパス

        Returns:
            dict: プロンプト設定
        """
        pass

    @abc.abstractmethod
    def _get_prompt_for_file_type(self, file_ext):
        """
        ファイル拡張子に応じたプロンプトを取得する

        Args:
            file_ext: ファイル拡張子

        Returns:
            dict: プロンプト設定
        """
        pass
