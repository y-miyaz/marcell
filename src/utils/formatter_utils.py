import os
import yaml
import re
import concurrent.futures
import time
import logging
from utils.logging_config import setup_logging

# ロガーの取得
logger = logging.getLogger(__name__)


def load_prompts(prompts_file):
    """
    プロンプト設定ファイルを読み込む

    Args:
        prompts_file: プロンプト設定ファイルのパス

    Returns:
        dict: 読み込まれたプロンプト設定
    """
    try:
        with open(prompts_file, "r", encoding="utf-8") as f:
            prompts = yaml.safe_load(f)
        logger.info(f"Successfully loaded prompts from {prompts_file}")
        return prompts
    except Exception as e:
        logger.error(f"Failed to load prompts from {os.getcwd()}/{prompts_file}: {e}")
        raise


def get_prompt_for_file_type(prompts, file_ext):
    """
    ファイル拡張子に応じたプロンプトを取得する

    Args:
        prompts: プロンプト設定辞書
        file_ext: ファイル拡張子

    Returns:
        dict: ファイル拡張子に対応するプロンプト設定
    """
    # 拡張子から.を除去して小文字に変換
    ext = file_ext.lstrip(".").lower() if file_ext else "default"

    logger.info(f"Selecting prompt for file type: {ext}")

    # 拡張子に対応するプロンプトを取得
    if ext in prompts:
        logger.info(f"Using prompt for {ext}")
        return prompts[ext]
    elif ext in ["xlsx", "xls", "xlsm"] and "excel" in prompts:
        logger.info(f"Using 'excel' prompt for {ext}")
        return prompts["excel"]
    else:
        logger.info(f"No specific prompt found for {ext}, using default prompt")
        return prompts["default"]


def split_markdown_to_chunks(markdown_content, max_tokens, count_tokens_func):
    """
    マークダウンを論理的なチャンクに分割する

    Args:
        markdown_content: 分割するマークダウンコンテンツ
        max_tokens: チャンクあたりの最大トークン数
        count_tokens_func: トークン数カウント関数（異なるモデル用に実装を渡す）

    Returns:
        list: マークダウンのチャンクリスト
    """
    # まずは見出しでセクションを分割
    section_pattern = r"(?=^#{1,6}\s+.+$)"
    sections = re.split(section_pattern, markdown_content, flags=re.MULTILINE)

    logger.info(f"Split markdown into {len(sections)} initial sections")

    chunks = []
    current_chunk = ""
    current_token_count = 0

    for section in sections:
        if not section.strip():
            continue
        # セクションのトークン数をカウント
        section_tokens = count_tokens_func(section)

        # セクション自体が大きすぎる場合は、段落で分割
        if section_tokens > max_tokens:
            # 段落で分割
            paragraphs = re.split(r"\n\s*\n", section)
            for para in paragraphs:
                para_tokens = count_tokens_func(para)

                # 1つの段落が制限を超える場合は、行で分割
                if para_tokens > max_tokens:
                    lines = para.split("\n")
                    for line in lines:
                        line_tokens = count_tokens_func(line)

                        # 現在のチャンクにこの行を追加するとトークン制限を超える場合、新しいチャンクを開始
                        if (
                            current_token_count + line_tokens > max_tokens
                            and current_chunk
                        ):
                            chunks.append(current_chunk.strip())
                            current_chunk = line
                            current_token_count = line_tokens
                        else:
                            current_chunk += line + "\n"
                            current_token_count += line_tokens

                # 現在のチャンクにこの段落を追加するとトークン制限を超える場合、新しいチャンクを開始
                elif current_token_count + para_tokens > max_tokens and current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = para
                    current_token_count = para_tokens
                else:
                    current_chunk += para + "\n\n"
                    current_token_count += para_tokens

        # 現在のチャンクにこのセクションを追加するとトークン制限を超える場合、新しいチャンクを開始
        elif current_token_count + section_tokens > max_tokens and current_chunk:
            chunks.append(current_chunk.strip())
            current_chunk = section
            current_token_count = section_tokens
        else:
            current_chunk += section
            current_token_count += section_tokens

    # 最後のチャンクを追加
    if current_chunk:
        chunks.append(current_chunk.strip())

    logger.info(f"Final split: {len(chunks)} chunks for processing")
    return chunks


def process_markdown_in_parallel(
    chunks, process_chunk_func, system_prompt, user_prompt_template, max_workers=4
):
    """
    マークダウンのチャンクを並列処理する

    Args:
        chunks: マークダウンのチャンクリスト
        process_chunk_func: 各チャンクを処理するメソッド
        system_prompt: システムプロンプト
        user_prompt_template: ユーザープロンプトテンプレート
        max_workers: 並列処理の最大ワーカー数

    Returns:
        str: 処理済みのマークダウンコンテンツ
    """
    start_time = time.time()
    chunk_count = len(chunks)
    logger.info(
        f"Processing {chunk_count} chunks in parallel using {max_workers} workers"
    )

    # ThreadPoolExecutorを使って並列処理
    formatted_chunks = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 各チャンクの処理をサブミット
        future_to_index = {
            executor.submit(
                process_chunk_func, chunk, system_prompt, user_prompt_template
            ): i
            for i, chunk in enumerate(chunks)
        }

        # 完了したものから結果を取得
        for future in concurrent.futures.as_completed(future_to_index):
            index = future_to_index[future]
            try:
                result = future.result()
                # インデックスと結果を記録（後で正しい順序で結合するため）
                formatted_chunks.append((index, result))
                logger.info(f"Completed chunk {index + 1}/{chunk_count}")
            except Exception as e:
                logger.error(f"Error processing chunk {index}: {e}")
                # エラーの場合は元のチャンクを使用
                formatted_chunks.append((index, chunks[index]))

    # インデックスでソートして元の順序を維持
    formatted_chunks.sort(key=lambda x: x[0])
    ordered_results = [chunk for _, chunk in formatted_chunks]

    # 処理されたチャンクを結合
    formatted_markdown = "\n\n".join(ordered_results)

    elapsed = time.time() - start_time
    logger.info(
        f"Parallel processing completed in {elapsed:.2f}s for {chunk_count} chunks"
    )
    return formatted_markdown
