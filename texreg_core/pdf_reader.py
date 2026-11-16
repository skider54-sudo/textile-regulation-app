"""업로드한 제품 문서 PDF에서 규제 진단용 후보 정보를 추출한다.

PDF는 신뢰할 수 없는 입력으로 취급한다. 파일을 실행하거나 첨부물을 열지 않고,
크기·페이지·추출 문자 수를 제한한 뒤 텍스트 레이어만 읽는다. OCR은 수행하지
않으므로 스캔 이미지 PDF는 사용자에게 별도로 안내한다.
"""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
import re
import unicodedata


MAX_PDF_BYTES = 15 * 1024 * 1024
MAX_PDF_PAGES = 60
MAX_EXTRACTED_CHARS = 120_000
MIN_USEFUL_CHARS = 40
MAX_DECOMPRESSED_STREAM_BYTES = 8 * 1024 * 1024


class PdfReadError(ValueError):
    """사용자에게 바로 안내할 수 있는 PDF 읽기 오류."""


@dataclass(frozen=True)
class PdfDocument:
    """안전 제한을 적용해 추출한 PDF 텍스트와 메타데이터."""

    page_count: int
    page_texts: tuple[str, ...]
    title: str = ""
    truncated: bool = False
    warnings: tuple[str, ...] = ()

    @property
    def text(self) -> str:
        return "\n\n".join(text for text in self.page_texts if text)

    @property
    def extracted_char_count(self) -> int:
        return len(self.text)

    @property
    def needs_ocr(self) -> bool:
        useful_chars = sum(character.isalnum() for character in self.text)
        return useful_chars < MIN_USEFUL_CHARS


@dataclass(frozen=True)
class MaterialCandidate:
    """문서에서 감지한 섬유 소재와 혼용률 후보."""

    name: str
    ratio: float | None
    page: int
    evidence: str


@dataclass(frozen=True)
class PdfInsights:
    """현재 제품 입력 화면에 연결할 수 있는 PDF 분석 결과."""

    document_types: tuple[str, ...]
    product_name: str = ""
    trade_name: str = ""
    materials: tuple[MaterialCandidate, ...] = ()
    composition_complete: bool = False
    destinations: tuple[str, ...] = ()
    membranes: tuple[str, ...] = ()
    coatings: tuple[str, ...] = ()
    laminations: tuple[str, ...] = ()
    finishings: tuple[str, ...] = ()
    processes: tuple[str, ...] = ()
    chemicals: tuple[str, ...] = ()
    cas_numbers: tuple[str, ...] = ()
    pfas_status: str = "미확인"
    detected_terms: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    @property
    def has_prefill_data(self) -> bool:
        return any(
            [
                self.product_name,
                self.trade_name,
                self.materials,
                self.destinations,
                self.membranes,
                self.coatings,
                self.laminations,
                self.finishings,
                self.processes,
                self.chemicals,
                self.cas_numbers,
            ]
        )


_MATERIAL_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "Recycled Polyester",
        (
            r"recycled\s+polyester",
            r"r\s*pet",
            r"재생\s*폴리에스(?:터|테르)",
            r"리사이클(?:드)?\s*폴리에스(?:터|테르)",
        ),
    ),
    (
        "Organic Cotton",
        (r"organic\s+cotton", r"유기\s*(?:면|코튼)", r"오가닉\s*코튼"),
    ),
    (
        "Tencel / Lyocell",
        (r"tencel", r"lyocell", r"텐셀", r"리오셀"),
    ),
    (
        "Polyester",
        (r"polyester", r"폴리에스(?:터|테르)", r"(?<![a-z])pes(?![a-z])"),
    ),
    (
        "Nylon",
        (
            r"nylon",
            r"polyamide",
            r"(?<![a-z])pa\s*(?:6|66)?(?![a-z0-9])",
            r"나일론",
            r"폴리아미드",
        ),
    ),
    ("Cotton", (r"cotton", r"코튼", r"(?<![가-힣])면(?![가-힣])", r"(?<![a-z])co(?![a-z])")),
    (
        "Spandex",
        (
            r"spandex",
            r"elastane",
            r"lycra",
            r"스판덱스",
            r"엘라스테인",
            r"폴리우레탄\s*탄성섬유",
            r"(?<![a-z])el(?![a-z])",
        ),
    ),
    ("Wool", (r"wool", r"양모", r"(?<![a-z])wo(?![a-z])")),
    ("Rayon", (r"rayon", r"viscose", r"레이온", r"비스코스", r"(?<![a-z])vi(?![a-z])")),
    ("Acrylic", (r"acrylic\s*(?:fiber|fibre)", r"아크릴\s*섬유", r"(?<![a-z])pan(?![a-z])")),
    (
        "Polypropylene",
        (r"polypropylene", r"폴리프로필렌", r"(?<![a-z])pp(?![a-z])"),
    ),
    ("Linen", (r"linen", r"flax", r"린넨", r"(?<![가-힣])아마(?![가-힣])", r"(?<![a-z])li(?![a-z])")),
    ("Modal", (r"modal", r"모달")),
)

