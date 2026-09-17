"""구글 뉴스 RSS Driven Adapter — 키워드 검색 (키·쿼터 없음).

엔드포인트: news.google.com/rss/search?q=&hl=ko&gl=KR&ceid=KR:ko (2026-09-16 실호출 확인).
- title 은 "제목 - 언론사" 형식 → 언론사 접미 제거, press 는 <source> 요소에서
- link 는 구글 리다이렉트 주소(원문 복원 안 함 — 방식이 자주 바뀜). 중복 제거는 이 주소 해시 기준
- description 은 관련 기사 앵커 HTML → 태그 제거 텍스트만 보존 (본문 저장 금지)
- pubDate 는 GMT → 네이버 어댑터와 같은 KST naive 로 통일. pubDate 없는 항목은 건너뜀(발행일 필수)
"""

import hashlib
import html
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo

import httpx

from apps.news.app.ports.output.news_article_port import NewsSearchGatewayPort
from apps.news.domain.entities.news_article_entity import NewsArticle

_ENDPOINT = "https://news.google.com/rss/search"
_LOCALE = {"hl": "ko", "gl": "KR", "ceid": "KR:ko"}
_KST = ZoneInfo("Asia/Seoul")
_TAG_PATTERN = re.compile(r"<[^>]+>")


def _clean(text: str) -> str:
    return " ".join(html.unescape(_TAG_PATTERN.sub("", text)).split())


def _article_id(url: str) -> str:
    return hashlib.sha1(url.encode()).hexdigest()[:20]


def _strip_press_suffix(title: str, press: str) -> str:
    suffix = f" - {press}"
    return title[: -len(suffix)] if press and title.endswith(suffix) else title


def _to_kst_naive(value: str) -> datetime:
    return parsedate_to_datetime(value).astimezone(_KST).replace(tzinfo=None)


def parse_feed(xml_text: str, keyword: str) -> list[NewsArticle]:
    root = ET.fromstring(xml_text)
    articles = []
    for item in root.iterfind("./channel/item"):
        published = item.findtext("pubDate", "").strip()
        if not published:
            continue
        url = item.findtext("link", "").strip()
        press = (item.findtext("source") or "").strip() or None
        articles.append(
            NewsArticle(
                article_id=_article_id(url),
                title=_strip_press_suffix(_clean(item.findtext("title", "")), press),
                description=_clean(item.findtext("description", "")),
                published_at=_to_kst_naive(published),
                url=url,
                matched_keyword=keyword,
                press=press,
            )
        )
    return articles


class GoogleNewsRssGateway(NewsSearchGatewayPort):
    def search(self, keyword: str) -> list[NewsArticle]:
        response = httpx.get(_ENDPOINT, params={"q": keyword, **_LOCALE}, timeout=15)
        response.raise_for_status()
        return parse_feed(response.text, keyword)
