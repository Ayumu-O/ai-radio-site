from datetime import datetime, timedelta, timezone

import feedparser

rss_urls = {
    "Zenn Trend": "https://zenn.dev/feed",
    "Qiita Trend": "https://qiita.com/popular-items/feed.atom",
}


def get_today_news(rss_urls):
    # 本日の新着記事のみを格納する変数
    news_entries = []

    # 今日の日付（日本時間）を取得
    jst = timezone(timedelta(hours=9))
    today = datetime.now(jst).date()

    # RSSフィードを順に巡回
    for rss_source, rss_url in rss_urls.items():
        feed = feedparser.parse(rss_url)

        # RSSフィード内の各記事を巡回
        for entry in feed.entries:
            entry_date = None

            # 公開日または更新日を取得
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                entry_date = datetime(*entry.published_parsed[:6], tzinfo=jst).date()
            elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                entry_date = datetime(*entry.updated_parsed[:6], tzinfo=jst).date()

            # 公開日または更新日が本日の日付である、かつ記事の要約がある場合のみ、記事を保存
            # if entry_date and entry_date == today and entry.summary:
            if entry.summary:
                news_entries.append(
                    {
                        "title": entry.title,
                        "link": entry.link,
                        "summary": entry.summary,
                        "source": rss_source,
                    }
                )

    return news_entries


if __name__ == "__main__":
    news_entries = get_today_news(rss_urls)
    print(news_entries)