_MATERIAL_CONTEXT = re.compile(
    r"fiber\s*content|fibre\s*content|textile\s*composition|fabric\s*composition|"
    r"material\s*composition|shell\s*(?:fabric)?|lining|base\s*fabric|"
    r"혼용률|섬유\s*조성|소재\s*구성|원단\s*구성|겉감|안감|원단|재질",
    re.IGNORECASE,
)

_DOCUMENT_LABELS = re.compile(
    r"(?:product\s*(?:name|identifier)|trade\s*name|item\s*name|article\s*name|"
    r"model(?:\s*name)?|style(?:\s*name)?|제품명|품명|모델명)\s*[:：\-]?\s*(.+)",
    re.IGNORECASE,
)

_CAS_PATTERN = re.compile(r"(?<!\d)([1-9]\d{1,6}-\d{2}-\d)(?!\d)")

_COUNTRY_PATTERNS: tuple[tuple[str, str], ...] = (
    ("EU", r"\bEU\b|European\s+Union|유럽\s*연합|유럽"),
    ("미국", r"\bU\.?S\.?A?\.?\b|United\s+States(?:\s+of\s+America)?|미국"),
    ("영국", r"\bU\.?K\.?\b|United\s+Kingdom|Great\s+Britain|영국"),
    ("일본", r"\bJP\b|Japan|일본"),
    ("중국", r"\bCN\b|China|P\.?R\.?C\.?|중국"),
    ("베트남", r"\bVN\b|Vietnam|베트남"),
    ("인도", r"\bIN\b|India|인도"),
    ("대만", r"\bTW\b|Taiwan|대만"),
    ("캐나다", r"\bCA\b|Canada|캐나다"),
    ("호주", r"\bAU\b|Australia|호주"),
    ("뉴질랜드", r"\bNZ\b|New\s+Zealand|뉴질랜드"),
    ("대한민국", r"\bKR\b|South\s+Korea|Republic\s+of\s+Korea|대한민국|한국"),
)

_DESTINATION_LABEL = re.compile(
    r"판매\s*(?:국|지역)|수출\s*(?:국|지역)|대상\s*시장|"
    r"\btarget\s+markets?\b|\bmarkets?\b|\bdestination\b|"
    r"\bcountry\s+of\s+sale\b|\bexport\s+(?:to|market)\b",
    re.IGNORECASE,
)

_ORIGIN_LABEL = re.compile(
    r"\bcountry\s+of\s+origin\b|\bmade\s+in\b|\borigin\s*[:：]|원산지|제조국",
    re.IGNORECASE,
)

def _clean_text(value: str) -> str:
    """제어문자를 제거하되 표·문단 분석을 위해 줄바꿈은 보존한다."""
    normalized = unicodedata.normalize("NFKC", value or "")
    normalized = "".join(
        character
        for character in normalized
        if character in {"\n", "\r", "\t"} or ord(character) >= 32
    )
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in normalized.splitlines()]
    return "\n".join(line for line in lines if line)


def _extract_with_reader(reader) -> PdfDocument:
    """pypdf Reader에서 페이지 텍스트를 제한 길이로 추출한다."""
    from pypdf.errors import LimitReachedError

    if reader.is_encrypted:
        raise PdfReadError("암호가 설정된 PDF입니다. 암호를 해제한 뒤 다시 업로드해 주세요.")

    page_count = len(reader.pages)
    if page_count == 0:
        raise PdfReadError("페이지가 없는 PDF입니다.")
    if page_count > MAX_PDF_PAGES:
        raise PdfReadError(f"PDF는 최대 {MAX_PDF_PAGES}페이지까지 읽을 수 있습니다.")

    page_texts: list[str] = []
    warnings: list[str] = []
    remaining = MAX_EXTRACTED_CHARS
    truncated = False
    for page_number, page in enumerate(reader.pages, start=1):
        if remaining <= 0:
            page_texts.append("")
            truncated = True
            continue
        try:
            extracted = _clean_text(page.extract_text() or "")
        except (LimitReachedError, MemoryError) as error:
            raise PdfReadError(
                "PDF 처리 안전 한도를 초과했습니다. 파일을 나누거나 다시 저장한 뒤 시도해 주세요."
            ) from error
        except Exception as error:  # 손상된 개별 페이지 때문에 전체 화면이 중단되지 않게 한다.
            page_texts.append("")
            warnings.append(f"{page_number}페이지 텍스트를 읽지 못했습니다: {type(error).__name__}")
            continue
        if len(extracted) > remaining:
            extracted = extracted[:remaining]
            truncated = True
        page_texts.append(extracted)
        remaining -= len(extracted)

    metadata = reader.metadata
    title = _clean_text(str(getattr(metadata, "title", "") or "")) if metadata else ""
    return PdfDocument(
        page_count=page_count,
        page_texts=tuple(page_texts),
        title=title[:160],
        truncated=truncated,
        warnings=tuple(warnings),
    )


