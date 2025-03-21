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
    import os

    from article_collector import get_today_news, rss_urls
    from article_selector import filter_relevant_news
    from article_summarizer import summarize_articles
    from dotenv import load_dotenv
    from langchain_openai import ChatOpenAI
    from script_generator import generate_radio_script

    load_dotenv()

    # 出力ディレクトリを作成
    os.makedirs("audio", exist_ok=True)
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, timeout=60, max_retries=2)
    news_entries = get_today_news(rss_urls=rss_urls)
    print("今日のニュースリスト:", [entry["title"] for entry in news_entries])
    print()
    filtered_news = filter_relevant_news(llm, news_entries)
    print("関心のあるニュースリスト:", [entry["title"] for entry in filtered_news])
    print()
    summarized_news = summarize_articles(llm, filtered_news)
    print("ニュース要約完了")
    print()
    radio_script = generate_radio_script(llm, summarized_news)
    print("ラジオ原稿作成完了")

    # 音声に変換
    output_file = "audio/test_episode.wav"
    text_to_speech(radio_script, output_file)
