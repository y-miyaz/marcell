import pandas as pd
import os
import re
import logging
import warnings
from converter.converter_interface import ConverterInterface
from utils.logging_config import setup_logging

# ロガーの取得
logger = logging.getLogger(__name__)

# openpyxlのデータ検証に関する警告を抑制
warnings.filterwarnings(
    "ignore",
    category=UserWarning,
    message="Data Validation extension is not supported and will be removed",
)
# FutureWarningも抑制
warnings.filterwarnings(
    "ignore",
    category=FutureWarning,
    message="Setting an item of incompatible dtype is deprecated",
)


class ExcelToMarkdownConverter(ConverterInterface):
    def __init__(self):
        pass

    def read_file(self, file_path):
        """
        様々な形式のファイルを読み込む
        """
        file_ext = os.path.splitext(file_path)[1].lower()

        try:
            # Excelファイル
            if file_ext in [".xlsx", ".xls", ".xlsm"]:
                return self.read_excel(file_path)

            # その他のサポートされていない形式
            else:
                logger.error(f"Unsupported file format: {file_ext}")
                return None

        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return None

    def read_excel(self, excel_path):
        """
        Excelファイルを読み込む
        """
        try:
            # ファイル拡張子に基づいてエンジンを明示的に選択
            file_ext = os.path.splitext(excel_path)[1].lower()
            engine = "openpyxl" if file_ext in [".xlsx", ".xlsm"] else "xlrd"

            # エンジンを明示的に指定してExcelファイル内の全シートの辞書を取得
            excel_data = pd.read_excel(excel_path, sheet_name=None, engine=engine)
            return excel_data
        except Exception as e:
            logger.error(f"Error reading Excel file: {e}")
            return None

    def _clean_dataframe(self, df):
        """
        DataFrameをクリーニングして、不要な値や列を削除する
        (修正版: 行の値に 'Unnamed' が含まれる行のみ削除)
        """
        if df.empty:
            return df

        # nanを空文字列に変換
        df = df.fillna("")

        # 'nan'やNaTという文字列をチェックして空文字に変換
        for col in df.columns:
            df[col] = df[col].apply(
                lambda x: "" if (str(x).lower() == "nan" or str(x) == "NaT") else x
            )

        # 空文字しか無い行を削除する
        rows_to_drop = []
        for i, row in df.iterrows():
            if all(str(val) == "" for val in row):
                rows_to_drop.append(i)

        if rows_to_drop:
            df = df.drop(index=rows_to_drop)

        # 1) 行の値に "Unnamed" が含まれる場合、その行を削除
        rows_to_drop_unnamed = []
        for i, row in df.iterrows():
            if any("Unnamed" in str(val) for val in row):
                rows_to_drop_unnamed.append(i)

        if rows_to_drop_unnamed:
            df = df.drop(index=rows_to_drop_unnamed)

        # 3) ヘッダ以外の値がすべて空文字の場合、その列を削除
        all_empty_cols = [col for col in df.columns if df[col].astype(str).eq("").all()]
        if all_empty_cols:
            df = df.drop(columns=all_empty_cols)

        # 2) 各行を左詰め（最初に出現する空文字以外の要素より右側を詰める）
        for i in df.index:
            # 行データを文字列に変換してリスト化
            row_data = df.loc[i].astype(str).tolist()
            # 最初の「空文字以外」の位置を探す
            first_non_empty_idx = None
            for idx, val in enumerate(row_data):
                if val != "":
                    first_non_empty_idx = idx
                    break

            if first_non_empty_idx is not None:
                # 左側(最初の非空セルまで)はそのまま
                left_part = row_data[:first_non_empty_idx]
                # 右側(最初の非空セル以降)
                right_part = row_data[first_non_empty_idx:]

                # 右側から空文字を除いたものを前に詰め、その残りを空文字に
                non_empty = [val for val in right_part if val != ""]
                num_empty = len(right_part) - len(non_empty)
                new_right_part = non_empty + ([""] * num_empty)

                # 左詰めした新たな行を再構築
                new_row_data = left_part + new_right_part

                # 列の数に合わせて長さを調整（念のため）
                if len(new_row_data) < len(df.columns):
                    new_row_data += [""] * (len(df.columns) - len(new_row_data))
                elif len(new_row_data) > len(df.columns):
                    new_row_data = new_row_data[: len(df.columns)]

                # 変更をDataFrameに反映 (FutureWarning修正)
                # df.loc[i, :] = new_row_data の代わりに
                try:
                    # 各列のデータ型を保持するための新しい方法
                    for col_idx, col in enumerate(df.columns):
                        if col_idx < len(new_row_data):
                            df.at[i, col] = new_row_data[col_idx]
                except Exception as e:
                    logger.warning(f"データ型変換エラー (行 {i}): {e}")
                    # エラーが発生した場合は元の行をそのまま維持
        return df

    def _dataframe_to_markdown(self, df):
        """
        DataFrameをマークダウン形式のテーブルに変換
        """
        if df.empty:
            return ""

        # データフレームをクリーニング
        df = self._clean_dataframe(df)

        # クリーニング後に空になった場合
        if df.empty or len(df.columns) == 0:
            return ""

        # pandasのto_markdownメソッドを使用
        markdown_text = df.to_markdown(index=False)

        # パイプ文字(|)の前後の余分なスペースを削除（行を分割して処理）
        lines = markdown_text.split("\n")
        processed_lines = []

        for line in lines:
            if line.strip():  # 空行でない場合のみ処理
                # 行の中央部分のパイプ前後のスペース削除: " | " → "|"
                processed_line = re.sub(r"(?<=\S)\s+\|\s+(?=\S)", "|", line)
                # 行頭のパイプ記号の後のスペース削除: "| " → "|"
                processed_line = re.sub(r"^\|\s+", "|", processed_line)
                # 行末のパイプ記号の前のスペース削除: " |" → "|"
                processed_line = re.sub(r"\s+\|$", "|", processed_line)
                processed_lines.append(processed_line)
            else:
                # 空行はそのまま追加
                processed_lines.append(line)

        # 処理した行を改行コードで結合して戻す
        return "\n".join(processed_lines)

    def _create_heading(self, text, level=2):
        """
        見出しを作成
        """
        return "#" * level + " " + text

    def _create_horizontal_rule(self):
        """
        水平線を作成
        """
        return "---"

    def convert_to_markdown(self, data, include_titles=True, file_ext=None):
        """
        データをMarkdown形式に変換

        Args:
            data: 変換するデータ
            include_titles: タイトルを含めるかどうか
            file_ext: 元のファイル拡張子（OpenAIプロンプト選択に使用）
        """
        if not data:
            return ""

        markdown_content = ""
        sheet_names = list(data.keys())

        # 各シート/データセットを処理
        for i, sheet_name in enumerate(sheet_names):
            df = data[sheet_name]

            # データセット名をH2見出しとして追加
            if include_titles:
                markdown_content += self._create_heading(sheet_name, level=2) + "\n\n"

            # DataFrameをクリーニング
            cleaned_df = self._clean_dataframe(df)

            # 空のデータフレームになった場合はスキップ
            if cleaned_df.empty or len(cleaned_df.columns) == 0:
                continue

            # DataFrameをMarkdown形式に変換
            table_md = self._dataframe_to_markdown(cleaned_df)

            # 生成されたマークダウンが空でないか確認
            if table_md.strip():
                markdown_content += table_md + "\n\n"

                # 最後のデータセット以外ではシート間の区切り線を追加
                if i < len(sheet_names) - 1:
                    markdown_content += self._create_horizontal_rule() + "\n\n"
        return markdown_content

    def save_markdown(self, markdown_content, output_path):
        """
        Markdown内容をファイルに保存
        """
        try:
            # 出力先ディレクトリを作成（存在しない場合）
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)
            logger.info(f"Markdown file successfully saved to: {output_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving Markdown file: {e}")
            return False

    def convert_file_to_markdown(self, file_path, output_path=None):
        """
        ファイルをMarkdownに変換して保存する
        """
        if not output_path:
            # 出力ファイル名が指定されていない場合、入力ファイル名を基に生成
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            output_path = f"{base_name}.md"

        # ファイルの拡張子を取得
        _, file_ext = os.path.splitext(file_path)

        # ファイルの読み込み
        data = self.read_file(file_path)
        if not data:
            # データが取得できない場合は空の文字列を返す（boolではなく）
            return ""

        # Markdownコンテンツの生成（ファイル拡張子を渡す）
        markdown_content = self.convert_to_markdown(data, file_ext=file_ext)

        # Markdownコンテンツを返す
        return markdown_content