def read_pdf_document(data: bytes) -> PdfDocument:
    """PDF 바이트에서 텍스트를 추출하고 자원 제한을 적용한다."""
    if not data:
        raise PdfReadError("비어 있는 파일입니다. 다른 PDF를 선택해 주세요.")
    if len(data) > MAX_PDF_BYTES:
        raise PdfReadError("PDF는 15MB 이하만 읽을 수 있습니다.")
    if b"%PDF-" not in data[:1024]:
        raise PdfReadError("PDF 형식을 확인할 수 없습니다. 올바른 PDF 파일을 선택해 주세요.")

    try:
        from pypdf import PdfReader, apply_configuration
        from pypdf.errors import LimitReachedError
    except ImportError as error:  # 배포 의존성 누락 시에도 화면 전체는 유지한다.
        raise PdfReadError("PDF 읽기 모듈을 불러오지 못했습니다. 관리자에게 알려 주세요.") from error

    try:
        # pypdf 기본값(스트림당 75MB)보다 낮게 제한해 압축 폭탄과 과도한
        # 콘텐츠 연산으로부터 공개 Streamlit 프로세스를 보호한다.
        with apply_configuration(
            maximum_declared_stream_length=MAX_DECOMPRESSED_STREAM_BYTES,
            array_based_stream_maximum_output_length=MAX_DECOMPRESSED_STREAM_BYTES,
            jbig2_maximum_output_length=MAX_DECOMPRESSED_STREAM_BYTES,
            lzw_maximum_output_length=MAX_DECOMPRESSED_STREAM_BYTES,
            run_length_maximum_output_length=MAX_DECOMPRESSED_STREAM_BYTES,
            zlib_maximum_output_length=MAX_DECOMPRESSED_STREAM_BYTES,
            brotli_maximum_output_length=MAX_DECOMPRESSED_STREAM_BYTES,
            image_maximum_buffer_size=MAX_DECOMPRESSED_STREAM_BYTES,
            stream_decoding_work_maximum_length=MAX_DECOMPRESSED_STREAM_BYTES * 2,
            stream_parsing_work_maximum_count=250_000,
            xform_maximum_invocations_per_extraction=500,
            xmp_maximum_input_length=1_000_000,
            page_tree_maximum_entries=256,
            page_tree_maximum_depth=32,
            page_tree_maximum_page_entries=2_000,
        ):
            reader = PdfReader(
                BytesIO(data),
                strict=False,
                root_object_recovery_limit=1_000,
                xref_stream_maximum_entries=200_000,
            )
            return _extract_with_reader(reader)
    except PdfReadError:
        raise
    except (LimitReachedError, MemoryError) as error:
        raise PdfReadError(
            "PDF 처리 안전 한도를 초과했습니다. 파일을 나누거나 다시 저장한 뒤 시도해 주세요."
        ) from error
    except Exception as error:  # pypdf가 손상 구조에 대해 다양한 예외를 낼 수 있다.
        raise PdfReadError("PDF 구조를 읽지 못했습니다. 파일을 다시 저장한 뒤 시도해 주세요.") from error


def _unique(values: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(value for value in values if value))


def _document_types(text: str, filename: str = "") -> tuple[str, ...]:
    found: list[str] = []
    header_lines = text.splitlines()[:8]
    sds_heading = any(
        re.fullmatch(
            r"\s*(?:(?:material\s+)?safety\s+data\s+sheet(?:\s*\(M?SDS\))?|"
            r"M?SDS|물질안전보건자료(?:\s*\(M?SDS\))?)"
            r"(?:\s*(?:according\s+to|regulation|rev(?:ision)?\.?|version|date)\b.*|"
            r"\s*[-–—:|]\s*(?!(?:available|reviewed|attached)\b).+)?\s*",
            line,
            re.I,
        )
        for line in header_lines
    )
    sds_filename = re.search(
        r"(?:^|[\s_.-])M?SDS(?:$|[\s_.-])",
        Path(filename).stem,
        re.I,
    )
    if sds_heading or sds_filename:
        found.append("SDS")
    tds_heading = any(
        re.fullmatch(
            r"\s*(?:technical\s+data\s*sheet|TDS|기술\s*(?:자료|데이터시트))"
            r"(?:\s*(?:rev(?:ision)?\.?|version|date)\b.*|"
            r"\s*[-–—:|]\s*(?!(?:available|reviewed|attached)\b).+)?\s*",
            line,
            re.I,
        )
        for line in header_lines
    )
    tds_filename = re.search(
        r"(?:^|[\s_.-])TDS(?:$|[\s_.-])",
        Path(filename).stem,
        re.I,
    )
    if tds_heading or tds_filename:
        found.append("TDS")
    if re.search(
        r"product\s+specification|bill\s+of\s+materials|\bBOM\b|fiber\s*content|"
        r"fibre\s*content|제품\s*사양서|혼용률|섬유\s*조성",
        text,
        re.I,
    ):
        found.append("제품 사양서")
    if re.search(r"test\s+report|certificate\s+of\s+analysis|시험\s*성적서|검사\s*성적서", text, re.I):
        found.append("시험성적서")
    return _unique(found) or ("일반 PDF",)


