import os

import requests

# VOICEVOXエンジンのURL
VOICEVOX_URL = "http://localhost:50021"
# ずんだもんのスピーカーID
ZUNDAMON_ID = 1


def text_to_speech(text, output_path):
    """テキストを音声に変換してファイルに保存する"""

    # 音声合成用クエリの作成
    query_params = {"text": text, "speaker": ZUNDAMON_ID}
    query_response = requests.post(f"{VOICEVOX_URL}/audio_query", params=query_params)
    query_response.raise_for_status()
    query_data = query_response.json()

    # 音声合成を実行
    synthesis_params = {"speaker": ZUNDAMON_ID}
    synthesis_response = requests.post(
        f"{VOICEVOX_URL}/synthesis", params=synthesis_params, json=query_data
    )
    synthesis_response.raise_for_status()

    # 音声ファイルを保存
    with open(output_path, "wb") as f:
        f.write(synthesis_response.content)

    print(f"Audio saved to {output_path}")
    return output_path


if __name__ == "__main__":
    # 出力ディレクトリを作成
    os.makedirs("audio", exist_ok=True)

    # サンプル原稿
    sample_script = """
    みなさん、おはようなのだ！ずんだもんだよ！
    今日も「ずんだもんAIポッドキャスト」からお送りするのだ！
    
    今日は2023年6月1日、木曜日なのだ。
    今日は簡単なテスト配信なのだ。本格的な配信は準備が整い次第始めるのだ！
    
    それでは、また明日会おうなのだ～！
    """

    # 音声に変換
    output_file = "audio/test_episode.wav"
    text_to_speech(sample_script, output_file)
