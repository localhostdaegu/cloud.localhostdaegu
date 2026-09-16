"""뉴스 폴링 수집기 (Driving Adapter, CLI — 크론 주기 실행 대상).

기본 키워드: 대구 구·군명 + "상권" (district 마스터에서 로드).
소스: 구글 뉴스 RSS (키·쿼터 없음). 호출량: 구·군 수(8)회/실행.

실행: python -m apps.news.adapter.inbound.cli.news_poller [키워드 ...]
"""

import sys

from sqlalchemy import select

from apps.master.adapter.outbound.orms.district_orm import DistrictOrm
from apps.news.adapter.outbound.gateways.google_news_gateway import GoogleNewsRssGateway
from apps.news.adapter.outbound.repositories.news_article_repository import (
    SqlAlchemyNewsArticleRepository,
)
from apps.news.app.use_cases.news_article_interactor import NewsArticleInteractor
from core.matrix.grid_oracle_database_manager import session_scope


def _default_keywords() -> list[str]:
    with session_scope() as session:
        districts = session.execute(select(DistrictOrm.name).order_by(DistrictOrm.name)).scalars()
        return [f"{name} 상권" for name in districts]


def main(keywords: list[str]) -> None:
    interactor = NewsArticleInteractor(
        repository=SqlAlchemyNewsArticleRepository(),
        gateway=GoogleNewsRssGateway(),
    )
    inserted = interactor.ingest(keywords or _default_keywords())
    print(f"news poller: 신규 {inserted}건 적재")


if __name__ == "__main__":
    main(sys.argv[1:])
