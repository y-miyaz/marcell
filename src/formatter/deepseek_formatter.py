import logging
import time
import re
from openai import OpenAI
from formatter.formatter_interface import FormatterInterface
from utils.logging_config import setup_logging
from utils.formatter_utils import (
    load_prompts,
    get_prompt_for_file_type,
    split_markdown_to_chunks,
    process_markdown_in_parallel,
)

# ロガーの取得
logger = logging.getLogger(__name__)


class DeepseekMarkdownFormatter(FormatterInterface):
    def __init__(
        self,
        model,
        api_key,
        prompts_file="prompts.yaml",
        max_tokens=3000,
        rate_limit_delay=1.0,
    ):
        # APIキーの設定
        self.api_key = api_key
        if not self.api_key:
            raise ValueError(
                "Deepseek API key is required. Set it in .env file or pass as argument"
            )

        # モデルの設定
        self.model = model
        logger.info(f"Using Deepseek model: {self.model}")

        # OpenAIクライアントの初期化（Deepseek API用に設定）
        self.client = OpenAI(api_key=self.api_key, base_url="https://api.deepseek.com")

        # レート制限の待機時間（秒）
        self.rate_limit_delay = rate_limit_delay
        logger.info(f"API rate limit delay set to {self.rate_limit_delay} seconds")

        # プロンプト設定ファイルの読み込み
        self.prompts = load_prompts(prompts_file)

        # チャンクサイズ設定（トークン数）
        self.max_tokens = max_tokens

        logger.info(
            f"Deepseek formatter initialized with max tokens per chunk: {self.max_tokens}"
        )

    def _load_prompts(self, prompts_file):
        """プロンプト設定ファイルを読み込む"""
        return load_prompts(prompts_file)

    def _estimate_tokens(self, text):
        """
        テキストのトークン数を推定する
        - 日本語: 1文字あたり約0.6トークン
        - 英語: 1文字あたり約0.3トークン
        - その他: 1文字あたり約0.4トークン
        """
        if not text:
            return 0

        # 日本語（ひらがな、カタカナ、漢字）
        japanese_chars = len(
            re.findall(r"[\u3000-\u303f\u3040-\u309f\u30a0-\u30ff\u4e00-\u9faf]", text)
        )

        # 英語（アルファベット、数字、一般的な記号）
        english_chars = len(re.findall(r"[a-zA-Z0-9\s\.,;:!?\'\"()\[\]{}]", text))

        # その他の文字（上記以外の全ての文字）
        other_chars = len(text) - japanese_chars - english_chars

        # トークン数の計算
        japanese_tokens = japanese_chars * 0.6  # 日本語は1文字あたり0.6トークン
        english_tokens = english_chars * 0.3  # 英語は1文字あたり0.3トークン
        other_tokens = other_chars * 0.4  # その他は1文字あたり0.4トークン

        total_tokens = japanese_tokens + english_tokens + other_tokens

        # 最低1トークンを保証し、整数に丸める
        return max(1, int(total_tokens))

    def _count_tokens(self, text):
        """テキストのトークン数をカウントする"""
        return self._estimate_tokens(text)

    def _process_chunk(self, chunk, system_prompt, user_prompt_template):
        """単一のチャンクを処理"""
        # ユーザープロンプトにコンテンツを挿入
        user_prompt = user_prompt_template.format(content=chunk)

        try:
            # APIリクエスト送信前に待機
            time.sleep(self.rate_limit_delay)

            # APIリクエスト送信（OpenAI SDKスタイルに変更）
            logger.info(f"Sending API request to Deepseek ({self.model})...")

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                stream=False,
            )

            # レスポンスからコンテンツを抽出
            formatted_chunk = response.choices[0].message.content

            logger.info(
                f"API request successful, received {len(formatted_chunk)} characters"
            )

            return formatted_chunk

        except Exception as e:
            logger.error(f"Error processing chunk with Deepseek: {e}")
            # エラーの場合は元のチャンクを返す
            return chunk

    def format_markdown(self, markdown_content, file_ext=None, max_workers=4):
        """
        Deepseek APIを使用してマークダウンを整形する（並列処理）

        Args:
            markdown_content (str): 整形するマークダウンコンテンツ
            file_ext (str, optional): ファイルの拡張子。プロンプト選択に使用。
            max_workers (int): 同時に実行するワーカーの最大数

        Returns:
            str: 整形されたマークダウンコンテンツ
        """
        # マークダウンの長さを確認
        content_length = len(markdown_content)
        logger.info(
            f"Format markdown request: {content_length} characters, file_ext: {file_ext}, using {max_workers} workers"
        )
        logger.info(
            f"Using rate limit delay of {self.rate_limit_delay}s between API requests"
        )

        # ファイル拡張子に応じたプロンプトを取得
        prompt_config = get_prompt_for_file_type(self.prompts, file_ext)

        # システムプロンプトとユーザープロンプトテンプレートを取得
        system_prompt = prompt_config.get(
            "system", "You are a markdown formatting expert."
        )
        user_prompt_template = prompt_config.get(
            "user", "Format the following markdown content:\n\n{content}"
        )

        # システムプロンプトのトークン数を計算
        system_tokens = self._count_tokens(system_prompt)
        # テンプレートのトークン数（コンテンツ部分を除く）
        template_tokens = self._count_tokens(
            user_prompt_template.replace("{content}", "")
        )

        # コンテンツに使用できるトークン数を計算（余裕を持たせる）
        content_max_tokens = (
            self.max_tokens - system_tokens - template_tokens - 500
        )  # 500はバッファ
        logger.info(f"Max tokens available for content: {content_max_tokens}")

        try:
            # マークダウンを適切なサイズのチャンクに分割
            chunks = split_markdown_to_chunks(
                markdown_content, content_max_tokens, self._count_tokens
            )

            # 並列処理でマークダウンを処理
            return process_markdown_in_parallel(
                chunks,
                self._process_chunk,
                system_prompt,
                user_prompt_template,
                max_workers,
            )

        except Exception as e:
            logger.error(f"Error in format_markdown: {e}")
            # エラーの場合は元のマークダウンを返す
            return markdown_content

    def _get_prompt_for_file_type(self, file_ext):
        """ファイル拡張子に応じたプロンプトを取得する"""
        return get_prompt_for_file_type(self.prompts, file_ext)