def _is_chemical_document(text: str, document_types: tuple[str, ...]) -> bool:
    """SDS 및 화학제품형 TDS를 섬유 제품 문서와 구분한다."""
    if "SDS" in document_types:
        return True
    if "TDS" not in document_types or "제품 사양서" in document_types:
        return False

    textile_signals = (
        (r"\bfabric\b|원단", 2),
        (r"\btextile\b|섬유", 2),
        (r"fiber\s*content|fibre\s*content|혼용률|섬유\s*조성", 3),
        (r"\bconstruction\b|제품\s*구조", 1),
        (r"\bmembrane\b|멤브레인", 1),
        (r"\bDWR\b|durable\s+water\s+repellent|발수\s*가공", 1),
        (r"target\s+market|판매\s*(?:국|지역)|수출\s*(?:국|지역)", 2),
        (r"\bgarment\b|\byarn\b|의류|원사", 1),
    )
    chemical_signals = (
        (r"\bCAS(?:\s*(?:No\.?|Number))?\b|\d{2,7}-\d{2}-\d", 3),
        (r"\bingredients?\b|성분\s*(?:명|정보|구성)", 2),
        (r"\b(?:polyester\s+)?resin\b|수지", 2),
        (r"\badhesive\b|접착제", 2),
        (r"\b(?:dispersion|emulsion|mixture)\b|분산액|에멀전|혼합물", 2),
        (r"chemical\s+composition|화학\s*조성", 2),
        (r"product\s+form\s*[:：-]?\s*(?:liquid|paste|powder)|제품\s*형태\s*[:：-]?\s*(?:액상|페이스트|분말)", 2),
    )
    textile_score = sum(
        weight for pattern, weight in textile_signals if re.search(pattern, text, re.I)
    )
    chemical_score = sum(
        weight for pattern, weight in chemical_signals if re.search(pattern, text, re.I)
    )
    return chemical_score > textile_score


def _candidate_name(
    document: PdfDocument,
    filename: str,
    chemical_document: bool,
) -> tuple[str, str]:
    candidates: list[str] = []
    for page_text in document.page_texts[:3]:
        lines = page_text.splitlines()
        for index, line in enumerate(lines):
            match = _DOCUMENT_LABELS.search(line)
            if match:
                value = match.group(1).strip(" :：-|/")
                if value:
                    candidates.append(value)
            elif re.fullmatch(
                r"product\s*(?:name|identifier)|trade\s*name|제품명|품명",
                line.strip(),
                re.I,
            ) and index + 1 < len(lines):
                candidates.append(lines[index + 1].strip())

    if document.title:
        candidates.append(document.title)
    stem = Path(filename).stem
    stem = re.sub(
        r"(?i)(?:^|[\s_\-])(SDS|MSDS|TDS|spec(?:ification)?|rev(?:ision)?\s*[\w.\-]*|20\d{2}[\-.]?\d{0,2}[\-.]?\d{0,2})(?=$|[\s_\-])",
        " ",
        stem,
    )
    stem = re.sub(r"[_\-]+", " ", stem).strip()
    if stem:
        candidates.append(stem)

    generic = re.compile(
        r"^(?:safety\s+data\s+sheet|material\s+safety\s+data\s+sheet|technical\s+data\s+sheet|"
        r"product\s+specification|test\s+report|untitled|document)$",
        re.I,
    )
    name = next(
        (
            re.sub(r"\s+", " ", value).strip()[:120]
            for value in candidates
            if 2 <= len(value.strip()) <= 160 and not generic.fullmatch(value.strip())
        ),
        "",
    )
    return ("", name) if chemical_document else (name, "")


def _find_ratio(line: str, alias_pattern: str) -> tuple[float | None, int]:
    number = r"(?P<ratio>\d{1,3}(?:[.,]\d+)?)"
    patterns = (
        rf"{number}\s*%\s*(?:of\s*)?(?:{alias_pattern})",
        rf"(?:{alias_pattern})(?:\s+(?:fiber|fibre))?\s*[:：\-]?\s*{number}\s*%",
    )
    for pattern in patterns:
        match = re.search(pattern, line, re.I)
        if match:
            ratio = float(match.group("ratio").replace(",", "."))
            if 0 < ratio <= 100:
                return ratio, match.start()
    material_match = re.search(alias_pattern, line, re.I)
    return None, material_match.start() if material_match else len(line)


