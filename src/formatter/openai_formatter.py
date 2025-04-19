import openai
import logging
import tiktoken
import time
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


class OpenAIMarkdownFormatter(FormatterInterface):
    def __init__(
        self,
        model,
        api_key,
        prompts_file="prompts.yaml",
        max_tokens=3000,
        rate_limit_delay=1.0,
    ):
        # APIキーの設定
        if not api_key:
            raise ValueError(
                "OpenAI API key is required. Set it in .env file or pass as argument"
            )

        # モデルの設定
        self.model = model
        logger.info(f"Using OpenAI model: {self.model}")

        # レート制限の待機時間（秒）
        self.rate_limit_delay = rate_limit_delay
        logger.info(f"API rate limit delay set to {self.rate_limit_delay} seconds")

        # OpenAI clientの初期化
        self.client = openai.OpenAI(api_key=api_key)

        # プロンプト設定ファイルの読み込み
        self.prompts = load_prompts(prompts_file)

        # チャンクサイズ設定（トークン数）
        self.max_tokens = max_tokens

        # トークンカウンターの初期化
        try:
            self.encoding = tiktoken.encoding_for_model(self.model)
            logger.info(f"Using tiktoken encoding for model: {self.model}")
        except KeyError:
            self.encoding = tiktoken.get_encoding("cl100k_base")
            logger.info("Using default cl100k_base encoding")

        logger.info(
            f"OpenAI formatter initialized with max tokens per chunk: {self.max_tokens}"
        )

    def _load_prompts(self, prompts_file):
        """プロンプト設定ファイルを読み込む"""
        return load_prompts(prompts_file)

    def _count_tokens(self, text):
        """テキストのトークン数をカウント"""
        return len(self.encoding.encode(text))

    def _process_chunk(self, chunk, system_prompt, user_prompt_template):
        """単一のチャンクを処理"""
        # ユーザープロンプトにコンテンツを挿入
        user_prompt = user_prompt_template.format(content=chunk)

        try:
            # APIリクエスト送信前に待機
            time.sleep(self.rate_limit_delay)

            # APIリクエスト送信
            logger.info(f"Sending API request to OpenAI ({self.model})...")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )

            # レスポンスからコンテンツを抽出
            formatted_chunk = response.choices[0].message.content
            logger.info(
                f"API request successful, received {len(formatted_chunk)} characters"
            )

            return formatted_chunk

        except Exception as e:
            logger.error(f"Error processing chunk with OpenAI: {e}")
            # エラーの場合は元のチャンクを返す
            return chunk

    def format_markdown(self, markdown_content, file_ext=None, max_workers=4):
        """
        OpenAI APIを使用してマークダウンを整形する（並列処理）

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
