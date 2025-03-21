from datetime import datetime
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate


def generate_radio_script(
    llm: BaseChatModel,
    articles: list[dict[str, Any]],
) -> str:
    """ラジオ番組の原稿全体を生成する"""
    # 日付と曜日の情報
    date_str = datetime.now().strftime("%Y年%m月%d日")
    weekday = ["月", "火", "水", "木", "金", "土", "日"][datetime.now().weekday()]

    # LLMへのプロンプト
    prompt = ChatPromptTemplate.from_messages(
        messages=[
            {
                "role": "system",
                "content": """
あなたは「ずんだもんAIポッドキャスト」のAIアシスタントです。
AIやテクノロジーに関するトレンド記事を紹介するラジオ番組を制作しています。
ずんだもんキャラクターの口調で、わかりやすく楽しい内容を心がけてください。
""",
            },
            {
                "role": "user",
                "content": """
あなたは「ずんだもんAIポッドキャスト」のAIラジオの番組原稿を作成するアシスタントです。
今日の放送（{date_str}（{weekday}））のラジオ原稿を作成してください。

番組情報:
- パーソナリティ: ずんだもん
- 内容: AIやテクノロジーに関するトレンド記事の紹介
- スタイル: 親しみやすく、初心者にもわかりやすい説明

以下の内容を含めて原稿を作成してください:
1. オープニング（挨拶、今日の番組内容紹介）
2. 記事紹介コーナー（各記事の要約と解説）
3. エンディング（まとめ、次回予告、お別れの挨拶）

原稿はずんだもんキャラクターの口調で書いてください。語尾には「〜のだ」「〜なのだ」を使います。
また、「記事1: タイトル」のように明確に記事の区切りを示してください。

記事情報:
{articles_text}

""",
            },
        ]
    )

    # LLMで原稿を生成
    chain = prompt | llm
    response = chain.invoke(
        input={
            "date_str": date_str,
            "weekday": weekday,
            "articles_text": "\n".join(
                [f"{i + 1}. {article['title']}" for i, article in enumerate(articles)]
            ),
        }
    )
    return response.content


if __name__ == "__main__":
    from article_collector import get_today_news, rss_urls
    from article_selector import filter_relevant_news
    from article_summarizer import summarize_articles
    from dotenv import load_dotenv
    from langchain_openai import ChatOpenAI

    load_dotenv()

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
    print("ラジオ原稿:")
    with open("radio_script.txt", "w", encoding="utf-8") as f:
        f.write(radio_script)
    print(radio_script)
