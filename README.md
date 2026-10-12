# TexReg Insight

섬유제품의 소재, 가공방법, 사용 화학물질, 용도와 판매·수출국을 입력하면 관련 국내외 규제를 매칭하고 Risk Score와 대응방안을 보여주는 Streamlit 프로토타입입니다.

## 주요 기능

- Home: 프로젝트 소개와 4단계 진단 흐름
- 제품 정보 입력: 혼용률, 층별 제품 구조, 공정별 상품명·CAS·SDS/TDS·PFAS 정보 입력
- 진단 결과: 0~100 Risk Score, 층별 구조, 규제 상태·일정, 상세 대응방안
- 제품 데이터베이스: 진단 당시 규제 스냅샷, 현재 규제 비교, 공식 출처 실시간 변경 감지
- 최신 규제 모니터링: 6시간 주기 공식 API·Atom·공고 목록 수집, 신규 문서·원문 변경 검토함
- 예시 범위: 제품 32개, 규제 38개, EU·미국·영국·일본·중국·베트남·인도·대만·캐나다·호주·뉴질랜드·대한민국 12개 시장
- CSV 기반 데이터: `data/products.csv`, `data/regulations.csv`

## 프로젝트 구조

```text
.
├─ app.py
├─ data/
│  ├─ products.csv
│  ├─ regulations.csv
│  ├─ regulation_actions.csv
│  ├─ regulation_timeline.csv
│  ├─ monitoring_sources.csv
│  ├─ regulatory_monitor_state.json
│  └─ regulatory_monitor_events.json
├─ pages/
│  ├─ 1_Product_Input.py
│  ├─ 2_Diagnosis_Result.py
│  ├─ 3_Risk_Dashboard.py
│  └─ 4_Regulation_Monitor.py
├─ scripts/
│  └─ run_regulatory_monitor.py
├─ .github/workflows/
│  └─ regulatory-monitor.yml
├─ texreg_core/
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

제품 기록을 열면 관련 규제의 HTTPS 공식 출처를 확인하고 ETag·Last-Modified·정규화 본문 지문을 저장합니다. 6시간 이내의 성공 결과는 재사용하며 `공식 출처 지금 다시 확인` 버튼으로 강제 갱신할 수 있습니다. 원문 변경은 `검토 필요`로 표시되며 미검토 변경이 Risk Score를 자동으로 바꾸지는 않습니다.

GitHub Actions의 `Regulatory Monitor` 워크플로는 6시간마다 등록 규제 원문과 12개 시장의 공식 API·Atom·공고 목록을 확인합니다. 첫 실행은 기준선을 만들고, 다음 실행부터 새 문서와 본문 변경을 `data/regulatory_monitor_events.json`에 누적합니다. Streamlit의 `최신 규제 모니터링` 화면에서 검토 후보·출처 상태·오류를 확인할 수 있습니다. 대한민국 국가법령정보 Open API까지 사용하려면 GitHub 저장소 Secrets에 `KOREA_LAW_OC`를 설정해야 합니다. 다른 출처는 해당 키 없이도 계속 확인됩니다.

자동 감지 결과는 법적 효력이나 적용 범위를 확정하지 않습니다. 담당자가 공식 원문을 검토해 승인한 뒤 세 규제 CSV를 갱신해야 Risk Score와 대응방안에 반영됩니다.

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
