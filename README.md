# TexReg Insight

섬유제품의 소재, 가공방법, 사용 화학물질, 용도와 판매·수출국을 입력하면 관련 국내외 규제를 매칭하고 Risk Score와 대응방안을 보여주는 Streamlit 프로토타입입니다.

## 주요 기능

- Home: 프로젝트 소개와 4단계 진단 흐름
- 제품 정보 입력: 소재·공정·화학물질·용도·판매·수출국 입력
- 진단 결과: 0~100 Risk Score, 위험도, 관련 규제, 상세 대응방안
- Risk Dashboard: 제품별 점수, 위험도 분포, 규제별 영향 제품 수
- 예시 범위: 제품 21개, 규제 19개, EU·미국·영국·일본·대한민국 5개 시장
- CSV 기반 데이터: `data/products.csv`, `data/regulations.csv`

## 프로젝트 구조

```text
.
├─ app.py
├─ data/
│  ├─ products.csv
│  ├─ regulations.csv
│  └─ regulation_actions.csv
├─ pages/
│  ├─ 1_Product_Input.py
│  ├─ 2_Diagnosis_Result.py
│  └─ 3_Risk_Dashboard.py
├─ utils/
│  ├─ data_loader.py
│  ├─ matching.py
│  └─ ui.py
├─ tests/
│  └─ test_matching.py
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

## 테스트

```powershell
python -m unittest discover -s tests -v
```

## 데이터 수정

`data/products.csv`, `data/regulations.csv`, `data/regulation_actions.csv`를 Excel 또는 텍스트 편집기로 수정할 수 있습니다. 컬럼명은 유지해야 합니다. `regulation_actions.csv`에는 규제별 실행 순서, 권장시험, 필요자료, 담당부서, 일정, 완료기준과 공식 출처가 분리되어 있습니다. 규제 매칭 확장 컬럼은 다음과 같습니다.

- `매칭유형`: `country_baseline`, `country_adult_textile`, `adult_use_required`, `pfas`, `keyword`, `keyword_or_use`, `use_required`, `child_use_required`, `sustainability`
- `기본점수`: 해당 규제가 총점에 기여하는 시작 점수
- `화학키워드`, `공정키워드`, `소재키워드`, `용도키워드`: `|`로 구분한 매칭 단어

규제·대응 데이터의 검토 기준일은 2026-10-01이며 점수 기준은 시연용 예시입니다. 실제 수출 판단에는 최신 법령, 적용 예외와 시험자료를 별도로 확인해야 합니다.