def _materials(document: PdfDocument, chemical_document: bool) -> tuple[MaterialCandidate, ...]:
    # 화학제품 SDS/TDS의 성분표는 섬유 혼용률이 아니다. 단, 같은 문서에
    # Fiber content/혼용률이 명시되어 제품 사양서로도 분류된 경우만 허용한다.
    if chemical_document:
        return ()

    hits: dict[str, tuple[int, int, int, MaterialCandidate]] = {}
    for page_number, page_text in enumerate(document.page_texts, start=1):
        lines = page_text.splitlines()
        for index, line in enumerate(lines):
            window = " ".join(lines[max(0, index - 1) : min(len(lines), index + 2)])
            contextual = bool(_MATERIAL_CONTEXT.search(window))
            has_percent = bool(re.search(r"\d{1,3}(?:[.,]\d+)?\s*%", line))
            chemical_component_line = bool(
                re.search(
                    r"\b(?:resin|adhesive|binder|dispersion|emulsion|ingredients?)\b|"
                    r"chemical\s+composition|coating\s+chemistry|수지|접착제|바인더|분산액|성분",
                    line,
                    re.I,
                )
            )
            if chemical_component_line:
                continue
            if not contextual and not has_percent:
                continue
            for canonical, aliases in _MATERIAL_PATTERNS:
                if canonical == "Polyester" and re.search(
                    r"recycled\s+polyester|r\s*pet|재생\s*폴리에스|리사이클(?:드)?\s*폴리에스",
                    line,
                    re.I,
                ):
                    continue
                if canonical == "Cotton" and re.search(r"organic\s+cotton|유기\s*(?:면|코튼)|오가닉\s*코튼", line, re.I):
                    continue
                for alias in aliases:
                    if not re.search(alias, line, re.I):
                        continue
                    # 두 글자 섬유 약어는 혼용률 문맥과 퍼센트가 모두 있어야 인정한다.
                    short_alias = alias in {
                        r"(?<![a-z])pes(?![a-z])",
                        r"(?<![a-z])co(?![a-z])",
                        r"(?<![a-z])el(?![a-z])",
                        r"(?<![a-z])wo(?![a-z])",
                        r"(?<![a-z])vi(?![a-z])",
                        r"(?<![a-z])pp(?![a-z])",
                        r"(?<![a-z])li(?![a-z])",
                    }
                    if short_alias and not (contextual and has_percent):
                        continue
                    ratio, position = _find_ratio(line, alias)
                    candidate = MaterialCandidate(
                        name=canonical,
                        ratio=ratio,
                        page=page_number,
                        evidence=line[:220],
                    )
                    current = hits.get(canonical)
                    quality = 0 if ratio is not None else 1
                    if current is None or (quality, page_number, position) < current[:3]:
                        hits[canonical] = (quality, page_number, position, candidate)
                    break

    ordered = sorted(hits.values(), key=lambda item: (item[1], item[2], item[0]))
    return tuple(item[3] for item in ordered)


def _valid_cas(value: str) -> bool:
    digits, check_digit = value.replace("-", "")[:-1], int(value[-1])
    total = sum(int(digit) * weight for weight, digit in enumerate(reversed(digits), start=1))
    return total % 10 == check_digit


def _cas_numbers(text: str) -> tuple[str, ...]:
    found: list[str] = []
    for clause in re.split(r"[\n;•]+", text):
        for match in _CAS_PATTERN.finditer(clause):
            value = match.group(1)
            if _valid_cas(value) and not _match_is_negated(clause, match):
                found.append(value)
    return _unique(found)


def _destinations(document: PdfDocument) -> tuple[str, ...]:
    contexts: list[str] = []
    for page_text in document.page_texts:
        lines = page_text.splitlines()
        for index, line in enumerate(lines):
            label_match = _DESTINATION_LABEL.search(line)
            if not label_match:
                continue
            context = line[label_match.end() :].strip(" :：-|")
            if not context and index + 1 < len(lines):
                next_line = lines[index + 1]
                if not _ORIGIN_LABEL.search(next_line):
                    context = next_line
            context = _ORIGIN_LABEL.split(context, maxsplit=1)[0]
            # 제외 시장은 자동 수출국 후보에 포함하지 않는다. 영어는 제외
            # 표현 뒤가 대상이고, 한국어는 대상 뒤에 '제외'가 붙는다.
            context = re.split(
                r"\b(?:excluding|except|not\s+for\s+sale\s+in)\b",
                context,
                maxsplit=1,
                flags=re.I,
            )[0]
            context = re.sub(
                r"(?:^|[,;/])\s*[^,;/]+?\s*제외\s*[:：-]?\s*",
                " ",
                context,
            )
            if context:
                contexts.append(context)
    found: list[str] = []
    for canonical, pattern in _COUNTRY_PATTERNS:
        if any(re.search(pattern, context, re.I) for context in contexts):
            found.append(canonical)
    return tuple(found)


