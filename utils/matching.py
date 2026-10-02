"""제품 정보와 규제 DB를 연결하는 규칙 기반 진단 엔진."""

from __future__ import annotations

import re
from typing import Any

import pandas as pd


COUNTRY_ALIASES = {
    "EU": {"eu", "유럽", "유럽연합", "europe", "europeanunion"},
    "미국": {"미국", "us", "usa", "unitedstates", "america"},
    "영국": {"영국", "uk", "unitedkingdom", "greatbritain", "britain"},
    "일본": {"일본", "jp", "japan"},
    "대한민국": {"대한민국", "한국", "kr", "korea", "southkorea", "republicofkorea"},
}

RISK_ORDER = {"낮음": 1, "보통": 2, "높음": 3}


def _text(value: Any) -> str:
    """결측치를 빈 문자열로 바꾸고 비교 가능한 문자열을 만든다."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return str(value).strip()


def _normalized(value: Any) -> str:
    """대소문자·공백·일부 구분기호 차이를 무시하기 위한 정규화."""
    return re.sub(r"[\s_\-]+", "", _text(value).lower())


def _terms(value: Any) -> list[str]:
    """CSV의 파이프 구분 키워드를 목록으로 변환한다."""
    return [term.strip() for term in re.split(r"[|,;/\n]+", _text(value)) if term.strip()]


def _contains_keyword(value: Any, keywords: Any) -> list[str]:
    """입력값에 포함된 규제 키워드 목록을 반환한다."""
    haystack = _normalized(value)
    terms = _terms(keywords)

    # PFAS-free와 불소 무첨가 표시는 화학물질 사용 근거로 계산하지 않는다.
    negative_claims = ("pfasfree", "pfas미사용", "불소무첨가", "무불소")
    pfas_terms = ("pfas", "pfoa", "pfos", "불소", "fluoro")
    if any(claim in haystack for claim in negative_claims):
        terms = [term for term in terms if not any(token in _normalized(term) for token in pfas_terms)]

    return [term for term in terms if _normalized(term) in haystack]


def _destinations(value: Any) -> set[str]:
    """사용자 수출국 표기를 규제 DB의 표준 국가명으로 변환한다."""
    normalized_parts = {
        _normalized(part) for part in re.split(r"[|,;/\n]+", _text(value)) if part.strip()
    }
    found: set[str] = set()
    for canonical, aliases in COUNTRY_ALIASES.items():
        if any(part in aliases for part in normalized_parts):
            found.add(canonical)
    return found


def risk_level(score: int) -> str:
    """총점 기준 위험 등급. 경계값은 발표용 프로토타입 가정이다."""
    if score >= 70:
        return "높음"
    if score >= 40:
        return "보통"
    return "낮음"


def regulation_risk_level(score: int) -> str:
    """개별 규제 기여점수를 직관적인 위험도로 변환한다."""
    if score >= 34:
        return "높음"
    if score >= 20:
        return "보통"
    return "낮음"


def relevance_level(factor_count: int, rule_type: str) -> str:
    """실제 매칭된 조건 수와 규칙 유형으로 관련성을 계산한다."""
    if factor_count >= 3 or (rule_type == "pfas" and factor_count >= 2):
        return "높음"
    if factor_count >= 2 or rule_type in {"country_baseline", "country_adult_textile"}:
        return "중간"
    return "낮음"


def match_regulation(product: dict[str, Any], regulation: dict[str, Any]) -> dict | None:
    """제품 한 건과 규제 한 건을 비교해 매칭 결과와 점수 근거를 만든다."""
    destinations = _destinations(product.get("수출국", ""))
    country = _text(regulation.get("국가"))
    if country not in destinations:
        return None

    chemical_hits = _contains_keyword(product.get("사용화학물질"), regulation.get("화학키워드"))
    process_hits = _contains_keyword(product.get("가공방법"), regulation.get("공정키워드"))
    material_hits = _contains_keyword(product.get("소재"), regulation.get("소재키워드"))
    usage_hits = _contains_keyword(product.get("제품용도"), regulation.get("용도키워드"))

    rule_type = _text(regulation.get("매칭유형")) or "keyword"
    # 국가만으로 검토하는 규제와 특정 조건이 있어야 매칭되는 규제를 구분한다.
    if rule_type in {"country_adult_textile", "adult_use_required"} and _contains_keyword(
        product.get("제품용도"), "유아|영아|아동|어린이"
    ):
        return None
    if rule_type == "pfas" and not (chemical_hits or process_hits):
        return None
    if rule_type == "keyword" and not chemical_hits:
        return None
    if rule_type == "keyword_or_use" and not (chemical_hits or usage_hits):
        return None
    if rule_type in {"use_required", "child_use_required"} and not usage_hits:
        return None
    if rule_type == "adult_use_required" and not usage_hits:
        return None

    base_score = int(float(regulation.get("기본점수") or 0))
    score = base_score
    reasons = [f"대상 시장 {country} 적용"]

    if chemical_hits:
        score += 14 if rule_type == "pfas" else 8
        reasons.append(f"화학물질 키워드: {', '.join(chemical_hits)}")
    if process_hits:
        score += 12 if rule_type == "pfas" else 7
        reasons.append(f"가공방법 키워드: {', '.join(process_hits)}")
    if material_hits:
        score += 4
        reasons.append(f"소재 키워드: {', '.join(material_hits)}")
    if usage_hits:
        score += 3
        reasons.append(f"용도 키워드: {', '.join(usage_hits)}")

    factor_count = 1 + sum(bool(hits) for hits in [chemical_hits, process_hits, material_hits, usage_hits])
    result = dict(regulation)
    result.update(
        {
            "기여점수": min(score, 60),
            "관련성": relevance_level(factor_count, rule_type),
            "위험도": regulation_risk_level(score),
            "매칭근거": reasons,
        }
    )
    return result


def diagnose_product(product: dict[str, Any], regulations: pd.DataFrame) -> dict[str, Any]:
    """제품 한 건의 관련 규제, 총점, 위험도를 계산한다."""
    matches: list[dict] = []
    for regulation in regulations.to_dict(orient="records"):
        matched = match_regulation(product, regulation)
        if matched:
            matches.append(matched)

    matches.sort(
        key=lambda item: (item["기여점수"], RISK_ORDER[item["위험도"]]),
        reverse=True,
    )
    # 규제가 늘어나도 점수가 과도하게 포화되지 않도록 상위 3개 기여도를 차등 반영한다.
    contributions = [int(item["기여점수"]) for item in matches]
    destinations = _destinations(product.get("수출국"))
    extreme_risk = False
    if destinations:
        primary = contributions[0] if contributions else 0
        secondary = round(contributions[1] * 0.40) if len(contributions) > 1 else 0
        tertiary = round(contributions[2] * 0.20) if len(contributions) > 2 else 0
        breadth_bonus = min(6, max(0, len(contributions) - 3))
        weighted_score = 5 + round(primary * 0.85) + secondary + tertiary + breadth_bonus

        # 100점은 3개 이상 시장에서 핵심규제 3개와 전체 규제 8개 이상이 동시에 매칭될 때만 부여한다.
        critical_regulations = sum(score >= 50 for score in contributions)
        extreme_risk = (
            len(destinations) >= 3
            and len(matches) >= 8
            and critical_regulations >= 3
        )
        score = 100 if extreme_risk else min(97, weighted_score)
    else:
        score = 0
    return {
        "제품": {key: _text(value) for key, value in product.items()},
        "score": score,
        "위험도": risk_level(score),
        "규제": matches,
        "100점조건": extreme_risk,
    }


def build_dashboard_data(
    products: pd.DataFrame, regulations: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """제품별 점수와 규제별 영향 제품 수를 대시보드용 표로 만든다."""
    product_rows: list[dict] = []
    impact_counts: dict[str, set[str]] = {}

    for product in products.to_dict(orient="records"):
        result = diagnose_product(product, regulations)
        product_name = _text(product.get("제품명"))
        product_rows.append(
            {
                "제품명": product_name,
                "Risk Score": result["score"],
                "위험도": result["위험도"],
                "관련 규제 수": len(result["규제"]),
            }
        )
        for match in result["규제"]:
            impact_counts.setdefault(match["규제명"], set()).add(product_name)

    product_summary = pd.DataFrame(product_rows)
    impact_summary = pd.DataFrame(
        [
            {"규제명": regulation, "영향 제품 수": len(product_names)}
            for regulation, product_names in impact_counts.items()
        ]
    )
    if not impact_summary.empty:
        impact_summary = impact_summary.sort_values("영향 제품 수", ascending=False).reset_index(drop=True)
    return product_summary, impact_summary
