"""상세 제품 입력 화면의 혼용률·구조·공정 추적 동작을 검증한다."""

import json
from io import BytesIO
import os
import tempfile
import unittest
from pathlib import Path

from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
from streamlit.testing.v1 import AppTest


ROOT = Path(__file__).resolve().parents[1]


def _by_label(elements, label):
    """위젯 순서가 바뀌어도 레이블로 안정적으로 찾는다."""
    return next(element for element in elements if element.label == label)


def _text_pdf(lines):
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font_reference = writer._add_object(
        DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            }
        )
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {
            NameObject("/Font"): DictionaryObject(
                {NameObject("/F1"): font_reference}
            )
        }
    )
    escaped = [
        line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        for line in lines
    ]
    stream = DecodedStreamObject()
    stream.set_data(
        (
            "BT /F1 11 Tf 50 740 Td 15 TL "
            + " Tj T* ".join(f"({line})" for line in escaped)
            + " Tj ET"
        ).encode("latin-1")
    )
    page[NameObject("/Contents")] = writer._add_object(stream)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


class ProductInputTest(unittest.TestCase):
    def setUp(self) -> None:
        # 화면 테스트가 실제 사용자 진단 이력을 만지지 않도록 임시 DB를 사용한다.
        self._temp_dir = tempfile.TemporaryDirectory()
        os.environ["TEXREG_HISTORY_DB"] = str(Path(self._temp_dir.name) / "history.db")

    def tearDown(self) -> None:
        os.environ.pop("TEXREG_HISTORY_DB", None)
        self._temp_dir.cleanup()

    def _open_input_page(self) -> AppTest:
        app = AppTest.from_file(str(ROOT / "app.py")).run(timeout=30)
        return app.switch_page("pages/1_Product_Input.py").run(timeout=30)

    def test_mixed_and_custom_materials_are_saved_with_ratios(self) -> None:
        app = self._open_input_page()

        self.assertEqual(len(app.exception), 0)
        destination_options = _by_label(app.multiselect, "판매·수출국 *").options
        for destination in [
            "중국",
            "베트남",
            "인도",
            "대만",
            "캐나다",
            "호주",
            "뉴질랜드",
            "대한민국",
        ]:
            self.assertIn(destination, destination_options)

        product_use_options = _by_label(app.selectbox, "제품 용도 *").options
        self.assertIn("아동용 잠옷", product_use_options)

        _by_label(app.text_input, "제품명 *").input("Test Leggings")
        _by_label(app.selectbox, "구성 1 소재").set_value("Nylon")
        _by_label(app.selectbox, "구성 2 소재").set_value("Spandex")
        _by_label(app.selectbox, "구성 3 소재").set_value("기타")
        app.run(timeout=30)

        self.assertFalse(_by_label(app.text_input, "구성 3 기타 소재명").disabled)
        self.assertFalse(_by_label(app.selectbox, "기타 소재 유형").disabled)
        _by_label(app.text_input, "구성 3 기타 소재명").input("Modal")
        _by_label(app.number_input, "구성 1 함량 (%)").set_value(80.0)
        _by_label(app.number_input, "구성 2 함량 (%)").set_value(17.0)
        _by_label(app.number_input, "구성 3 함량 (%)").set_value(3.0)
        _by_label(app.multiselect, "판매·수출국 *").set_value(["미국", "일본"])
        _by_label(app.multiselect, "주요 가공방법").set_value(["발수"])
        app.run(timeout=30)

        _by_label(app.text_input, "발수 상품명·가공제").input("DWR-X")
        _by_label(app.text_input, "발수 화학물질명").input("fluorotelomer polymer")
        _by_label(app.text_input, "발수 CAS No.").input("미확인")
        _by_label(app.selectbox, "발수 SDS/TDS").set_value("SDS 확보")
        _by_label(app.selectbox, "발수 PFAS 여부").set_value("PFAS 사용·포함 가능")
        _by_label(app.button, "규제 진단하기").click().run(timeout=30)

        self.assertEqual(len(app.exception), 0)
        product = app.session_state["current_result"]["제품"]
        self.assertEqual(product["소재"], "Nylon 80%, Spandex 17%, Modal 3%")
        self.assertEqual(product["소재분류"], "섬유")
        self.assertEqual(product["제품형태"], "의류 완제품")
        self.assertEqual(product["피부접촉"], "직접·장시간 접촉")
        process_details = json.loads(product["공정상세"])
        self.assertEqual(process_details[0]["공정"], "발수")
        self.assertEqual(process_details[0]["SDS/TDS"], "SDS 확보")
        self.assertEqual(process_details[0]["PFAS 여부"], "PFAS 사용·포함 가능")
        self.assertEqual(
            app.session_state["registered_products"][-1]["소재"],
            "Nylon 80%, Spandex 17%, Modal 3%",
        )

        app.switch_page("pages/2_Diagnosis_Result.py").run(timeout=30)
        self.assertEqual(len(app.exception), 0)
        self.assertIn("Test Leggings 진단 결과", [title.value for title in app.title])
        markdown_values = [element.value for element in app.markdown]
        self.assertTrue(any('class="workflow-steps"' in value for value in markdown_values))
        self.assertTrue(any('class="risk-alert ' in value for value in markdown_values))
        self.assertTrue(any("입력한 제품 구조 확인" in element.label for element in app.expander))
        self.assertTrue(any("공정·화학물질 추적 정보" in element.label for element in app.expander))
        self.assertTrue(any("실행형 상세 대응방안" in value for value in markdown_values))
        self.assertTrue(any("즉시 실행 순서" in value for value in markdown_values))
        self.assertTrue(any("완료 기준" in value for value in markdown_values))

        action_list = next(value for value in markdown_values if 'class="action-list"' in value)
        self.assertNotIn("\n", action_list)
        self.assertEqual(action_list.count('class="action-step"'), 3)

    def test_pdf_upload_prefills_detected_product_fields(self) -> None:
        app = self._open_input_page()
        pdf_bytes = _text_pdf(
            [
                "PRODUCT SPECIFICATION",
                "Product Name: Alpine Rain Jacket",
                "Fiber Content: Polyester 85%, Cotton 15%",
                "Target Market: EU, Japan",
                "Process: knitted and dyeing",
                "Chemical: PFOA",
            ]
        )

        app.session_state["processes"] = ["미확인"]
        app.session_state["chemicals"] = ["미확인", "PFOS"]

        _by_label(app.file_uploader, "제품 문서 PDF").set_value(
            ("alpine-spec.pdf", pdf_bytes, "application/pdf")
        )
        app.run(timeout=30)

        self.assertEqual(len(app.exception), 0)
        markdown_values = [element.value for element in app.markdown]
        self.assertTrue(any("Alpine Rain Jacket" in value for value in markdown_values))
        _by_label(app.button, "감지 정보 입력란에 반영").click().run(timeout=30)

        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.session_state["product_name"], "Alpine Rain Jacket")
        self.assertEqual(app.session_state["destinations"], ["EU", "일본"])
        self.assertEqual(app.session_state["material_1"], "Polyester")
        self.assertEqual(app.session_state["material_ratio_1"], 85.0)
        self.assertEqual(app.session_state["material_2"], "Cotton")
        self.assertEqual(app.session_state["material_ratio_2"], 15.0)
        self.assertFalse(app.session_state["composition_unknown"])
        self.assertIn("편직", app.session_state["processes"])
        self.assertIn("염색", app.session_state["processes"])
        self.assertNotIn("미확인", app.session_state["processes"])
        self.assertIn("PFOA", app.session_state["chemicals"])
        self.assertNotIn("미확인", app.session_state["chemicals"])

    def test_sds_trade_name_replaces_unknown_chemical_sentinel(self) -> None:
        app = self._open_input_page()
        pdf_bytes = _text_pdf(
            [
                "SAFETY DATA SHEET",
                "Product Name: NeutralSoft X",
                "SECTION 1: Identification of the substance and supplier",
            ]
        )
        app.session_state["chemicals"] = ["미확인"]

        _by_label(app.file_uploader, "제품 문서 PDF").set_value(
            ("neutral-soft-sds.pdf", pdf_bytes, "application/pdf")
        )
        app.run(timeout=30)
        _by_label(
            app.checkbox,
            "기존 작성값도 PDF 감지값으로 덮어쓰기",
        ).set_value(True).run(timeout=30)
        _by_label(app.button, "감지 정보 입력란에 반영").click().run(timeout=30)

        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.session_state["chemicals"], ["기타"])
        self.assertIn("NeutralSoft X", app.session_state["custom_chemical"])

    def test_composition_total_must_be_100_percent(self) -> None:
        app = self._open_input_page()

        _by_label(app.text_input, "제품명 *").input("Invalid Blend")
        _by_label(app.number_input, "구성 1 함량 (%)").set_value(80.0)
        _by_label(app.multiselect, "판매·수출국 *").set_value(["EU"])
        _by_label(app.button, "규제 진단하기").click().run(timeout=30)

        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.error), 1)
        self.assertIn("100%", app.error[0].value)

    def test_functional_structure_supports_multiple_selections(self) -> None:
        app = self._open_input_page()

        _by_label(app.text_input, "제품명 *").input("Multi-layer Shell")
        _by_label(app.multiselect, "판매·수출국 *").set_value(["EU"])
        _by_label(app.multiselect, "Membrane").set_value(
            ["PU 멤브레인", "PTFE/ePTFE 멤브레인", "기타"]
        )
        _by_label(app.multiselect, "Coating").set_value(["PU 코팅", "Silicone 코팅"])
        _by_label(app.multiselect, "Lamination").set_value(
            ["PU 접착제", "Hot-melt 접착제"]
        )
        _by_label(app.multiselect, "Finishing").set_value(["DWR 발수 가공", "항균 가공"])
        app.run(timeout=30)

        custom_membrane = _by_label(app.text_input, "기타 Membrane")
        self.assertFalse(custom_membrane.disabled)
        custom_membrane.input("PET 멤브레인")
        _by_label(app.button, "규제 진단하기").click().run(timeout=30)

        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.error), 0)
        product = app.session_state["current_result"]["제품"]
        self.assertEqual(
            product["Membrane"],
            "PU 멤브레인, PTFE/ePTFE 멤브레인, PET 멤브레인",
        )
        self.assertEqual(product["Coating"], "PU 코팅, Silicone 코팅")
        self.assertEqual(product["Lamination"], "PU 접착제, Hot-melt 접착제")
        self.assertEqual(product["Finishing"], "DWR 발수 가공, 항균 가공")

        process_names = {
            detail["공정"] for detail in json.loads(product["공정상세"])
        }
        self.assertTrue(
            {
                "PU 코팅",
                "Silicone 코팅",
                "PU 접착제 라미네이션",
                "Hot-melt 접착제 라미네이션",
                "DWR 발수 가공",
                "항균 가공",
            }.issubset(process_names)
        )


if __name__ == "__main__":
    unittest.main()
