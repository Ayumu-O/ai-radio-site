def filter_relevant_news(llm, news_entries):
    # ニュースのリストを、生成AIに入力できるテキスト形式に整形
    # ニュースのリストは項番を付与され下記の形式に。
    #    1. タイトル：<ニュース1のタイトル>
    #       要約：<ニュース1の要約>
    #    2. タイトル：<ニュース2のタイトル>
    #      ......
    news_text = "\n\n".join(
        [
            f"{i + 1}. タイトル: {news['title']}\n　　要約: {news['summary']}"
            for i, news in enumerate(news_entries)
        ]
    )

    # テキスト形式に整形されたニュースのリストと、指示文を合わせてプロンプトに変換
    prompt = f"""
あなたはAIに関連する情報を収集するためのAIアシスタントです。以下のニュースリストの中から、私の関心に合致するものだけを選んでください。

# 関心のある分野
- AI技術の最新動向
- AIの活用事例
- AIに関連する法規制、ガバナンス

# ニュースリスト
{news_text}

# 出力フォーマット
関心のあるニュースの番号をカンマ区切りで挙げてください（例：1,3,5）
関連するニュースがない場合、「なし」と答えてください。
""".strip()

    # プロンプトをGeminiに入力、関心のあるニュースの項番を返す
    response = llm.invoke(prompt)
    selected_indices = [
        int(i.strip()) - 1 for i in response.content.split(",") if i.strip().isdigit()
    ]

    # 項番の情報を元に、関心のあるニュースのみを集めたリストを返す
    return [news_entries[i] for i in selected_indices if 0 <= i < len(news_entries)]


if __name__ == "__main__":
    from article_collector import get_today_news, rss_urls
    from dotenv import load_dotenv
    from langchain_openai import ChatOpenAI

    load_dotenv()

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, timeout=60, max_retries=2)
    news_entries = get_today_news(rss_urls=rss_urls)
    print("今日のニュースリスト:", [entry["title"] for entry in news_entries])
    filtered_news = filter_relevant_news(llm, news_entries)
    print("関心のあるニュースリスト:", [entry["title"] for entry in filtered_news])
