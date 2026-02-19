"""
한국투자증권 순위분석 API
- 거래량 순위
- 거래대금 순위
- 등락률 순위 (상승/하락)
"""
from typing import Dict, Any, List, Tuple
from datetime import datetime

from modules.kis_client import KISClient
from modules.market_hours import is_market_hours


from modules.utils import safe_int, safe_float


class KISRankAPI:
    """순위분석 API"""

    def __init__(self, client: KISClient = None):
        """
        Args:
            client: KIS 클라이언트 (없으면 새로 생성)
        """
        self.client = client or KISClient()
        # blng_cls_code별 _collect_extended_stocks 결과 캐시
        # 동일 blng_cls_code는 시장 무관하게 같은 데이터를 반환하므로 1회만 호출
        self._extended_stocks_cache: Dict[str, List[Dict[str, Any]]] = {}

    def _determine_market(self, code: str) -> str:
        """종목코드로 시장 구분

        한국거래소 종목코드 규칙:
        - KOSPI: 주로 0~2로 시작하는 6자리 (예: 005930 삼성전자)
        - KOSDAQ: 주로 3~4로 시작하는 6자리 (예: 373220 LG에너지솔루션은 예외)
        - ETN: Q로 시작 (예: Q530036)
        - ETF: 6자리, 1~2로 시작 (예: 114800 KODEX인버스)

        Note: 완벽하지 않으므로 참고용으로만 사용
        """
        if not code:
            return "UNKNOWN"

        # ETN은 Q로 시작
        if code.startswith("Q"):
            return "ETN"

        # 6자리 숫자인 경우
        if len(code) == 6 and code.isdigit():
            first_digit = code[0]
            # 3, 4로 시작하면 대체로 KOSDAQ
            if first_digit in ("3", "4"):
                return "KOSDAQ"
            # 나머지는 KOSPI (ETF 포함)
            return "KOSPI"

        return "UNKNOWN"

    def _is_etf_or_etn(self, code: str, name: str) -> bool:
        """ETF/ETN 여부 판단

        Args:
            code: 종목코드
            name: 종목명

        Returns:
            ETF/ETN이면 True
        """
        # ETN은 Q로 시작
        if code.startswith("Q"):
            return True

        # 종목명에 ETF 운용사 키워드 포함
        etf_keywords = [
            "KODEX", "TIGER", "KBSTAR", "ARIRANG", "HANARO",
            "SOL", "KINDEX", "KOSEF", "ACE", "PLUS", "RISE",
            "ETN", "ETF", "선물", "인버스", "레버리지",
            "채권", "국채", "회사채", "액티브",
        ]
        for keyword in etf_keywords:
            if keyword in name:
                return True

        # 특수 코드 형태 (0000XX 등)
        if code.startswith("0000") or code.startswith("00"):
            if not code[2:].isdigit():  # 0000D0 같은 형태
                return True

        return False

    def _fetch_volume_rank_raw(
        self,
        price_min: str = "",
        price_max: str = "",
        blng_cls_code: str = "0",
    ) -> List[Dict[str, Any]]:
        """거래량순위 원본 API 호출 (내부용)

        Args:
            price_min: 최소 가격 조건
            price_max: 최대 가격 조건
            blng_cls_code: 소속 구분 코드
                - "0": 평균거래량 (기본값)
                - "1": 거래증가율
                - "2": 평균거래회전율
                - "3": 거래금액순 (거래대금순위)
                - "4": 평균거래금액회전율

        Returns:
            API 원본 응답의 output 리스트
        """
        path = "/uapi/domestic-stock/v1/quotations/volume-rank"
        tr_id = "FHPST01710000"

        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_COND_SCR_DIV_CODE": "20171",
            "FID_INPUT_ISCD": "0000",
            "FID_DIV_CLS_CODE": "0",
            "FID_BLNG_CLS_CODE": blng_cls_code,
            "FID_TRGT_CLS_CODE": "0",
            "FID_TRGT_EXLS_CLS_CODE": "0",
            "FID_INPUT_PRICE_1": price_min,
            "FID_INPUT_PRICE_2": price_max,
            "FID_VOL_CNT": "",
            "FID_INPUT_DATE_1": "",
        }

        result = self.client.request("GET", path, tr_id, params=params)

        if result.get("rt_cd") != "0":
            raise Exception(f"API 오류: {result.get('msg1', 'Unknown error')}")

        return result.get("output", [])

    def _collect_extended_stocks(
        self,
        blng_cls_code: str = "0",
        sort_field: str = "acml_vol",
    ) -> List[Dict[str, Any]]:
        """가격대별 분할 조회로 확장된 종목 수집 (캐시 적용)

        KIS API는 1회 최대 30개만 반환하므로,
        가격대별로 세분화하여 분할 조회합니다.
        동일 blng_cls_code 결과는 캐시하여 중복 API 호출을 방지합니다.

        Args:
            blng_cls_code: 소속 구분 코드 ("0": 거래량, "3": 거래대금)
            sort_field: 정렬 기준 필드 ("acml_vol": 거래량, "acml_tr_pbmn": 거래대금)

        Returns:
            중복 제거된 전체 종목 리스트 (sort_field 기준 정렬)
        """
        # 캐시 히트: 동일 blng_cls_code 데이터 재사용
        if blng_cls_code in self._extended_stocks_cache:
            cached = self._extended_stocks_cache[blng_cls_code]
            # sort_field만 다를 수 있으므로 복사 후 재정렬
            result = list(cached)
            result.sort(key=lambda x: safe_int(x.get(sort_field, 0)), reverse=True)
            return result

        # 세분화된 가격대 (15개 구간 → 최대 450개 종목 수집 가능)
        price_ranges = [
            ("", "500"),
            ("500", "1000"),
            ("1000", "2000"),
            ("2000", "3000"),
            ("3000", "5000"),
            ("5000", "7000"),
            ("7000", "10000"),
            ("10000", "15000"),
            ("15000", "20000"),
            ("20000", "30000"),
            ("30000", "50000"),
            ("50000", "70000"),
            ("70000", "100000"),
            ("100000", "150000"),
            ("150000", ""),
        ]

        all_stocks = []
        seen_codes = set()

        for price_min, price_max in price_ranges:
            stocks = self._fetch_volume_rank_raw(price_min, price_max, blng_cls_code)
            for stock in stocks:
                code = stock.get("mksc_shrn_iscd", "")
                if code and code not in seen_codes:
                    seen_codes.add(code)
                    all_stocks.append(stock)

        # 캐시 저장 (정렬 전 원본)
        self._extended_stocks_cache[blng_cls_code] = list(all_stocks)

        all_stocks.sort(key=lambda x: safe_int(x.get(sort_field, 0)), reverse=True)

        return all_stocks

    def get_volume_rank(
        self,
        market: str = "ALL",
        limit: int = 30,
        exclude_etf: bool = False,
        extended: bool = True,
    ) -> List[Dict[str, Any]]:
        """거래량순위 조회

        Args:
            market: 시장 구분
                - "ALL": 전체
                - "KOSPI": 코스피
                - "KOSDAQ": 코스닥
            limit: 조회 건수
            exclude_etf: ETF/ETN 제외 여부
            extended: 확장 조회 모드 (가격대별 분할 조회로 더 많은 종목 수집)

        Returns:
            거래량 순위 종목 리스트
        """
        # ETF 제외 시 확장 조회 사용 (더 많은 종목 필요)
        if extended and exclude_etf:
            stocks = self._collect_extended_stocks()
        else:
            stocks = self._fetch_volume_rank_raw()

        # 결과 정리 및 필터링
        parsed = []
        for stock in stocks:
            code = stock.get("mksc_shrn_iscd", "")
            name = stock.get("hts_kor_isnm", "")
            stock_market = self._determine_market(code)
            is_etf = self._is_etf_or_etn(code, name)

            # ETF/ETN 제외 필터
            if exclude_etf and is_etf:
                continue

            # 시장 필터링
            market_upper = market.upper()
            if market_upper != "ALL":
                if market_upper == "KOSPI" and stock_market not in ("KOSPI",):
                    continue
                if market_upper == "KOSDAQ" and stock_market != "KOSDAQ":
                    continue

            parsed.append({
                "rank": len(parsed) + 1,
                "code": code,
                "name": name,
                "current_price": safe_int(stock.get("stck_prpr", 0)),
                "change_rate": safe_float(stock.get("prdy_ctrt", 0)),
                "change_price": safe_int(stock.get("prdy_vrss", 0)),
                "volume": safe_int(stock.get("acml_vol", 0)),
                "volume_rate": safe_float(stock.get("vol_inrt", 0)),
                "trading_value": safe_int(stock.get("acml_tr_pbmn", 0)),
                "market": stock_market,
                "is_etf": is_etf,
            })

            if len(parsed) >= limit:
                break

        return parsed

    def get_fluctuation_rank(
        self,
        market: str = "ALL",
        direction: str = "UP",
        limit: int = 30,
        exclude_etf: bool = False,
        extended: bool = True,
    ) -> List[Dict[str, Any]]:
        """등락률순위 조회

        Note: KIS API의 등락률순위 전용 API가 불안정하여,
              거래량순위 API 데이터를 등락률 기준으로 정렬하여 반환합니다.

        Args:
            market: 시장 구분 ("ALL", "KOSPI", "KOSDAQ")
            direction: 상승/하락 ("UP": 상승, "DOWN": 하락)
            limit: 조회 건수
            exclude_etf: ETF/ETN 제외 여부
            extended: 확장 조회 모드

        Returns:
            등락률 순위 종목 리스트
        """
        # 거래량 순위 API에서 전체 데이터 가져오기 (등락률 정보 포함)
        volume_data = self.get_volume_rank(
            market=market, limit=500, exclude_etf=exclude_etf, extended=extended
        )

        # 등락률 기준 정렬
        if direction.upper() == "UP":
            # 상승률 순 (높은 순)
            sorted_data = sorted(volume_data, key=lambda x: x["change_rate"], reverse=True)
            # 양수 등락률만 필터링
            sorted_data = [s for s in sorted_data if s["change_rate"] > 0]
        else:
            # 하락률 순 (낮은 순)
            sorted_data = sorted(volume_data, key=lambda x: x["change_rate"])
            # 음수 등락률만 필터링
            sorted_data = [s for s in sorted_data if s["change_rate"] < 0]

        # 순위 재계산 및 방향 추가
        result = []
        for idx, stock in enumerate(sorted_data[:limit]):
            stock_copy = stock.copy()
            stock_copy["rank"] = idx + 1
            stock_copy["direction"] = direction.upper()
            result.append(stock_copy)

        return result

    def get_top30_by_volume(
        self,
        exclude_etf: bool = True,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """코스피/코스닥 거래량 Top30 조회

        Args:
            exclude_etf: ETF/ETN 제외 여부 (기본값: True)

        Returns:
            {
                "kospi": [...],
                "kosdaq": [...],
                "collected_at": "2024-01-01T12:00:00"
            }
        """
        return {
            "kospi": self.get_volume_rank(market="KOSPI", limit=30, exclude_etf=exclude_etf),
            "kosdaq": self.get_volume_rank(market="KOSDAQ", limit=30, exclude_etf=exclude_etf),
            "collected_at": datetime.now().isoformat(),
            "category": "volume",
            "exclude_etf": exclude_etf,
        }

    def get_top30_by_fluctuation(
        self,
        exclude_etf: bool = True,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """코스피/코스닥 등락률 Top30 조회 (상승 + 하락)

        Args:
            exclude_etf: ETF/ETN 제외 여부 (기본값: True)

        Returns:
            {
                "kospi_up": [...],
                "kospi_down": [...],
                "kosdaq_up": [...],
                "kosdaq_down": [...],
                "collected_at": "2024-01-01T12:00:00"
            }
        """
        return {
            "kospi_up": self.get_fluctuation_rank(market="KOSPI", direction="UP", limit=30, exclude_etf=exclude_etf),
            "kospi_down": self.get_fluctuation_rank(market="KOSPI", direction="DOWN", limit=30, exclude_etf=exclude_etf),
            "kosdaq_up": self.get_fluctuation_rank(market="KOSDAQ", direction="UP", limit=30, exclude_etf=exclude_etf),
            "kosdaq_down": self.get_fluctuation_rank(market="KOSDAQ", direction="DOWN", limit=30, exclude_etf=exclude_etf),
            "collected_at": datetime.now().isoformat(),
            "category": "fluctuation",
            "exclude_etf": exclude_etf,
        }

    def get_trading_value_rank(
        self,
        market: str = "ALL",
        limit: int = 30,
        exclude_etf: bool = False,
        extended: bool = True,
    ) -> List[Dict[str, Any]]:
        """거래대금순위 조회

        거래량순위 API(FHPST01710000)의 FID_BLNG_CLS_CODE="3" 으로
        서버 측 거래대금 기준 정렬 결과를 반환합니다.

        Args:
            market: 시장 구분 ("ALL", "KOSPI", "KOSDAQ")
            limit: 조회 건수
            exclude_etf: ETF/ETN 제외 여부
            extended: 확장 조회 모드 (가격대별 분할 조회로 더 많은 종목 수집)

        Returns:
            거래대금 순위 종목 리스트 (get_volume_rank()와 동일한 출력 구조)
        """
        if extended and exclude_etf:
            stocks = self._collect_extended_stocks(
                blng_cls_code="3", sort_field="acml_tr_pbmn"
            )
        else:
            stocks = self._fetch_volume_rank_raw(blng_cls_code="3")

        parsed = []
        for stock in stocks:
            code = stock.get("mksc_shrn_iscd", "")
            name = stock.get("hts_kor_isnm", "")
            stock_market = self._determine_market(code)
            is_etf = self._is_etf_or_etn(code, name)

            if exclude_etf and is_etf:
                continue

            market_upper = market.upper()
            if market_upper != "ALL":
                if market_upper == "KOSPI" and stock_market != "KOSPI":
                    continue
                if market_upper == "KOSDAQ" and stock_market != "KOSDAQ":
                    continue

            parsed.append({
                "rank": len(parsed) + 1,
                "code": code,
                "name": name,
                "current_price": safe_int(stock.get("stck_prpr", 0)),
                "change_rate": safe_float(stock.get("prdy_ctrt", 0)),
                "change_price": safe_int(stock.get("prdy_vrss", 0)),
                "volume": safe_int(stock.get("acml_vol", 0)),
                "volume_rate": safe_float(stock.get("vol_inrt", 0)),
                "trading_value": safe_int(stock.get("acml_tr_pbmn", 0)),
                "market": stock_market,
                "is_etf": is_etf,
            })

            if len(parsed) >= limit:
                break

        return parsed

    def get_top30_by_trading_value(
        self,
        exclude_etf: bool = True,
    ) -> Dict[str, Any]:
        """코스피/코스닥 거래대금 Top30 조회

        Args:
            exclude_etf: ETF/ETN 제외 여부 (기본값: True)

        Returns:
            {
                "kospi": [...],
                "kosdaq": [...],
                "collected_at": "...",
                "category": "trading_value",
            }
        """
        return {
            "kospi": self.get_trading_value_rank(market="KOSPI", limit=30, exclude_etf=exclude_etf),
            "kosdaq": self.get_trading_value_rank(market="KOSDAQ", limit=30, exclude_etf=exclude_etf),
            "collected_at": datetime.now().isoformat(),
            "category": "trading_value",
            "exclude_etf": exclude_etf,
        }

    def _fetch_fluctuation_rank_raw(self) -> List[Dict[str, Any]]:
        """등락률순위 전용 API 원본 호출 (내부용)

        FHPST01700000 전용 API를 사용합니다.
        거래량 API(FHPST01710000)와는 별개 데이터 소스입니다.

        Returns:
            API 원본 응답의 output 리스트
        """
        path = "/uapi/domestic-stock/v1/ranking/fluctuation"
        tr_id = "FHPST01700000"

        params = {
            "fid_cond_mrkt_div_code": "J",
            "fid_cond_scr_div_code": "20170",
            "fid_input_iscd": "0000",
            "fid_rank_sort_cls_code": "0",
            "fid_input_cnt_1": "0",
            "fid_prc_cls_code": "0",
            "fid_input_price_1": "",
            "fid_input_price_2": "",
            "fid_vol_cnt": "",
            "fid_trgt_cls_code": "0",
            "fid_trgt_exls_cls_code": "0",
            "fid_div_cls_code": "0",
            "fid_rsfl_rate1": "",
            "fid_rsfl_rate2": "",
        }

        result = self.client.request("GET", path, tr_id, params=params)

        if result.get("rt_cd") != "0":
            raise Exception(f"API 오류: {result.get('msg1', 'Unknown error')}")

        return result.get("output", [])

    def get_fluctuation_rank_direct(
        self,
        market: str = "ALL",
        direction: str = "UP",
        limit: int = 30,
        exclude_etf: bool = False,
    ) -> List[Dict[str, Any]]:
        """등락률순위 전용 API(FHPST01700000)로 직접 조회

        거래량 API 기반 get_fluctuation_rank()와는 별개 데이터 소스입니다.
        단일 API 호출(최대 30건)에서 파싱/필터링합니다.

        Args:
            market: 시장 구분 ("ALL", "KOSPI", "KOSDAQ")
            direction: 상승/하락 ("UP": 상승, "DOWN": 하락)
            limit: 조회 건수
            exclude_etf: ETF/ETN 제외 여부

        Returns:
            등락률 순위 종목 리스트 (get_volume_rank()와 동일한 출력 구조)
        """
        raw_stocks = self._fetch_fluctuation_rank_raw()

        parsed = []
        for stock in raw_stocks:
            # 전용 API는 stck_shrn_iscd 필드 사용 (거래량 API는 mksc_shrn_iscd)
            code = stock.get("stck_shrn_iscd", "")
            name = stock.get("hts_kor_isnm", "")
            change_rate = safe_float(stock.get("prdy_ctrt", 0))
            stock_market = self._determine_market(code)
            is_etf = self._is_etf_or_etn(code, name)

            # ETF/ETN 제외 필터
            if exclude_etf and is_etf:
                continue

            # 시장 필터링
            market_upper = market.upper()
            if market_upper != "ALL":
                if market_upper == "KOSPI" and stock_market != "KOSPI":
                    continue
                if market_upper == "KOSDAQ" and stock_market != "KOSDAQ":
                    continue

            # 방향 필터링 (prdy_ctrt 부호 기준)
            direction_upper = direction.upper()
            if direction_upper == "UP" and change_rate <= 0:
                continue
            if direction_upper == "DOWN" and change_rate >= 0:
                continue

            parsed.append({
                "rank": len(parsed) + 1,
                "code": code,
                "name": name,
                "current_price": safe_int(stock.get("stck_prpr", 0)),
                "change_rate": change_rate,
                "change_price": safe_int(stock.get("prdy_vrss", 0)),
                "volume": safe_int(stock.get("acml_vol", 0)),
                "volume_rate": safe_float(stock.get("vol_inrt", 0)),
                "trading_value": safe_int(stock.get("acml_tr_pbmn", 0)),
                "market": stock_market,
                "is_etf": is_etf,
                "direction": direction_upper,
                "consecutive_up_days": safe_int(stock.get("stck_up_days", 0)),
                "consecutive_down_days": safe_int(stock.get("stck_down_days", 0)),
            })

            if len(parsed) >= limit:
                break

        return parsed

    def get_top_fluctuation_direct(
        self,
        exclude_etf: bool = True,
    ) -> Dict[str, Any]:
        """등락률순위 전용 API로 코스피/코스닥 상승·하락 조합 조회

        단일 API 호출(30건)로 4개 카테고리를 분리하므로,
        카테고리당 건수가 적을 수 있습니다 (API 한계).

        get_top30_by_fluctuation()과 동일한 반환 구조입니다.

        Args:
            exclude_etf: ETF/ETN 제외 여부 (기본값: True)

        Returns:
            {
                "kospi_up": [...],
                "kospi_down": [...],
                "kosdaq_up": [...],
                "kosdaq_down": [...],
                "collected_at": "...",
                "category": "fluctuation_direct",
            }
        """
        raw_stocks = self._fetch_fluctuation_rank_raw()

        categories = {
            "kospi_up": [],
            "kospi_down": [],
            "kosdaq_up": [],
            "kosdaq_down": [],
        }

        for stock in raw_stocks:
            code = stock.get("stck_shrn_iscd", "")
            name = stock.get("hts_kor_isnm", "")
            change_rate = safe_float(stock.get("prdy_ctrt", 0))
            stock_market = self._determine_market(code)
            is_etf = self._is_etf_or_etn(code, name)

            if exclude_etf and is_etf:
                continue

            # 보합(0%)은 제외
            if change_rate == 0:
                continue

            # 시장 + 방향 결정
            if stock_market == "KOSPI":
                market_key = "kospi"
            elif stock_market == "KOSDAQ":
                market_key = "kosdaq"
            else:
                continue

            direction_key = "up" if change_rate > 0 else "down"
            category_key = f"{market_key}_{direction_key}"

            target = categories[category_key]
            target.append({
                "rank": len(target) + 1,
                "code": code,
                "name": name,
                "current_price": safe_int(stock.get("stck_prpr", 0)),
                "change_rate": change_rate,
                "change_price": safe_int(stock.get("prdy_vrss", 0)),
                "volume": safe_int(stock.get("acml_vol", 0)),
                "volume_rate": safe_float(stock.get("vol_inrt", 0)),
                "trading_value": safe_int(stock.get("acml_tr_pbmn", 0)),
                "market": stock_market,
                "is_etf": is_etf,
                "direction": "UP" if change_rate > 0 else "DOWN",
                "consecutive_up_days": safe_int(stock.get("stck_up_days", 0)),
                "consecutive_down_days": safe_int(stock.get("stck_down_days", 0)),
            })

        # 카테고리별 change_rate 기준 재정렬 + 순위 재할당
        for key in ("kospi_up", "kosdaq_up"):
            categories[key].sort(key=lambda x: x["change_rate"], reverse=True)
            for idx, stock in enumerate(categories[key]):
                stock["rank"] = idx + 1

        for key in ("kospi_down", "kosdaq_down"):
            categories[key].sort(key=lambda x: x["change_rate"])
            for idx, stock in enumerate(categories[key]):
                stock["rank"] = idx + 1

        return {
            **categories,
            "collected_at": datetime.now().isoformat(),
            "category": "fluctuation_direct",
            "exclude_etf": exclude_etf,
        }

    def get_investor_data(self, stocks: List[Dict]) -> Dict[str, Dict]:
        """여러 종목의 투자자(수급) 데이터 일괄 조회

        KIS API FHKST01010900을 종목별로 호출하여
        외국인/기관 순매수 데이터를 수집

        Args:
            stocks: 종목 리스트 [{"code": "...", "name": "...", ...}, ...]

        Returns:
            {종목코드: {"name", "foreign_net", "institution_net", "individual_net"}, ...}
        """
        import time

        path = "/uapi/domestic-stock/v1/quotations/inquire-investor"
        tr_id = "FHKST01010900"

        result = {}
        total = len(stocks)

        for idx, stock in enumerate(stocks):
            code = stock.get("code", "")
            name = stock.get("name", "")

            if not code:
                continue

            try:
                params = {
                    "FID_COND_MRKT_DIV_CODE": "J",
                    "FID_INPUT_ISCD": code,
                }

                response = self.client.request("GET", path, tr_id, params=params)

                if response.get("rt_cd") != "0":
                    continue

                output = response.get("output", [])
                if not output:
                    continue

                # 당일 데이터 (첫 번째 항목)
                today = output[0]
                result[code] = {
                    "name": name,
                    "foreign_net": safe_int(today.get("frgn_ntby_qty", 0)),
                    "institution_net": safe_int(today.get("orgn_ntby_qty", 0)),
                    "individual_net": safe_int(today.get("prsn_ntby_qty", 0)),
                }

            except Exception as e:
                print(f"  ⚠ {name}({code}) 투자자 데이터 조회 실패: {e}")
                continue

            # 진행 상황 출력
            if (idx + 1) % 10 == 0 or idx + 1 == total:
                print(f"  진행: {idx + 1}/{total}")

            # API 호출 간격 (Rate limit 방지)
            time.sleep(0.05)

        return result

    def get_investor_data_estimate(self, stocks: List[Dict]) -> Dict[str, Dict]:
        """장중 외인/기관 추정 수급 데이터 수집

        KIS API HHPTJ04160200을 종목별로 호출하여
        외국인/기관 추정 순매수 데이터를 수집 (개인 데이터 없음)

        Args:
            stocks: 종목 리스트 [{"code": "...", "name": "...", ...}, ...]

        Returns:
            {종목코드: {"name", "foreign_net", "institution_net", "individual_net": None}, ...}
        """
        import time

        result = {}
        total = len(stocks)

        for idx, stock in enumerate(stocks):
            code = stock.get("code", "")
            name = stock.get("name", "")

            if not code:
                continue

            try:
                response = self.client.get_investor_trend_estimate(code)

                if response.get("rt_cd") != "0":
                    continue

                output2 = response.get("output2", [])
                if not output2:
                    continue

                # bsop_hour_gb가 가장 큰(최신) 행 추출
                latest = max(output2, key=lambda x: x.get("bsop_hour_gb", ""))

                result[code] = {
                    "name": name,
                    "foreign_net": safe_int(latest.get("frgn_fake_ntby_qty", 0)),
                    "institution_net": safe_int(latest.get("orgn_fake_ntby_qty", 0)),
                    "individual_net": None,
                }

            except Exception as e:
                print(f"  ⚠ {name}({code}) 추정 수급 조회 실패: {e}")
                continue

            # 진행 상황 출력
            if (idx + 1) % 10 == 0 or idx + 1 == total:
                print(f"  진행: {idx + 1}/{total}")

            # API 호출 간격 (Rate limit 방지)
            time.sleep(0.05)

        return result

    def get_investor_data_auto(self, stocks: List[Dict]) -> Tuple[Dict[str, Dict], bool]:
        """장중/장외 자동 전환 수급 데이터 수집

        장중(09:00~15:30)이면 추정 API, 장외면 확정 API 호출

        Args:
            stocks: 종목 리스트

        Returns:
            (data_dict, is_estimated) 튜플
        """
        if is_market_hours():
            print("[수급] 장중 → 추정 데이터(HHPTJ04160200) 사용")
            data = self.get_investor_data_estimate(stocks)
            return data, True
        else:
            print("[수급] 장외 → 확정 데이터(FHKST01010900) 사용")
            data = self.get_investor_data(stocks)
            return data, False


def test_rank_api():
    """순위 API 테스트"""
    try:
        api = KISRankAPI()

        print("=" * 60)
        print("[거래량 Top30 조회 테스트]")
        print("=" * 60)

        # 코스피 거래량 Top 10
        print("\n[코스피 거래량 Top 10]")
        kospi_vol = api.get_volume_rank(market="KOSPI", limit=10)
        for stock in kospi_vol:
            print(f"  {stock['rank']:2d}. {stock['name']:<15s} ({stock['code']}) "
                  f"| {stock['current_price']:>10,}원 | {stock['change_rate']:>+6.2f}% | "
                  f"거래량: {stock['volume']:>15,}")

        # 코스닥 거래량 Top 10
        print("\n[코스닥 거래량 Top 10]")
        kosdaq_vol = api.get_volume_rank(market="KOSDAQ", limit=10)
        for stock in kosdaq_vol:
            print(f"  {stock['rank']:2d}. {stock['name']:<15s} ({stock['code']}) "
                  f"| {stock['current_price']:>10,}원 | {stock['change_rate']:>+6.2f}% | "
                  f"거래량: {stock['volume']:>15,}")

        print("\n" + "=" * 60)
        print("[등락률 Top 10 조회 테스트]")
        print("=" * 60)

        # 코스피 상승률 Top 10
        print("\n[코스피 상승률 Top 10]")
        kospi_up = api.get_fluctuation_rank(market="KOSPI", direction="UP", limit=10)
        for stock in kospi_up:
            print(f"  {stock['rank']:2d}. {stock['name']:<15s} ({stock['code']}) "
                  f"| {stock['current_price']:>10,}원 | {stock['change_rate']:>+6.2f}%")

        # 코스피 하락률 Top 10
        print("\n[코스피 하락률 Top 10]")
        kospi_down = api.get_fluctuation_rank(market="KOSPI", direction="DOWN", limit=10)
        for stock in kospi_down:
            print(f"  {stock['rank']:2d}. {stock['name']:<15s} ({stock['code']}) "
                  f"| {stock['current_price']:>10,}원 | {stock['change_rate']:>+6.2f}%")

    except Exception as e:
        print(f"[ERROR] 테스트 실패: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_rank_api()
