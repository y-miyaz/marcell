import logging


def setup_logging(level=logging.INFO):
    """
    プロジェクト全体で使用する共通のロギング設定

    Args:
        level: ロギングレベル（デフォルトはINFO）

    Returns:
        logging.Logger: 設定済みロガー
    """
    # ロギング設定が複数回実行されることを防ぐ
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=level,
            format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    return logging.getLogger(__name__)


# デフォルトロガーを設定
logger = logging.getLogger(__name__)
