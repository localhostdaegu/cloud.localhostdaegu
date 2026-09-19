"""통계청 SGIS 오픈API 지오코딩 Driven Adapter.

- 도메인: sgisapi.mods.go.kr — 구 sgisapi.kostat.go.kr 는 302 이전됐다 (2026-09-19 실측)
- 인증: /OpenAPI3/auth/authentication.json?consumer_key=&consumer_secret= → accessToken(4시간).
  accessTimeout(epoch ms) 전까지 재사용한다
- 지오코딩: /OpenAPI3/addr/geocode.json?accessToken=&address=&pagenum=0&resultcount=1
  → resultdata[0].x/y 는 EPSG:5179(UTM-K) 문자열 → WGS84(lng, lat) 변환.
  "대구광역시 달서구 와룡로 70" → x 1093700.96 / y 1760716.28 → (128.53752, 35.83849) 실측,
  어린이집 원천 좌표 5건과 2~104m 일치로 교차검증 (2026-09-19)
- 무결과는 예외가 아니라 errCd 로 온다: -100 검색결과 없음, -200 주소 형식 불가 → None
- 브이월드 지오코더는 결과 저장을 약관으로 금지해 store 좌표 영구 적재에 못 쓴다 — SGIS로 대체.
  권고 한도 일 5만 회이므로 호출은 CLI 캐시가 억제하고, 실사용량은 call_count로 보고한다
"""

import re
import time

import httpx
from pyproj import Transformer

from core.matrix.grid_address_normalizer import normalize_address
from core.matrix.grid_http_error_translator import translate_http_errors
from core.matrix.grid_keymaker_secret_manager import get_settings

_BASE_URL = "https://sgisapi.mods.go.kr/OpenAPI3"
_TRANSFORMER = Transformer.from_crs(5179, 4326, always_xy=True)  # UTM-K → WGS84
_TOKEN_MARGIN_SEC = 60  # 만료 직전 호출이 인증 오류로 떨어지지 않도록 앞당겨 재발급
# 주소 자체의 실패 — 재시도해도 같으므로 예외가 아니라 None (CLI가 실패로 캐시해 재호출을 막는다)
_NO_RESULT_CODES = {-100, -200}


_LOT_NUMBER = re.compile(r"^(?P<head>.*?\S)\s+(?P<main>\d+)(?:-(?P<sub>\d+))?(?P<tail>\s.*)?$")


def address_variants(address: str) -> list[str]:
    """SGIS가 받아 주는 순서로 주소를 단순화한 후보 목록(중복 제거, 원문 정규화본이 첫 번째).

    1) 정규화(괄호·지하 제거) 원문
    2) 번지의 앞자리 0 제거 + 번지 뒤 토큰(층·호·건물명) 제거  예: "동성로2가 0067-0003 1,2층" → "동성로2가 67-3"
    3) 부번 제거  예: "송현동 554-2" → "송현동 554"  (SGIS 실측: 부번 지번은 무결과, 본번은 결과)
    동 이름만 남기는 단계는 두지 않는다 — 법정동 중심점은 행정동 판정을 한쪽으로 몰아 지표를 왜곡한다.
    """
    first = normalize_address(address)
    variants = [first]
    match = _LOT_NUMBER.match(first)
    if match:
        head, main, sub = match.group("head"), str(int(match.group("main"))), match.group("sub")
        variants.append(f"{head} {main}-{int(sub)}" if sub else f"{head} {main}")
        if sub:
            variants.append(f"{head} {main}")
    return list(dict.fromkeys(variants))


def _raise_on_error(payload: dict) -> None:
    if int(payload.get("errCd") or 0) != 0:
        raise RuntimeError(f"SGIS API 오류: errCd={payload.get('errCd')} {payload.get('errMsg')}")


class SgisGeocodeGateway:
    def __init__(self) -> None:
        settings = get_settings()
        self._service_id = settings.sgis_service_id
        self._security_key = settings.sgis_security_key
        self._token = ""
        self._token_expires_at = 0.0  # epoch sec
        self.call_count = 0  # 호출량 규율 — CLI가 로그로 보고 (인증 호출 포함)
        self._client = httpx.Client(timeout=httpx.Timeout(60, connect=10))

    def geocode(self, address: str) -> tuple[float, float] | None:
        """주소 → (lng, lat). 원천이 찾지 못하면 None (0,0으로 채우지 않는다).

        지번 주소는 부번·앞자리 0·층호 때문에 못 찾는 경우가 많아(2026-09-19 인허가 5,547건 중 47% 실패)
        address_variants 순서로 단순화하며 재시도하고 첫 성공에서 멈춘다.
        """
        for variant in address_variants(address):
            point = self._geocode_once(variant)
            if point is not None:
                return point
        return None

    def _geocode_once(self, address: str) -> tuple[float, float] | None:
        payload = self._request(
            f"{_BASE_URL}/addr/geocode.json",
            {
                "accessToken": self._access_token(),
                "address": address,
                "pagenum": 0,
                "resultcount": 1,
            },
        )
        if int(payload.get("errCd") or 0) in _NO_RESULT_CODES:
            return None
        _raise_on_error(payload)
        rows = (payload.get("result") or {}).get("resultdata") or []
        if not rows:
            return None
        return _TRANSFORMER.transform(float(rows[0]["x"]), float(rows[0]["y"]))

    def _access_token(self) -> str:
        if self._token and time.time() < self._token_expires_at:
            return self._token
        payload = self._request(
            f"{_BASE_URL}/auth/authentication.json",
            {"consumer_key": self._service_id, "consumer_secret": self._security_key},
        )
        _raise_on_error(payload)
        result = payload["result"]
        self._token = result["accessToken"]
        self._token_expires_at = int(result["accessTimeout"]) / 1000 - _TOKEN_MARGIN_SEC
        return self._token

    def _request(self, url: str, params: dict) -> dict:
        response = self._get_with_retry(self._client, url, params)
        self.call_count += 1
        return response.json()

    @staticmethod
    def _get_with_retry(
        client: httpx.Client, url: str, params: dict, attempts: int = 3
    ) -> httpx.Response:
        """타임아웃·5xx는 지수 백오프 재시도, 4xx는 즉시 전파 (MOIS 게이트웨이 전례).
        전파 오류는 consumer_secret 이 빠진 메시지로 번역한다."""
        with translate_http_errors():
            for attempt in range(attempts):
                try:
                    response = client.get(url, params=params)
                    response.raise_for_status()
                    return response
                except httpx.HTTPStatusError as error:
                    if error.response.status_code < 500 or attempt == attempts - 1:
                        raise
                except httpx.TimeoutException:
                    if attempt == attempts - 1:
                        raise
                time.sleep(2**attempt)
        raise RuntimeError("unreachable")
