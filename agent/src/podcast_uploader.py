import argparse
import logging
import os
from datetime import datetime

import yaml

# ロギング設定
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def get_audio_file_size(file_path):
    """オーディオファイルのサイズ（バイト）を取得"""
    try:
        return os.path.getsize(file_path)
    except Exception as e:
        logger.error(f"Error getting audio file size: {e}")
        return 0


def get_audio_duration(file_path):
    """オーディオファイルの時間を取得（実際には音声解析が必要）"""
    # この実装は仮のもの。実際はffprobeなどを使用して正確な時間を取得する
    try:
        # ffprobeがあれば使用
        import subprocess

        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                file_path,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        duration_seconds = float(result.stdout.strip())
        minutes = int(duration_seconds // 60)
        seconds = int(duration_seconds % 60)
        return f"{minutes:02d}:{seconds:02d}"
    except Exception as e:
        logger.warning(f"Could not determine audio duration: {e}")
        return "00:00"


def create_podcast_post(audio_file, title=None, description=None, content=None):
    """ポッドキャスト記事を作成"""
    # 現在の日時
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    date_time_str = now.strftime("%Y-%m-%d %H:%M:%S +0900")

    # タイトル
    if title is None:
        title = f"Zundamon AI Podcast {date_str}"

    # 説明文
    if description is None:
        description = f"{date_str}: ずんだもんがAIやテクノロジーのトレンド記事を紹介する放送です。"

    # コンテンツ
    if content is None:
        content = description

    logger.info(f"Creating podcast post for: {title}")

    # 出力ディレクトリの確認
    posts_dir = "_posts"
    audio_dir = "audio"
    os.makedirs(posts_dir, exist_ok=True)
    os.makedirs(audio_dir, exist_ok=True)

    # 音声ファイルのサイズを取得
    audio_file_size = get_audio_file_size(audio_file)

    # 音声ファイルの長さを取得
    duration = get_audio_duration(audio_file)

    # フロントマターの作成
    front_matter = {
        "actor_ids": ["zundamon"],
        "audio_file_path": "/" + audio_file,
        "audio_file_size": audio_file_size,
        "date": date_time_str,
        "description": description,
        "duration": f'"{duration}"',
        "layout": "article",
        "title": f"Zundamon AI Podcast {date_str}",
    }

    # 投稿ファイル名の作成
    # 同じ日付の投稿がある場合は番号を増やしていく
    existing_posts = [f for f in os.listdir(posts_dir) if f.startswith(f"{date_str}-")]
    number = len(existing_posts) + 1
    post_filename = f"{date_str}-{number}.md"
    post_path = os.path.join(posts_dir, post_filename)

    # 投稿ファイルの作成
    with open(post_path, "w", encoding="utf-8") as f:
        f.write("---\n")
        yaml.dump(front_matter, f, default_flow_style=False, allow_unicode=True)
        f.write("---\n\n")
        f.write(content + "\n\n")

    logger.info(f"Created podcast post at: {post_path}")
    return post_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload podcast episode to yattecast")
    parser.add_argument("--audio", required=True, help="Path to audio file")
    parser.add_argument("--title", help="Podcast episode title")
    parser.add_argument("--description", help="Episode description (optional)")

    args = parser.parse_args()

    create_podcast_post(
        title=args.title,
        audio_file=args.audio,
        description=args.description,
    )

    print("\nポッドキャストエピソードが作成されました")
    print("この変更をGitHubにプッシュするには:")
    print("git add _posts/ audio/")
    print('git commit -m "Add new podcast episode"')
    print("git push origin main")