def _match_is_negated(clause: str, match: re.Match[str]) -> bool:
    """키워드 바로 앞·뒤에 연결된 부정 표현만 해당 증거에 적용한다."""
    before = clause[max(0, match.start() - 64) : match.start()]
    after = clause[match.end() : min(len(clause), match.end() + 48)]
    nearby = f"{before[-36:]} {after[:36]}"
    negative_detection = re.search(
        r"\bnot\s+detected\b|\bnon[\s-]*detect(?:ed)?\b|"
        r"\bN\.?\s*D\.?(?:\b|$)|below\s+(?:the\s+)?limit|"
        r"불검출|미검출|검출\s*한계\s*미만",
        nearby,
        re.I,
    )
    explicit_positive = re.search(
        r"\b(?:detected|exceeded|fail(?:ed)?)\b|(?<!불)(?<!미)검출|초과|부적합",
        nearby,
        re.I,
    )
    if explicit_positive and not negative_detection:
        return False
    preceding = re.search(
        r"(?:\bno\b|\bnot\b|\bwithout\b|does\s+not\s+contain|"
        r"(?:complies?(?:\s+with)?|compliant(?:\s+with)?|conforms?(?:\s+to)?|meets?)[^.;:]{0,30}|"
        r"no\s+intentionally\s+added|free\s+of|미사용|미함유|무첨가|"
        r"불검출|미검출|없음|미적용)\s*(?:[:：,/-]\s*)?$",
        before,
        re.I,
    )
    following = re.match(
        r"\s*(?:[-–—:/,]\s*)?(?:free\b|not\s+detected|below\s+(?:the\s+)?limit|"
        r"N\.?\s*D\.?(?:\b|$)|"
        r".{0,24}\b(?:pass(?:ed)?|compliant|conforms?|meets?)\b|"
        r"미사용|미함유|무첨가|불검출|미검출|없음|미적용|기준\s*미만)",
        after,
        re.I,
    )
    return bool(preceding or following)


def _positive_pattern(text: str, pattern: str) -> bool:
    # 부정 표현은 같은 줄에서도 해당 키워드에 직접 연결된 경우에만 적용한다.
    # 예: "ePTFE membrane / PFAS-free DWR"에서 ePTFE 증거는 유지한다.
    for clause in re.split(r"[\n;•]+", text):
        for match in re.finditer(pattern, clause, re.I):
            if not _match_is_negated(clause, match):
                return True
    return False


def _mapped_values(text: str, mappings: tuple[tuple[str, str], ...]) -> tuple[str, ...]:
    return tuple(value for value, pattern in mappings if _positive_pattern(text, pattern))


def _pfas_status(text: str) -> tuple[str, tuple[str, ...]]:
    # 마침표는 N.D. 같은 시험결과 약어를 깨뜨리므로 줄·세미콜론 단위로 본다.
    clauses = [clause.strip() for clause in re.split(r"[\n;•]+", text) if clause.strip()]
    strong_negative = re.compile(
        r"PFAS[\s-]*(?:free|미사용|미함유|무첨가)|no\s+intentionally\s+added\s+PFAS|"
        r"does\s+not\s+contain\s+PFAS|fluorine[\s-]*free|무불소|불소\s*(?:무첨가|미사용|미함유)",
        re.I,
    )
    positive = re.compile(
        r"\bPFAS\b|\bPFOA\b|\bPFOS\b|\bPFHxA\b|\bPFHxS\b|perfluoro|polyfluoro|"
        r"fluorotelomer|(?<![A-Za-z])e?PTFE(?![A-Za-z])",
        re.I,
    )
    negative_found = any(strong_negative.search(clause) for clause in clauses)
    positive_hits: list[tuple[str, re.Match[str]]] = []
    for clause in clauses:
        for match in positive.finditer(clause):
            if not _match_is_negated(clause, match):
                positive_hits.append((clause, match))
    terms: list[str] = []
    for _, match in positive_hits:
        terms.append(match.group(0).upper() if len(match.group(0)) <= 8 else match.group(0))
    if positive_hits and negative_found:
        return "상충 정보", _unique(terms)
    if positive_hits:
        return "PFAS 사용·포함 가능", _unique(terms)
    if negative_found:
        return "PFAS-free 확인", ()
    return "미확인", ()


def _sds_composition_text(document: PdfDocument) -> str:
    """SDS의 규제 언급이 아닌 Section 3 성분 정보만 추린다."""
    text = document.text
    section_match = re.search(
        r"(?:section\s*3\b|3\s*[.:：]\s*(?:composition|ingredients)|제\s*3\s*항)"
        r"[\s\S]*?(?=(?:section\s*4\b|4\s*[.:：]\s*(?:first|응급)|제\s*4\s*항)|\Z)",
        text,
        re.I,
    )
    if section_match:
        return section_match.group(0)

    lines = text.splitlines()
    selected: list[str] = []
    for index, line in enumerate(lines):
        if _CAS_PATTERN.search(line) or re.search(r"ingredients?|성분\s*(?:명|정보|구성)", line, re.I):
            selected.extend(lines[max(0, index - 1) : min(len(lines), index + 3)])
    return "\n".join(dict.fromkeys(selected))


