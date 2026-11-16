"""제품 문서 PDF의 안전한 추출과 입력 후보 분석을 검증한다."""

from io import BytesIO
import unittest

from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from texreg_core.pdf_reader import (
    MAX_DECOMPRESSED_STREAM_BYTES,
    MAX_PDF_BYTES,
    PdfDocument,
    PdfReadError,
    analyze_pdf_document,
    read_pdf_document,
)


def make_text_pdf(lines: list[str]) -> bytes:
    """추가 렌더링 의존성 없이 Helvetica 텍스트 PDF를 메모리에서 만든다."""
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    font_reference = writer._add_object(font)
    page[NameObject("/Resources")] = DictionaryObject(
        {
            NameObject("/Font"): DictionaryObject(
                {NameObject("/F1"): font_reference}
            )
        }
    )
    escaped_lines = [
        line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        for line in lines
    ]
    commands = " Tj T* ".join(f"({line})" for line in escaped_lines)
    stream = DecodedStreamObject()
    stream.set_data(f"BT /F1 11 Tf 50 740 Td 15 TL {commands} Tj ET".encode("latin-1"))
    page[NameObject("/Contents")] = writer._add_object(stream)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


class PdfReaderTests(unittest.TestCase):
    def test_text_pdf_is_read_and_product_fields_are_detected(self) -> None:
        pdf_bytes = make_text_pdf(
            [
                "PRODUCT SPECIFICATION",
                "Product Name: Alpine Rain Jacket",
                "Fiber Content: Polyester 85%, Cotton 15%",
                "Target Market: EU, Japan",
                "Process: knitted and dyeing",
                "Finishing: DWR water repellent",
            ]
        )

        document = read_pdf_document(pdf_bytes)
        insights = analyze_pdf_document(document, "alpine-spec.pdf")

        self.assertEqual(document.page_count, 1)
        self.assertFalse(document.needs_ocr)
        self.assertEqual(insights.product_name, "Alpine Rain Jacket")
        self.assertEqual(
            [(item.name, item.ratio) for item in insights.materials],
            [("Polyester", 85.0), ("Cotton", 15.0)],
        )
        self.assertTrue(insights.composition_complete)
        self.assertEqual(insights.destinations, ("EU", "일본"))
        self.assertIn("편직", insights.processes)
        self.assertIn("염색", insights.processes)
        self.assertIn("DWR 발수 가공", insights.finishings)

    def test_sds_product_is_trade_name_and_not_base_fabric(self) -> None:
        document = PdfDocument(
            page_count=1,
            page_texts=(
                "SAFETY DATA SHEET\n"
                "Product Name: FluoroGuard X\n"
                "SECTION 3 Composition\n"
                "PFOA 335-67-1 10%\n"
                "Polyester resin 25%",
            ),
        )

        insights = analyze_pdf_document(document, "FluoroGuard_SDS.pdf")

        self.assertEqual(insights.product_name, "")
        self.assertEqual(insights.trade_name, "FluoroGuard X")
        self.assertEqual(insights.materials, ())
        self.assertEqual(insights.cas_numbers, ("335-67-1",))
        self.assertIn("PFOA", insights.chemicals)
        self.assertEqual(insights.pfas_status, "PFAS 사용·포함 가능")

    def test_standalone_sds_heading_is_classified_as_chemical_document(self) -> None:
        document = PdfDocument(
            page_count=1,
            page_texts=((
                "SDS\n"
                "Product Name: PolyResin X\n"
                "SECTION 3 Composition\n"
                "PFOA 335-67-1 1%\n"
                "Polyester resin 25%"
            ),),
        )

        insights = analyze_pdf_document(document, "PolyResin_SDS.pdf")

        self.assertIn("SDS", insights.document_types)
        self.assertEqual(insights.product_name, "")
        self.assertEqual(insights.trade_name, "PolyResin X")
        self.assertEqual(insights.materials, ())
        self.assertEqual(insights.cas_numbers, ("335-67-1",))
        self.assertIn("PFOA", insights.chemicals)

    def test_common_sds_heading_variants_remain_chemical_documents(self) -> None:
        headings = (
            "SAFETY DATA SHEET according to Regulation (EC) No. 1907/2006",
            "물질안전보건자료(MSDS)",
            "물질안전보건자료 (MSDS)",
        )
        for heading in headings:
            with self.subTest(heading=heading):
                insights = analyze_pdf_document(
                    PdfDocument(
                        page_count=1,
                        page_texts=(f"{heading}\nProduct Name: FluoroGuard X",),
                    ),
                    "10462_en.pdf",
                )
                self.assertIn("SDS", insights.document_types)
                self.assertEqual(insights.product_name, "")
                self.assertEqual(insights.trade_name, "FluoroGuard X")

    def test_tds_heading_with_product_suffix_is_recognized(self) -> None:
        insights = analyze_pdf_document(
            PdfDocument(
                page_count=1,
                page_texts=((
                    "TECHNICAL DATA SHEET – StormShield 3L\n"
                    "Product Name: StormShield 3L Fabric\n"
                    "Construction: ePTFE membrane"
                ),),
            ),
            "10462_en.pdf",
        )

        self.assertIn("TDS", insights.document_types)
        self.assertEqual(insights.product_name, "StormShield 3L Fabric")

    def test_chemical_tds_resin_is_not_used_as_base_fabric(self) -> None:
        document = PdfDocument(
            page_count=1,
            page_texts=(
                "TECHNICAL DATA SHEET\n"
                "Product Name: PolyBond 25\n"
                "Composition: Polyester resin 25%\n"
                "Application: coating adhesive",
            ),
        )

        insights = analyze_pdf_document(document, "PolyBond_TDS.pdf")

        self.assertEqual(insights.product_name, "")
        self.assertEqual(insights.trade_name, "PolyBond 25")
        self.assertEqual(insights.materials, ())

    def test_product_coating_resin_is_not_counted_as_fiber_content(self) -> None:
        document = PdfDocument(
            page_count=1,
            page_texts=((
                "PRODUCT SPECIFICATION\n"
                "Fiber Content: Cotton 100%\n"
                "Coating chemistry: Polyester resin 25%"
            ),),
        )

        insights = analyze_pdf_document(document, "coated-cotton-spec.pdf")

        self.assertEqual(
            [(candidate.name, candidate.ratio) for candidate in insights.materials],
            [("Cotton", 100.0)],
        )
        self.assertTrue(insights.composition_complete)

    def test_textile_tds_keeps_product_structure_and_target_market(self) -> None:
        document = PdfDocument(
            page_count=1,
            page_texts=((
                "TECHNICAL DATA SHEET\n"
                "Product Name: StormShield 3L Fabric\n"
                "Construction: ePTFE membrane\n"
                "Target Market: EU\n"
                "DWR finish"
            ),),
        )

        insights = analyze_pdf_document(document, "stormshield-tds.pdf")

        self.assertEqual(insights.product_name, "StormShield 3L Fabric")
        self.assertEqual(insights.trade_name, "")
        self.assertEqual(insights.destinations, ("EU",))
        self.assertIn("PTFE/ePTFE 멤브레인", insights.membranes)
        self.assertIn("DWR 발수 가공", insights.finishings)

    def test_pfas_free_and_eptfe_are_reported_as_conflicting(self) -> None:
        document = PdfDocument(
            page_count=1,
            page_texts=(
                "PRODUCT SPECIFICATION\n"
                "Construction: ePTFE membrane / DWR, PFAS-free chemistry",
            ),
        )

        insights = analyze_pdf_document(document, "shell-spec.pdf")

        self.assertEqual(insights.pfas_status, "상충 정보")
        self.assertIn("PTFE/ePTFE 멤브레인", insights.membranes)
        self.assertIn("DWR 발수 가공", insights.finishings)
        self.assertNotIn("PFAS-free 발수제", insights.chemicals)
        self.assertTrue(any("수동 확인" in warning for warning in insights.warnings))

    def test_test_report_pass_does_not_prefill_tested_substances(self) -> None:
        document = PdfDocument(
            page_count=1,
            page_texts=(
                "TEST REPORT\n"
                "PFOA / PFOS test: PASS\n"
                "Complies with EU PFAS restriction requirements.",
            ),
        )

        insights = analyze_pdf_document(document, "pfas-test-report.pdf")

        self.assertEqual(insights.chemicals, ())
        self.assertEqual(insights.cas_numbers, ())
        self.assertEqual(insights.pfas_status, "미확인")
        self.assertTrue(any("시험 대상" in warning for warning in insights.warnings))

    def test_sds_reference_does_not_turn_a_test_report_into_an_sds(self) -> None:
        document = PdfDocument(
            page_count=1,
            page_texts=((
                "TEST REPORT\n"
                "SDS reviewed\n"
                "PFOA CAS 335-67-1: PASS"
            ),),
        )

        insights = analyze_pdf_document(document, "supplier-test-report.pdf")

        self.assertEqual(insights.document_types, ("시험성적서",))
        self.assertEqual(insights.chemicals, ())
        self.assertEqual(insights.cas_numbers, ())
        self.assertEqual(insights.pfas_status, "미확인")

    def test_sds_availability_note_does_not_turn_product_spec_into_an_sds(self) -> None:
        document = PdfDocument(
            page_count=1,
            page_texts=((
                "PRODUCT SPECIFICATION\n"
                "Product Name: Alpine Jacket\n"
                "Fiber Content: Polyester 100%\n"
                "Safety Data Sheet available on request\n"
                "Target Market: EU"
            ),),
        )

        insights = analyze_pdf_document(document, "alpine-product-spec.pdf")

        self.assertEqual(insights.document_types, ("제품 사양서",))
        self.assertEqual(insights.product_name, "Alpine Jacket")
        self.assertEqual(
            [(candidate.name, candidate.ratio) for candidate in insights.materials],
            [("Polyester", 100.0)],
        )
        self.assertEqual(insights.destinations, ("EU",))

    def test_product_spec_pass_table_does_not_mark_test_targets_as_used(self) -> None:
        document = PdfDocument(
            page_count=1,
            page_texts=((
                "PRODUCT SPECIFICATION\n"
                "Fiber Content: Polyester 100%\n"
                "PFOA / PFOS test: PASS\n"
                "Complies with EU PFAS restriction requirements."
            ),),
        )

        insights = analyze_pdf_document(document, "jacket-spec.pdf")

        self.assertEqual(insights.chemicals, ())
        self.assertEqual(insights.cas_numbers, ())
        self.assertEqual(insights.pfas_status, "미확인")

    def test_cas_with_pass_result_is_not_prefilled_as_a_used_substance(self) -> None:
        document = PdfDocument(
            page_count=1,
            page_texts=((
                "PRODUCT SPECIFICATION\n"
                "Fiber Content: Polyester 100%\n"
                "PFOA CAS 335-67-1: PASS"
            ),),
        )

        insights = analyze_pdf_document(document, "passed-spec.pdf")

        self.assertEqual(insights.chemicals, ())
        self.assertEqual(insights.cas_numbers, ())
        self.assertEqual(insights.pfas_status, "미확인")

    def test_failed_or_exceeded_pfas_result_remains_positive_evidence(self) -> None:
        failed = analyze_pdf_document(
            PdfDocument(
                page_count=1,
                page_texts=("PRODUCT SPECIFICATION\nPFOA CAS 335-67-1 restriction: FAIL",),
            ),
            "failed-spec.pdf",
        )
        exceeded = analyze_pdf_document(
            PdfDocument(
                page_count=1,
                page_texts=("PRODUCT SPECIFICATION\nPFOS regulation limit exceeded",),
            ),
            "exceeded-spec.pdf",
        )

        self.assertIn("PFOA", failed.chemicals)
        self.assertEqual(failed.cas_numbers, ("335-67-1",))
        self.assertEqual(failed.pfas_status, "PFAS 사용·포함 가능")
        self.assertIn("PFOS", exceeded.chemicals)
        self.assertEqual(exceeded.pfas_status, "PFAS 사용·포함 가능")

    def test_detected_pfas_remains_positive_even_when_the_limit_test_passes(self) -> None:
        document = PdfDocument(
            page_count=1,
            page_texts=((
                "PRODUCT SPECIFICATION\n"
                "PFOA detected (CAS 335-67-1) at 2 ppm: PASS"
            ),),
        )

        insights = analyze_pdf_document(document, "detected-spec.pdf")

        self.assertIn("PFOA", insights.chemicals)
        self.assertEqual(insights.cas_numbers, ("335-67-1",))
        self.assertEqual(insights.pfas_status, "PFAS 사용·포함 가능")

    def test_origin_on_line_after_empty_market_label_is_not_destination(self) -> None:
        document = PdfDocument(
            page_count=1,
            page_texts=(
                "PRODUCT SPECIFICATION\n"
                "Target Market:\n"
                "Country of Origin: China",
            ),
        )

        insights = analyze_pdf_document(document, "origin-only.pdf")

        self.assertEqual(insights.destinations, ())

    def test_destination_exclusions_and_unrelated_marketing_text_are_ignored(self) -> None:
        prefix_exclusion = analyze_pdf_document(
            PdfDocument(page_count=1, page_texts=("판매국: EU 제외 미국, 일본",)),
            "prefix-exclusion.pdf",
        )
        suffix_exclusion = analyze_pdf_document(
            PdfDocument(page_count=1, page_texts=("판매국: 미국, 일본, 중국 제외",)),
            "suffix-exclusion.pdf",
        )
        marketing_name = analyze_pdf_document(
            PdfDocument(page_count=1, page_texts=("Marketing Name: EU Heritage Jacket",)),
            "marketing-name.pdf",
        )

        self.assertEqual(prefix_exclusion.destinations, ("미국", "일본"))
        self.assertEqual(suffix_exclusion.destinations, ("미국", "일본"))
        self.assertEqual(marketing_name.destinations, ())

    def test_origin_after_empty_target_market_is_not_a_destination(self) -> None:
        for origin_label in ("Origin: China", "Country of Origin: China"):
            with self.subTest(origin_label=origin_label):
                insights = analyze_pdf_document(
                    PdfDocument(
                        page_count=1,
                        page_texts=(f"PRODUCT SPECIFICATION\nTarget Market:\n{origin_label}",),
                    ),
                    "origin-spec.pdf",
                )
                self.assertEqual(insights.destinations, ())

    def test_inline_origin_is_removed_without_losing_target_market(self) -> None:
        insights = analyze_pdf_document(
            PdfDocument(
                page_count=1,
                page_texts=("Target Market: EU / Origin: China",),
            ),
            "market-and-origin.pdf",
        )

        self.assertEqual(insights.destinations, ("EU",))

    def test_rounded_composition_is_not_marked_complete(self) -> None:
        document = PdfDocument(
            page_count=1,
            page_texts=(
                "PRODUCT SPECIFICATION\n"
                "Fiber Content: Polyester 33.3%, Cotton 33.3%, Nylon 33.3%",
            ),
        )

        insights = analyze_pdf_document(document, "rounded-blend.pdf")

        self.assertFalse(insights.composition_complete)
        self.assertTrue(any("100%" in warning for warning in insights.warnings))

    def test_cas_checksum_rejects_number_with_invalid_check_digit(self) -> None:
        document = PdfDocument(
            page_count=1,
            page_texts=("CAS No. 335-67-1\nCAS No. 123-45-6",),
        )

        insights = analyze_pdf_document(document, "chemicals.pdf")

        self.assertEqual(insights.cas_numbers, ("335-67-1",))

    def test_nd_notation_does_not_mark_tested_pfas_as_used(self) -> None:
        for result in ("PFOA: ND", "PFOS: N.D."):
            with self.subTest(result=result):
                insights = analyze_pdf_document(
                    PdfDocument(
                        page_count=1,
                        page_texts=(f"PRODUCT SPECIFICATION\n{result}",),
                    ),
                    "nd-result-spec.pdf",
                )
                self.assertEqual(insights.chemicals, ())
                self.assertEqual(insights.pfas_status, "미확인")

    def test_blank_pdf_requests_ocr(self) -> None:
        writer = PdfWriter()
        writer.add_blank_page(width=612, height=792)
        output = BytesIO()
        writer.write(output)

        document = read_pdf_document(output.getvalue())

        self.assertTrue(document.needs_ocr)
        self.assertEqual(document.extracted_char_count, 0)

    def test_encrypted_and_excessively_long_pdf_are_rejected(self) -> None:
        encrypted_writer = PdfWriter()
        encrypted_writer.add_blank_page(width=612, height=792)
        encrypted_writer.encrypt("secret")
        encrypted_output = BytesIO()
        encrypted_writer.write(encrypted_output)

        with self.assertRaisesRegex(PdfReadError, "암호"):
            read_pdf_document(encrypted_output.getvalue())

        long_writer = PdfWriter()
        for _ in range(61):
            long_writer.add_blank_page(width=72, height=72)
        long_output = BytesIO()
        long_writer.write(long_output)

        with self.assertRaisesRegex(PdfReadError, "60페이지"):
            read_pdf_document(long_output.getvalue())

        maximum_writer = PdfWriter()
        for _ in range(60):
            maximum_writer.add_blank_page(width=72, height=72)
        maximum_output = BytesIO()
        maximum_writer.write(maximum_output)

        self.assertEqual(read_pdf_document(maximum_output.getvalue()).page_count, 60)

    def test_compressed_page_stream_is_stopped_at_decompression_limit(self) -> None:
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
        stream = DecodedStreamObject()
        stream.set_data(
            b"BT /F1 11 Tf (" + b"A" * (MAX_DECOMPRESSED_STREAM_BYTES + 1024) + b") Tj ET"
        )
        page[NameObject("/Contents")] = writer._add_object(stream.flate_encode())
        output = BytesIO()
        writer.write(output)

        self.assertLess(len(output.getvalue()), MAX_PDF_BYTES)
        with self.assertRaisesRegex(PdfReadError, "안전 한도"):
            read_pdf_document(output.getvalue())

    def test_non_pdf_and_oversized_pdf_are_rejected(self) -> None:
        with self.assertRaisesRegex(PdfReadError, "PDF 형식"):
            read_pdf_document(b"not a pdf")
        with self.assertRaisesRegex(PdfReadError, "15MB"):
            read_pdf_document(b"%PDF-1.7\n" + b"x" * MAX_PDF_BYTES)


if __name__ == "__main__":
    unittest.main()
