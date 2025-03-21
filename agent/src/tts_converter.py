import logging
import os
import subprocess
import tempfile

import requests

# ロギング設定
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# VOICEVOXエンジンのURL
VOICEVOX_URL = "http://localhost:50021"
# ずんだもんのスピーカーID
ZUNDAMON_ID = 1


def generate_audio_for_text(text, speaker_id):
    """テキストから音声データを生成する"""
    logger.debug(f"テキスト「{text[:30]}...」の音声合成を開始")

    # 音声合成用クエリの作成
    query_params = {"text": text, "speaker": speaker_id}
    try:
        logger.debug("音声合成クエリを作成中")
        query_response = requests.post(
            f"{VOICEVOX_URL}/audio_query", params=query_params
        )
        query_response.raise_for_status()
        query_data = query_response.json()

        # 音声合成を実行
        logger.debug("音声を合成中")
        synthesis_params = {"speaker": speaker_id}
        synthesis_response = requests.post(
            f"{VOICEVOX_URL}/synthesis", params=synthesis_params, json=query_data
        )
        synthesis_response.raise_for_status()

        logger.debug(f"テキスト「{text[:30]}...」の音声合成が完了")
        return synthesis_response.content
    except requests.RequestException as e:
        logger.error(f"VOICEVOXサーバーとの通信中にエラーが発生: {e}")
        raise


def text_to_speech(text, output_path, speaker_id=ZUNDAMON_ID):
    """テキストを音声に変換してファイルに保存する"""
    logger.info(f"音声合成を開始: 出力先={output_path}")

    # テキストを改行で分割
    lines = [line.strip() for line in text.split("\n") if line.strip()]

    if not lines:
        logger.warning("変換するテキストがありません")
        return None

    logger.info(f"合計 {len(lines)} 行のテキストを処理します")

    # 一時ディレクトリを作成
    with tempfile.TemporaryDirectory() as temp_dir:
        logger.debug(f"一時ディレクトリを作成: {temp_dir}")
        temp_files = []

        # 各行を音声に変換
        for i, line in enumerate(lines):
            logger.info(f"処理中: 行 {i + 1}/{len(lines)}")
            try:
                audio_data = generate_audio_for_text(line, speaker_id)

                # 一時ファイルに保存
                temp_file = os.path.join(temp_dir, f"line_{i:04d}.wav")
                with open(temp_file, "wb") as f:
                    f.write(audio_data)

                temp_files.append(temp_file)
                logger.debug(f"一時ファイルを保存: {temp_file}")
            except Exception as e:
                logger.error(f"行 '{line}' の処理中にエラーが発生しました: {e}")

        # 音声ファイルを結合
        if temp_files:
            # 出力ディレクトリが存在しない場合は作成
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                logger.debug(f"出力ディレクトリを作成: {output_dir}")
                os.makedirs(output_dir)

            # ffmpegのconcat用のファイルリストを作成
            concat_list_path = os.path.join(temp_dir, "concat_list.txt")
            with open(concat_list_path, "w") as f:
                for temp_file in temp_files:
                    f.write(f"file '{temp_file}'\n")

            logger.info(f"FFmpegを使用して {len(temp_files)} 個の音声ファイルを結合中")

            # ffmpegを使って結合
            try:
                ffmpeg_command = [
                    "ffmpeg",
                    "-f",
                    "concat",
                    "-safe",
                    "0",
                    "-i",
                    concat_list_path,
                    "-c",
                    "copy",
                    output_path,
                ]
                logger.debug(f"実行コマンド: {' '.join(ffmpeg_command)}")

                # FFmpegの出力をキャプチャして、エラー時にログに記録
                process = subprocess.run(
                    ffmpeg_command,
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )

                logger.info(f"音声が {output_path} に保存されました")
                logger.debug(f"FFmpeg出力: {process.stderr}")
                return output_path
            except Exception as e:
                logger.error(f"FFmpegでの結合中にエラーが発生しました: {e}")
                logger.error(f"FFmpeg出力: {e.stderr}")
                return None
        else:
            logger.warning("音声ファイルが生成されませんでした")
            return None


if __name__ == "__main__":
    import os
    from argparse import ArgumentParser

    from article_collector import get_today_news, rss_urls
    from article_selector import filter_relevant_news
    from article_summarizer import summarize_articles
    from dotenv import load_dotenv
    from langchain_openai import ChatOpenAI
    from script_generator import generate_radio_script

    load_dotenv()

    parser = ArgumentParser(description="Generate radio script from news articles")
    parser.add_argument("--script", help="Path to read the radio script")
    parser.add_argument(
        "--output", default="audio/test_episode.wav", help="Path to save the audio file"
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    # デバッグモードが有効な場合はログレベルを変更
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logger.debug("デバッグモードが有効になりました")

    if args.script:
        script_file = args.script
        logger.info(f"指定されたスクリプトファイルを読み込み: {script_file}")
        with open(script_file, "r", encoding="utf-8") as f:
            radio_script = f.read()
    else:
        # 出力ディレクトリを作成
        os.makedirs("audio", exist_ok=True)
        logger.info("ニュース記事を取得して処理します")

        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, timeout=60, max_retries=2)
        news_entries = get_today_news(rss_urls=rss_urls)
        logger.info(f"今日のニュースリスト: {len(news_entries)}件")

        filtered_news = filter_relevant_news(llm, news_entries)
        logger.info(f"関心のあるニュースリスト: {len(filtered_news)}件")

        summarized_news = summarize_articles(llm, filtered_news)
        logger.info("ニュース要約完了")

        radio_script = generate_radio_script(llm, summarized_news)
        logger.info("ラジオ原稿作成完了")

    # 音声に変換
    text_to_speech(radio_script, args.output)
