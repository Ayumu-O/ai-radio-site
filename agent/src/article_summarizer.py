import copy
import logging

import requests
from bs4 import BeautifulSoup
from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel

# ロギング設定
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class Summary(BaseModel):
    summary: str


def fetch_article_content(url: str) -> str:
    """記事のURLからコンテンツを取得する"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        return response.text
    except Exception as e:
        logger.error(f"Error fetching article content from {url}: {e}")
        return ""


def extract_article_text(html_content: str, source: str) -> str:
    """HTMLから記事の本文テキストを抽出する"""
    try:
        soup = BeautifulSoup(html_content, "html.parser")

        # サイトに応じた抽出方法
        if "zenn.dev" in source:
            article_element = soup.select_one("article.article")
            if article_element:
                # 不要な要素を除外
                for element in article_element.select("pre, code, script, style"):
                    element.decompose()
                return article_element.get_text(separator="\n").strip()

        elif "qiita.com" in source:
            article_element = soup.select_one(".it-MdContent")
            if article_element:
                # 不要な要素を除外
                for element in article_element.select("pre, code, script, style"):
                    element.decompose()
                return article_element.get_text(separator="\n").strip()

        # 他のサイトの場合は一般的な方法で抽出
        article_element = (
            soup.select_one("article")
            or soup.select_one(".article")
            or soup.select_one(".post-content")
        )
        if article_element:
            # 不要な要素を除外
            for element in article_element.select("pre, code, script, style"):
                element.decompose()
            return article_element.get_text(separator="\n").strip()

        # 一般的なコンテンツの抽出
        main_element = (
            soup.select_one("main")
            or soup.select_one("#main")
            or soup.select_one(".main-content")
        )
        if main_element:
            # 不要な要素を除外
            for element in main_element.select("pre, code, script, style"):
                element.decompose()
            return main_element.get_text(separator="\n").strip()

        # それでも取得できない場合はbodyから
        body = soup.select_one("body")
        if body:
            # 不要な要素を除外
            for element in body.select(
                "header, footer, nav, aside, pre, code, script, style"
            ):
                element.decompose()
            return body.get_text(separator="\n").strip()

        return ""
    except Exception as e:
        logger.error(f"Error extracting article text: {e}")
        return ""


def prepare_batch_inputs(news_entries):
    """記事からバッチ処理用の入力を準備する"""
    batch_inputs = []
    article_indices = []
    processed_entries = copy.deepcopy(news_entries)

    for i, entry in enumerate(processed_entries):
        html_content = fetch_article_content(entry["link"])
        if not html_content:
            entry["ai_summary"] = entry["summary"]
            continue

        article_text = extract_article_text(html_content, entry["link"])
        if not article_text or len(article_text) < 100:
            entry["ai_summary"] = entry["summary"]
            continue

        # 長すぎる記事は切り詰める
        if len(article_text) > 15000:
            article_text = article_text[:15000] + "..."

        # バッチ処理用の入力を追加
        batch_inputs.append(
            {
                "title": entry["title"],
                "source": entry["link"],
                "article_text": article_text,
            }
        )
        article_indices.append(i)

    return processed_entries, batch_inputs, article_indices


def create_summary_prompt():
    """要約用のプロンプトを作成する"""
    return ChatPromptTemplate.from_messages(
        [
            {
                "role": "user",
                "content": """
以下の記事を、ラジオ放送で紹介するための要約にしてください。
- 要約は5-7分で読み上げられる量にしてください（約1000-1500字程度）。
- 記事の主要なポイント、なぜこの話題が重要なのか、読者にとってのメリットを含めてください。
- 具体的なデータや数字、例があれば含めてください。
- 専門用語は簡単に説明してください。

記事タイトル: {title}
記事ソース: {source}

記事本文:
{article_text}
""".strip(),
            }
        ]
    )


def process_batch_results(summarized_entries, batch_results, article_indices):
    """バッチ処理の結果を元の記事リストに反映する"""
    for i, result_index in enumerate(article_indices):
        if i < len(batch_results):
            summarized_entries[result_index]["ai_summary"] = batch_results[i].summary
        else:
            summarized_entries[result_index]["ai_summary"] = summarized_entries[
                result_index
            ]["summary"]

    return summarized_entries


def summarize_articles(llm: BaseChatModel, news_entries):
    """記事リストをバッチで要約する"""
    # バッチ処理の準備
    summarized_entries, batch_inputs, article_indices = prepare_batch_inputs(
        news_entries
    )

    # バッチ処理する記事がない場合は終了
    if not batch_inputs:
        return summarized_entries

    # プロンプトの準備
    prompt = create_summary_prompt()

    # バッチ処理を実行
    try:
        sllm = llm.with_structured_output(Summary)
        chain = prompt | sllm
        batch_results = chain.batch(batch_inputs)

        # 結果を元の記事リストに反映
        summarized_entries = process_batch_results(
            summarized_entries, batch_results, article_indices
        )
    except Exception as e:
        logging.error(f"バッチ処理中にエラーが発生しました: {e}")
        # エラー時は元の要約を使用
        for result_index in article_indices:
            summarized_entries[result_index]["ai_summary"] = summarized_entries[
                result_index
            ]["summary"]

    return summarized_entries


if __name__ == "__main__":
    from article_collector import get_today_news, rss_urls
    from article_selector import filter_relevant_news
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
    print("要約済みニュースリスト:")
    for entry in summarized_news:
        print(f"タイトル: {entry['title']}\n要約: {entry['ai_summary']}\n")
