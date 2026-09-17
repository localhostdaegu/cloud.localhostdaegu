import logging
from datetime import datetime

from apps.news.app.dtos.news_article_dto import NewsArticleDto
from apps.news.app.ports.input.news_article_use_case import NewsArticleUseCase
from apps.news.app.ports.output.news_article_port import (
    NewsArticleRepositoryPort,
    NewsSearchGatewayPort,
)

LOGGER = logging.getLogger(__name__)


class NewsArticleInteractor(NewsArticleUseCase):
    def __init__(
        self,
        repository: NewsArticleRepositoryPort,
        gateway: NewsSearchGatewayPort,
    ) -> None:
        self._repository = repository
        self._gateway = gateway

    def myself(self) -> NewsArticleDto:
        return NewsArticleDto(
            article_id="myself",
            title="news BC 배선 검증",
            description="router → use_case → interactor 왕복 확인용 하드코딩 데이터",
            published_at=datetime(2026, 8, 25),
            url="https://example.com/myself",
            matched_keyword="myself",
        )

    def ingest(self, keywords: list[str]) -> int:
        inserted = 0
        for keyword in keywords:
            try:
                articles = self._gateway.search(keyword)
            except Exception:
                # 한 키워드의 원천 오류(HTTP 등)가 남은 키워드 수집을 막지 않도록 기록 후 계속
                LOGGER.warning("news ingest: 키워드 '%s' 수집 실패 — 다음 키워드 계속", keyword, exc_info=True)
                continue
            inserted += self._repository.save_new(articles)
        return inserted
