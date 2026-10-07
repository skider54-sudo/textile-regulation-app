"""규칙 기반 매칭 엔진의 핵심 시나리오 테스트."""

import unittest
from pathlib import Path

import pandas as pd

from utils.matching import build_dashboard_data, diagnose_product


ROOT = Path(__file__).resolve().parents[1]


class MatchingEngineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.regulations = pd.read_csv(ROOT / "data" / "regulations.csv").fillna("")

    def test_eu_pfas_water_repellent_is_high_risk(self) -> None:
        product = {
            "제품명": "PFAS Jacket",
            "소재": "Polyester",
            "가공방법": "발수, 코팅",
            "사용화학물질": "PFAS계 불소수지",
            "제품용도": "아웃도어 의류",
            "수출국": "EU",
        }
        result = diagnose_product(product, self.regulations)
        regulation_names = {item["규제명"] for item in result["규제"]}
        self.assertIn("PFAS Restriction", regulation_names)
        self.assertIn("EU REACH", regulation_names)
        self.assertEqual(result["위험도"], "높음")

    def test_eu_product_always_checks_reach(self) -> None:
        product = {
            "제품명": "Basic Tote",
            "소재": "Cotton",
            "가공방법": "편직",
            "사용화학물질": "없음",
            "제품용도": "가방",
            "수출국": "EU",
        }
        result = diagnose_product(product, self.regulations)
        regulation_names = {item["규제명"] for item in result["규제"]}
        self.assertIn("EU REACH", regulation_names)

    def test_low_risk_product_remains_bounded(self) -> None:
        product = {
            "제품명": "Plain Towel",
            "소재": "Organic Cotton",
            "가공방법": "편직",
            "사용화학물질": "없음",
            "제품용도": "생활용 섬유",
            "수출국": "미국",
        }
        result = diagnose_product(product, self.regulations)
        self.assertGreaterEqual(result["score"], 0)
        self.assertLessEqual(result["score"], 100)
        self.assertEqual(result["위험도"], "낮음")

    def test_dashboard_counts_every_product(self) -> None:
        products = pd.read_csv(ROOT / "data" / "products.csv").fillna("")
        product_summary, impact_summary = build_dashboard_data(products, self.regulations)
        self.assertEqual(len(product_summary), len(products))
        self.assertFalse(impact_summary.empty)

    def test_uk_and_japan_destinations_are_supported(self) -> None:
        product = {
            "제품명": "Global Shirt",
            "소재": "Cotton",
            "가공방법": "염색",
            "사용화학물질": "아조염료",
            "제품용도": "일상 의류",
            "수출국": "영국, 일본",
        }
        result = diagnose_product(product, self.regulations)
        regulation_names = {item["규제명"] for item in result["규제"]}
        self.assertIn("UK REACH", regulation_names)
        self.assertIn("Household Goods Quality Labeling Act", regulation_names)

    def test_south_korea_infant_product_matches_kc_requirements(self) -> None:
        product = {
            "제품명": "Korea Baby Romper",
            "소재": "Organic Cotton",
            "가공방법": "편직, 염색",
            "사용화학물질": "없음",
            "제품용도": "유아용 의류",
            "수출국": "대한민국",
        }
        result = diagnose_product(product, self.regulations)
        regulation_names = {item["규제명"] for item in result["규제"]}
        self.assertIn("KC 유아용 섬유제품 안전기준", regulation_names)
        self.assertNotIn("가정용 섬유제품 안전기준", regulation_names)

    def test_south_korea_alias_and_k_reach_are_supported(self) -> None:
        product = {
            "제품명": "Korea PFOS Shell",
            "소재": "Polyester",
            "가공방법": "발수, 코팅",
            "사용화학물질": "중점관리물질(성분명 확인 필요)",
            "제품용도": "아웃도어 의류",
            "수출국": "Korea",
        }
        result = diagnose_product(product, self.regulations)
        regulation_names = {item["규제명"] for item in result["규제"]}
        self.assertIn("가정용 섬유제품 안전기준", regulation_names)
        self.assertIn("K-REACH 제품 내 중점관리물질 신고", regulation_names)

    def test_china_child_product_matches_general_and_child_standards(self) -> None:
        product = {
            "제품명": "China Kids Hoodie",
            "소재": "Cotton, Polyester",
            "가공방법": "편직, 염색, 프린팅",
            "사용화학물질": "안료 프린트",
            "제품용도": "아동용 의류",
            "수출국": "PRC",
        }
        result = diagnose_product(product, self.regulations)
        regulation_names = {item["규제명"] for item in result["규제"]}
        self.assertIn("China Product Quality & Textile Labelling", regulation_names)
        self.assertIn("China GB 18401-2010", regulation_names)
        self.assertIn("China GB 31701-2015", regulation_names)

    def test_china_child_standard_does_not_match_adult_apparel(self) -> None:
        product = {
            "제품명": "China Adult Shirt",
            "소재": "Cotton",
            "가공방법": "편직, 염색",
            "사용화학물질": "반응성염료",
            "제품용도": "일상 의류",
            "수출국": "중국",
        }
        result = diagnose_product(product, self.regulations)
        regulation_names = {item["규제명"] for item in result["규제"]}
        self.assertIn("China GB 18401-2010", regulation_names)
        self.assertNotIn("China GB 31701-2015", regulation_names)

    def test_canada_pfas_outerwear_matches_textile_and_toxic_rules(self) -> None:
        product = {
            "제품명": "Canada PFAS Rain Shell",
            "소재": "Nylon",
            "가공방법": "발수, 코팅",
            "사용화학물질": "PFOA",
            "제품용도": "아웃도어 의류",
            "수출국": "Canada",
        }
        result = diagnose_product(product, self.regulations)
        regulation_names = {item["규제명"] for item in result["규제"]}
        self.assertIn("Canada Textile Labelling Act & Regulations", regulation_names)
        self.assertIn("Canada Textile Flammability Regulations", regulation_names)
        self.assertIn(
            "Canada Prohibition of Certain Toxic Substances Regulations, 2025",
            regulation_names,
        )
        self.assertNotIn("Canada Children's Sleepwear Regulations", regulation_names)

    def test_canada_child_sleepwear_uses_dedicated_rule(self) -> None:
        product = {
            "제품명": "Canada Kids Pyjamas",
            "소재": "Cotton",
            "가공방법": "편직, 염색",
            "사용화학물질": "반응성염료",
            "제품용도": "아동용 잠옷",
            "수출국": "캐나다",
        }
        result = diagnose_product(product, self.regulations)
        regulation_names = {item["규제명"] for item in result["규제"]}
        self.assertIn("Canada Textile Labelling Act & Regulations", regulation_names)
        self.assertIn("Canada Children's Sleepwear Regulations", regulation_names)
        self.assertNotIn("Canada Textile Flammability Regulations", regulation_names)

    def test_australia_child_sleepwear_and_pfas_rules_are_conditional(self) -> None:
        child_product = {
            "제품명": "Australia Kids Pyjamas",
            "소재": "Cotton",
            "가공방법": "편직, 염색",
            "사용화학물질": "반응성염료",
            "제품용도": "아동용 잠옷",
            "수출국": "AU",
        }
        child_result = diagnose_product(child_product, self.regulations)
        child_names = {item["규제명"] for item in child_result["규제"]}
        self.assertIn("Australia Care Labelling Information Standard 2023", child_names)
        self.assertIn("Australia Children's Nightwear Safety Standard 2017", child_names)
        self.assertNotIn("Australia IChEMS Schedule 7 PFAS", child_names)

        pfas_product = {
            "제품명": "Australia PFAS Outdoor Jacket",
            "소재": "Nylon",
            "가공방법": "발수, 코팅",
            "사용화학물질": "PFAS계 불소수지",
            "제품용도": "아웃도어 의류",
            "수출국": "호주",
        }
        pfas_result = diagnose_product(pfas_product, self.regulations)
        pfas_names = {item["규제명"] for item in pfas_result["규제"]}
        self.assertIn("Australia Care Labelling Information Standard 2023", pfas_names)
        self.assertIn("Australia IChEMS Schedule 7 PFAS", pfas_names)
        self.assertNotIn("Australia Children's Nightwear Safety Standard 2017", pfas_names)

    def test_child_rules_require_child_product_use(self) -> None:
        product = {
            "제품명": "Adult Printed Jacket",
            "소재": "Polyester",
            "가공방법": "코팅, 프린팅",
            "사용화학물질": "납, 프탈레이트",
            "제품용도": "일상 의류",
            "수출국": "미국, 대한민국",
        }
        result = diagnose_product(product, self.regulations)
        regulation_names = {item["규제명"] for item in result["규제"]}
        self.assertNotIn("CPSIA", regulation_names)
        self.assertNotIn("KC 유아용 섬유제품 안전기준", regulation_names)
        self.assertNotIn("KC 아동용 섬유제품 안전기준", regulation_names)

    def test_ftc_textile_rule_excludes_general_bag(self) -> None:
        product = {
            "제품명": "US Backpack",
            "소재": "Polyester",
            "가공방법": "봉제",
            "사용화학물질": "없음",
            "제품용도": "가방",
            "수출국": "미국",
        }
        result = diagnose_product(product, self.regulations)
        regulation_names = {item["규제명"] for item in result["규제"]}
        self.assertNotIn("FTC Textile Fiber Products Identification Act", regulation_names)

    def test_pfas_free_claim_is_not_a_chemical_hit(self) -> None:
        product = {
            "제품명": "PFAS-free Raincoat",
            "소재": "Polyester",
            "가공방법": "방수",
            "사용화학물질": "PFAS-free 발수제",
            "제품용도": "유아용 의류",
            "수출국": "미국",
        }
        result = diagnose_product(product, self.regulations)
        pfas_match = next(
            item for item in result["규제"] if item["규제명"] == "California AB 1817"
        )
        self.assertFalse(
            any("화학물질 키워드" in reason for reason in pfas_match["매칭근거"])
        )

    def test_two_market_pfas_product_does_not_reach_100(self) -> None:
        product = {
            "제품명": "Two-market PFAS Jacket",
            "소재": "Polyester",
            "가공방법": "발수, 코팅",
            "사용화학물질": "PFAS계 불소수지",
            "제품용도": "아웃도어 의류",
            "수출국": "EU, 미국",
        }
        result = diagnose_product(product, self.regulations)
        self.assertGreaterEqual(result["score"], 70)
        self.assertLess(result["score"], 100)
        self.assertFalse(result["100점조건"])

    def test_extreme_three_market_product_can_reach_100(self) -> None:
        product = {
            "제품명": "Three-market PFAS Backpack",
            "소재": "Polyester",
            "가공방법": "발수, 코팅",
            "사용화학물질": "C6 fluorotelomer 발수제",
            "제품용도": "가방",
            "수출국": "EU, 미국, 영국",
        }
        result = diagnose_product(product, self.regulations)
        self.assertEqual(result["score"], 100)
        self.assertTrue(result["100점조건"])


if __name__ == "__main__":
    unittest.main()
