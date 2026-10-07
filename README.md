# TexReg Insight

섬유제품의 소재, 가공방법, 사용 화학물질, 용도와 판매·수출국을 입력하면 관련 국내외 규제를 매칭하고 Risk Score와 대응방안을 보여주는 Streamlit 프로토타입입니다.

## 주요 기능

- Home: 프로젝트 소개와 4단계 진단 흐름
- 제품 정보 입력: 혼용률, 층별 제품 구조, 공정별 상품명·CAS·SDS/TDS·PFAS 정보 입력
- 진단 결과: 0~100 Risk Score, 층별 구조, 규제 상태·일정, 상세 대응방안
- 제품 데이터베이스: 진단 당시 규제 스냅샷, 현재 규제 비교, 공식 출처 실시간 변경 감지
- 예시 범위: 제품 28개, 규제 29개, EU·미국·영국·일본·중국·캐나다·호주·대한민국 8개 시장
- CSV 기반 데이터: `data/products.csv`, `data/regulations.csv`

## 프로젝트 구조

```text
.
├─ app.py
├─ data/
│  ├─ products.csv
│  ├─ regulations.csv
│  ├─ regulation_actions.csv
│  └─ regulation_timeline.csv
├─ pages/
│  ├─ 1_Product_Input.py
│  ├─ 2_Diagnosis_Result.py
│  └─ 3_Risk_Dashboard.py
├─ utils/
│  ├─ data_loader.py
│  ├─ history.py
│  ├─ matching.py
│  ├─ source_monitor.py
│  └─ ui.py
├─ tests/
│  ├─ test_matching.py
│  ├─ test_history.py
│  ├─ test_product_database.py
│  └─ test_source_monitor.py
└─ requirements.txt
```

## 실행 방법

PowerShell에서 프로젝트 폴더로 이동한 뒤 아래 명령을 실행합니다.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

브라우저에서 `http://localhost:8501`을 열면 됩니다.

진단 이력은 기본적으로 `data/diagnosis_history.db` SQLite 파일에 보존됩니다. 각 진단의 제품 입력, 점수, 매칭 규제, 매칭 근거, 규제 일정과 대응방안이 불변 스냅샷으로 저장됩니다. 이 파일은 Git에 포함되지 않습니다. Streamlit Community Cloud에서 장기 보존하려면 외부 PostgreSQL 또는 Supabase 같은 영구 DB로 저장 계층을 교체해야 합니다.

제품 기록을 열면 관련 규제의 HTTPS 공식 출처를 확인하고 ETag·Last-Modified·정규화 본문 지문을 저장합니다. 6시간 이내의 성공 결과는 재사용하며 `공식 출처 지금 다시 확인` 버튼으로 강제 갱신할 수 있습니다. 원문 변경은 `검토 필요`로 표시되며 미검토 변경이 Risk Score를 자동으로 바꾸지는 않습니다. 완전히 신설된 규제까지 자동 탐지하려면 관할별 API·RSS 연계가 추가로 필요합니다.

## 테스트

```powershell
python -m unittest discover -s tests -v
```

## 데이터 수정

`data/products.csv`, `data/regulations.csv`, `data/regulation_actions.csv`, `data/regulation_timeline.csv`를 Excel 또는 텍스트 편집기로 수정할 수 있습니다. 컬럼명은 유지해야 합니다. `regulation_actions.csv`에는 규제별 실행 순서와 공식 출처가, `regulation_timeline.csv`에는 규제 상태·발표일·확정일·주요 시행일·유예기간·최근 확인일이 분리되어 있습니다. 규제 매칭 확장 컬럼은 다음과 같습니다.

- `매칭유형`: `country_baseline`, `country_adult_textile`, `adult_use_required`, `pfas`, `keyword`, `keyword_or_use`, `use_required`, `child_use_required`, `sustainability`
- `기본점수`: 해당 규제가 총점에 기여하는 시작 점수
- `화학키워드`, `공정키워드`, `소재키워드`, `용도키워드`: `|`로 구분한 매칭 단어

규제별 검토 기준일은 `regulation_timeline.csv`에서 관리하며 점수 기준은 시연용 예시입니다. 실제 수출 판단에는 최신 법령, 적용 예외와 시험자료를 별도로 확인해야 합니다.
