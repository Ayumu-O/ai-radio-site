import argparse
import datetime
import logging
import os
import re
import shutil
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


def extract_links_from_script(script_content):
    """スクリプトから関連リンクを抽出"""
    links = []
    lines = script_content.split("\n")

    # 簡易的なリンク抽出（URLを含む行を探す）
    for line in lines:
        if "http://" in line or "https://" in line:
            # URLとその前のテキストを抽出
            match = re.search(r"(.*?)(https?://[^\s]+)", line)
            if match:
                title = match.group(1).strip()
                url = match.group(2).strip()
                if title:
                    links.append(f"- [{title}]({url})")
                else:
                    links.append(f"- {url}")

    return links


def create_podcast_post(
    title, audio_file, script_file=None, episode_num=None, description=None
):
    """ポッドキャスト記事を作成"""
    logger.info(f"Creating podcast post for: {title}")

    # 出力ディレクトリの確認
    posts_dir = "_posts"
    audio_dir = "audio"
    os.makedirs(posts_dir, exist_ok=True)
    os.makedirs(audio_dir, exist_ok=True)

    # 音声ファイルをaudioディレクトリにコピー
    audio_basename = os.path.basename(audio_file)
    audio_dest_path = os.path.join(audio_dir, audio_basename)

    try:
        shutil.copy(audio_file, audio_dest_path)
        logger.info(f"Copied audio file to: {audio_dest_path}")
    except Exception as e:
        logger.error(f"Failed to copy audio file: {e}")
        audio_dest_path = audio_file  # 元のパスを使用

    # 現在の日時
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    date_time_str = now.strftime("%Y-%m-%d %H:%M:%S +0900")

    # 話数番号（指定がなければファイル名から推測）
    if episode_num is None:
        try:
            # ファイル名からエピソード番号を抽出
            match = re.search(r"(\d+)", os.path.basename(audio_file))
            if match:
                episode_num = int(match.group(1))
            else:
                # 既存の投稿から最大エピソード番号を取得
                max_episode = 0
                for file in os.listdir(posts_dir):
                    if file.endswith(".md"):
                        match = re.search(r"(\d+)", file)
                        if match:
                            episode = int(match.group(1))
                            max_episode = max(max_episode, episode)
                episode_num = max_episode + 1
        except Exception as e:
            logger.warning(f"Could not determine episode number: {e}")
            episode_num = 1

    # 説明文（指定がなければスクリプトから生成）
    if description is None:
        if script_file and os.path.exists(script_file):
            with open(script_file, "r", encoding="utf-8") as f:
                script_content = f.read()

            # スクリプトの最初の数行から説明文を生成
            lines = [
                line
                for line in script_content.split("\n")
                if line.strip() and not line.startswith("#")
            ]
            description = " ".join(lines[:3])[:150] + "..."
        else:
            description = f"ずんだもんがAIやテクノロジーのトレンド記事を紹介する第{episode_num}回目の放送です。"

    # 音声ファイルのサイズを取得
    audio_file_size = get_audio_file_size(audio_file)

    # 音声ファイルの長さを取得
    duration = get_audio_duration(audio_file)

    # リンク情報（スクリプトがある場合）
    links_section = ""
    if script_file and os.path.exists(script_file):
        with open(script_file, "r", encoding="utf-8") as f:
            script_content = f.read()

        links = extract_links_from_script(script_content)
        if links:
            links_section = "## 関連リンク\n\n" + "\n".join(links)

    # フロントマターの作成
    front_matter = {
        "actor_ids": ["zundamon"],
        "audio_file_path": f"/audio/{audio_basename}",
        "audio_file_size": audio_file_size,
        "date": date_time_str,
        "description": description,
        "duration": duration,
        "layout": "article",
        "title": f"{episode_num}. {title}",
    }

    # 投稿ファイル名の作成
    post_filename = f"{date_str}-{episode_num}.md"
    post_path = os.path.join(posts_dir, post_filename)

    # 投稿ファイルの作成
    with open(post_path, "w", encoding="utf-8") as f:
        f.write("---\n")
        yaml.dump(front_matter, f, default_flow_style=False, allow_unicode=True)
        f.write("---\n\n")

        # リンクセクションがあれば追加
        if links_section:
            f.write(links_section + "\n\n")

    logger.info(f"Created podcast post at: {post_path}")
    return post_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload podcast episode to yattecast")
    parser.add_argument(
        "--title", default="ずんだもんAIラジオ", help="Podcast episode title"
    )
    parser.add_argument("--audio", required=True, help="Path to audio file")
    parser.add_argument("--script", help="Path to script file (optional)")
    parser.add_argument("--episode", type=int, help="Episode number (optional)")
    parser.add_argument("--description", help="Episode description (optional)")

    args = parser.parse_args()

    create_podcast_post(
        title=args.title,
        audio_file=args.audio,
        script_file=args.script,
        episode_num=args.episode,
        description=args.description,
    )

    print("\nポッドキャストエピソードが作成されました")
    print("この変更をGitHubにプッシュするには:")
    print("git add _posts/ audio/")
    print('git commit -m "Add new podcast episode"')
    print("git push origin main")