def analyze_pdf_document(document: PdfDocument, filename: str = "document.pdf") -> PdfInsights:
    """추출 텍스트를 현재 제품 입력 필드에 맞는 후보값으로 분석한다."""
    text = document.text
    document_types = _document_types(text, filename)
    chemical_document = _is_chemical_document(text, document_types)
    product_name, trade_name = _candidate_name(document, filename, chemical_document)
    materials = _materials(document, chemical_document)
    test_report_only = (
        "시험성적서" in document_types
        and not any(kind in document_types for kind in ("SDS", "TDS", "제품 사양서"))
    )
    if test_report_only:
        chemical_text = ""
    elif "SDS" in document_types:
        chemical_text = _sds_composition_text(document)
    else:
        chemical_text = text
    cas_numbers = _cas_numbers(chemical_text)

    ratios = [candidate.ratio for candidate in materials]
    composition_complete = bool(materials) and all(ratio is not None for ratio in ratios)
    if composition_complete:
        composition_complete = abs(sum(ratio for ratio in ratios if ratio is not None) - 100.0) < 0.01

    membranes = _mapped_values(
        text,
        (
            ("PTFE/ePTFE 멤브레인", r"(?:e?PTFE).{0,24}(?:membrane|film)|(?:membrane|film).{0,24}(?:e?PTFE)"),
            ("TPU 멤브레인", r"(?:TPU|thermoplastic\s+polyurethane).{0,24}(?:membrane|film)|(?:membrane|film).{0,24}(?:TPU|thermoplastic\s+polyurethane)"),
            ("PU 멤브레인", r"(?<!T)(?:\bPU\b|polyurethane).{0,24}(?:membrane|film)|(?:membrane|film).{0,24}(?<!T)(?:\bPU\b|polyurethane)"),
            ("PE 멤브레인", r"(?:\bPE\b|polyethylene).{0,24}(?:membrane|film)|(?:membrane|film).{0,24}(?:\bPE\b|polyethylene)"),
        ),
    )
    coatings = _mapped_values(
        text,
        (
            ("PU 코팅", r"(?:\bPU\b|polyurethane).{0,20}coat(?:ed|ing)|coat(?:ed|ing).{0,20}(?:\bPU\b|polyurethane)|PU\s*코팅"),
            ("PVC 코팅", r"(?:\bPVC\b|polyvinyl\s+chloride).{0,20}coat(?:ed|ing)|PVC\s*코팅"),
            ("Acrylic 코팅", r"acrylic.{0,20}coat(?:ed|ing)|아크릴\s*코팅"),
            ("Silicone 코팅", r"silicone.{0,20}coat(?:ed|ing)|실리콘\s*코팅"),
        ),
    )
    laminations = _mapped_values(
        text,
        (
            ("Hot-melt 접착제", r"hot[\s-]*melt.{0,20}(?:adhesive|laminat)|핫멜트.{0,15}(?:접착|라미)"),
            ("수계 접착제", r"water[\s-]*(?:based|borne).{0,20}(?:adhesive|laminat)|수계.{0,15}(?:접착|라미)"),
            ("용제형 접착제", r"solvent[\s-]*based.{0,20}(?:adhesive|laminat)|용제형.{0,15}(?:접착|라미)"),
            ("PU 접착제", r"(?:\bPU\b|polyurethane).{0,20}(?:adhesive|laminat)|PU\s*접착"),
        ),
    )
    finishings = _mapped_values(
        text,
        (
            ("DWR 발수 가공", r"\bDWR\b|durable\s+water\s+repellent|발수\s*가공"),
            ("방오 가공", r"stain\s+repellent|soil\s+repellent|방오\s*가공"),
            ("난연 가공", r"flame\s+retardant|fire\s+retardant|난연\s*가공"),
            ("항균 가공", r"antimicrobial|antibacterial|항균\s*가공"),
            ("유연 가공", r"soften(?:er|ing)|유연\s*가공"),
            ("주름방지 가공", r"wrinkle[\s-]*resistant|easy[\s-]*care|주름\s*방지"),
            ("워싱", r"garment\s+wash|워싱"),
        ),
    )
    processes = _mapped_values(
        text,
        (
            ("편직", r"\bknit(?:ted|ting)?\b|편직"),
            ("직조", r"\bwov(?:en|ing)\b|\bweav(?:e|ing)\b|직조"),
            ("부직포", r"\bnon[\s-]*woven\b|spunbond|meltblown|부직포"),
            ("봉제", r"\bsew(?:n|ing)?\b|stitched|cut[\s-]*and[\s-]*sew|봉제"),
            ("염색", r"\bdye(?:d|ing)?\b|염색"),
            ("프린팅", r"screen\s+print|heat\s+transfer|sublimation|\bprinting?\b|프린팅|날염"),
            ("발수", r"\bDWR\b|durable\s+water\s+repellent|발수"),
            ("방수", r"waterproof(?:ing)?|방수"),
            ("PU 코팅", r"(?:\bPU\b|polyurethane).{0,20}coat(?:ed|ing)|PU\s*코팅"),
            ("코팅", r"\bcoat(?:ed|ing)\b|코팅"),
            ("라미네이팅", r"\blaminat(?:e|ed|ing|ion)\b|라미네이팅|라미네이션"),
            ("수지가공", r"resin\s+finish|crosslinking|수지\s*가공"),
            ("난연 코팅", r"(?:flame|fire)\s+retardant.{0,20}coat|난연\s*코팅"),
            ("난연", r"flame\s+retardant|fire\s+retardant|난연"),
            ("항균", r"antimicrobial|antibacterial|항균"),
            ("유연", r"soften(?:er|ing)|유연"),
            ("재활용 원사 가공", r"recycled\s+yarn|재생\s*원사|재활용\s*원사"),
        ),
    )
    if "PU 코팅" in processes:
        processes = tuple(value for value in processes if value != "코팅")
    if "난연 코팅" in processes:
        processes = tuple(value for value in processes if value != "난연")
    chemicals = list(
        _mapped_values(
            chemical_text,
            (
                ("C6 fluorotelomer 발수제", r"\bC6\b.{0,24}fluorotelomer|fluorotelomer.{0,24}\bC6\b"),
                ("C8 fluorotelomer 발수제", r"\bC8\b.{0,24}fluorotelomer|fluorotelomer.{0,24}\bC8\b"),
                ("PFOA", r"\bPFOA\b|335-67-1"),
                ("PFOS", r"\bPFOS\b|1763-23-1"),
                ("포름알데히드계 수지", r"formaldehyde.{0,24}resin|포름알데히드.{0,16}수지"),
                ("프탈레이트계 가소제", r"phthalate.{0,24}plasticizer|프탈레이트.{0,16}가소제"),
                ("아조 염료", r"azo\s+dye|아조\s*염료"),
                ("DMF", r"\bDMF\b|68-12-2"),
                ("SCCP", r"\bSCCP\b|short[\s-]*chain\s+chlorinated\s+paraffin"),
                ("안티몬", r"\bantimony\b|안티몬|7440-36-0"),
                ("난연제", r"flame\s+retardant|fire\s+retardant|난연제"),
                ("항균제", r"antimicrobial\s+agent|antibacterial\s+agent|항균제"),
            ),
        )
    )
    pfas_status, detected_terms = _pfas_status(chemical_text)
    if pfas_status == "PFAS-free 확인" and "DWR 발수 가공" in finishings:
        chemicals.append("PFAS-free 발수제")

    warnings = list(document.warnings)
    if document.truncated:
        warnings.append("문서가 길어 앞부분 120,000자까지만 분석했습니다.")
    if len(materials) > 4:
        warnings.append("소재가 4개를 초과해 혼용률은 자동 반영하지 않습니다.")
    elif materials and not composition_complete:
        warnings.append("감지한 혼용률 합계가 100%가 아니어서 함량은 자동 확정하지 않습니다.")
    if pfas_status == "상충 정보":
        warnings.append("PFAS-free 주장과 PFAS 가능 성분이 함께 감지되어 수동 확인이 필요합니다.")
    if test_report_only and (
        _CAS_PATTERN.search(text)
        or re.search(r"\bPFAS\b|\bPFOA\b|\bPFOS\b|\bPFHxA\b|\bPFHxS\b", text, re.I)
    ):
        warnings.append("시험성적서의 시험 대상 물질은 실제 함유 성분으로 자동 반영하지 않습니다.")

    destinations = _destinations(document)
    if chemical_document:
        destinations = ()
        membranes = ()
        coatings = ()
        laminations = ()
        finishings = ()
        processes = ()

    return PdfInsights(
        document_types=document_types,
        product_name=product_name,
        trade_name=trade_name,
        materials=materials,
        composition_complete=composition_complete,
        destinations=destinations,
        membranes=membranes,
        coatings=coatings,
        laminations=laminations,
        finishings=finishings,
        processes=processes,
        chemicals=_unique(chemicals),
        cas_numbers=cas_numbers,
        pfas_status=pfas_status,
        detected_terms=detected_terms,
        warnings=_unique(warnings),
    )


def preview_text(document: PdfDocument, limit: int = 6_000) -> str:
    """화면에서 확인할 수 있도록 페이지 번호를 붙인 제한 길이 미리보기를 만든다."""
    chunks: list[str] = []
    remaining = max(0, limit)
    for page_number, page_text in enumerate(document.page_texts, start=1):
        if not page_text or remaining <= 0:
            continue
        heading = f"[페이지 {page_number}]\n"
        available = max(0, remaining - len(heading))
        excerpt = page_text[:available]
        chunks.append(f"{heading}{excerpt}")
        remaining -= len(heading) + len(excerpt)
    value = "\n\n".join(chunks)
    if document.extracted_char_count > len(value):
        value += "\n\n… 미리보기 생략 …"
    return value
