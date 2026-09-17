"""구글 뉴스 RSS 게이트웨이 파싱 검증 — 실응답(2026-09-16 표본) 기반 픽스처, 네트워크 미사용."""

from datetime import datetime

from apps.news.adapter.outbound.gateways.google_news_gateway import parse_feed

# 실응답 표본 축약 — 파싱에 쓰는 요소는 실제 태그·형식 그대로
_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/">
<channel>
<title>"서문시장 상권" - Google 뉴스</title>
<item>
<title>[사라지는 가게] 서문시장·청라언덕 1층 상가 5곳 중 1곳 공실…문 연 곳도 썰렁 - 매일신문</title>
<link>https://news.google.com/rss/articles/CBMiYkFV?oc=5</link>
<guid isPermaLink="false">CBMiYkFV</guid>
<pubDate>Mon, 03 Aug 2026 07:00:00 GMT</pubDate>
<description>&lt;a href="https://news.google.com/rss/articles/CBMiYkFV?oc=5" target="_blank"&gt;[사라지는 가게] 서문시장·청라언덕 1층 상가 5곳 중 1곳 공실…문 연 곳도 썰렁&lt;/a&gt;&amp;nbsp;&amp;nbsp;&lt;font color="#6f6f6f"&gt;매일신문&lt;/font&gt;</description>
<source url="https://www.imaeil.com">매일신문</source>
</item>
<item>
<title>[대구 전통상권은 지금] 전통상권, 침체 장기화 - 구조적 변화 - 대구일보</title>
<link>https://news.google.com/rss/articles/CBMiaEFV?oc=5</link>
<guid isPermaLink="false">CBMiaEFV</guid>
<pubDate>Tue, 14 Apr 2026 07:00:00 GMT</pubDate>
<description>&lt;a href="https://news.google.com/rss/articles/CBMiaEFV?oc=5"&gt;[대구 전통상권은 지금] 전통상권, 침체 장기화 - 구조적 변화&lt;/a&gt;&amp;nbsp;&amp;nbsp;&lt;font color="#6f6f6f"&gt;대구일보&lt;/font&gt;</description>
<source url="https://www.idaegu.com">대구일보</source>
</item>
</channel>
</rss>"""

_EMPTY_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>"없는키워드" - Google 뉴스</title></channel></rss>"""


def test_parse_feed_maps_real_rss_item():
    articles = parse_feed(_FEED, keyword="서문시장 상권")
    first = articles[0]
    assert len(articles) == 2
    assert first.title == "[사라지는 가게] 서문시장·청라언덕 1층 상가 5곳 중 1곳 공실…문 연 곳도 썰렁"  # " - 언론사" 접미 제거
    assert first.press == "매일신문"
    assert first.url == "https://news.google.com/rss/articles/CBMiYkFV?oc=5"
    assert first.published_at == datetime(2026, 8, 3, 16, 0)  # GMT → KST naive (네이버 어댑터와 동일 기준)
    assert first.matched_keyword == "서문시장 상권"
    assert first.description == "[사라지는 가게] 서문시장·청라언덕 1층 상가 5곳 중 1곳 공실…문 연 곳도 썰렁 매일신문"  # 태그·엔티티 제거
    assert len(first.article_id) == 20
    assert first.article_id != articles[1].article_id


def test_parse_feed_strips_only_trailing_press_suffix():
    second = parse_feed(_FEED, keyword="k")[1]
    assert second.title == "[대구 전통상권은 지금] 전통상권, 침체 장기화 - 구조적 변화"
    assert second.press == "대구일보"


_FEED_MISSING_PUBDATE = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>"동성로 상권" - Google 뉴스</title>
<item>
<title>발행일 없는 기사 - 어느신문</title>
<link>https://news.google.com/rss/articles/NOPUBDATE?oc=5</link>
<description>발행일 없는 기사</description>
<source url="https://example.com">어느신문</source>
</item>
<item>
<title>동성로 상권 회복 - 대구일보</title>
<link>https://news.google.com/rss/articles/WITHPUBDATE?oc=5</link>
<pubDate>Tue, 15 Sep 2026 01:00:00 GMT</pubDate>
<description>동성로 상권 회복</description>
<source url="https://www.idaegu.com">대구일보</source>
</item>
</channel></rss>"""


def test_parse_feed_skips_item_without_pubdate():
    articles = parse_feed(_FEED_MISSING_PUBDATE, keyword="동성로 상권")
    assert [a.title for a in articles] == ["동성로 상권 회복"]  # 발행일 없는 항목만 건너뛰고 나머지는 유지


def test_parse_feed_returns_empty_when_no_items():
    assert parse_feed(_EMPTY_FEED, keyword="없는키워드") == []
