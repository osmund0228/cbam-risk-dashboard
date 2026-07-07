# CBAM 리스크 대시보드 — 구현 계획

**목적**: CBAM_Final_Risk_Analysis_2026.csv 기반 Streamlit 대시보드  
**범위**: 리스크 등급 시각화 + 품목 분석 + 기업용 비용 시뮬레이터  
**배포**: Streamlit Community Cloud (GitHub 연동)

---

## 폴더 구조

```
cbam_dashboard/
├── CLAUDE.md                       ← 이 파일
├── DESIGN.md                       ← 관세청 브랜드 디자인 가이드
├── app.py                          ← 단일 진입점 (st.tabs로 3섹션 구성)
├── chart_helpers.py                ← Plotly 차트 함수 모음
├── requirements.txt
├── .streamlit/
│   └── config.toml                 ← Streamlit 테마 (관세청 컬러)
└── data/
    └── CBAM_Final_Risk_Analysis_2026.csv   ← 원본에서 복사
```

**pages/ 폴더 미사용**: 163개 품목, 차트 7개 규모에서 multi-page는 과함.  
`st.tabs`로 단일 파일에 3섹션 구성 → 데이터·필터 상태 공유가 단순함.

---

## 데이터 명세 (`data/CBAM_Final_Risk_Analysis_2026.csv`)

| 컬럼 | 설명 |
|------|------|
| `hs6` | HS코드 6자리 |
| `hs6_name_kr` | 품목명(한글) |
| `cbam_category` | 철강/비료/알루미늄/시멘트/수소 |
| `c1_scaled_pred` | C1 스케일링된 예측값 (잠재 부담액) |
| `c2_scaled_pred` | C2 스케일링된 예측값 (수출 의존도) |
| `c3_scaled_pred` | C3 스케일링된 예측값 (탄소 격차) |
| `Risk_Score` | 최종 리스크 점수 (가중합) |
| `Risk_Grade` | RED / YELLOW / GREEN |
| `Main_Risk_Factor` | 잠재 부담액(C1) / 수출 의존도(C2) / 탄소 격차(C3) |
| `Contribution_C1` | C1 기여값 (가중 적용) |
| `Contribution_C2` | C2 기여값 (가중 적용) |
| `Contribution_C3` | C3 기여값 (가중 적용, 음수 가능) |

**등급 분포**: RED 33개 / YELLOW 38개 / GREEN 92개 / 합계 163개  
**가중치**: C1 39.86% / C2 35.25% / C3 24.89% (CRITIC 방법)

---

## 기술 스택

| 항목 | 선택 |
|------|------|
| 프레임워크 | Streamlit |
| 차트 | Plotly Express / Plotly Graph Objects (st 네이티브 차트 미사용) |
| 테이블 | st.dataframe (내장) |
| 데이터 | pandas |
| 폰트 | 시스템 한글 폰트 자동 인식 (Plotly), 별도 설정 불필요 |

```
# requirements.txt
streamlit>=1.35
pandas>=2.0
plotly>=5.20
numpy>=1.26
```

**Plotly 선택 이유**: 양방향 막대(C3 음수 분리), 도넛, 누적 영역 등 이 대시보드의  
핵심 차트들이 st 네이티브로 구현 불가. 호버 텍스트·색상·기준선 제어 필요.

---

## EU 무상할당 스케줄 (시뮬레이터 내장 데이터)

```python
EU_SCHEDULE = {
    2026: {'free_alloc': 0.975, 'eua_price': 97},
    2027: {'free_alloc': 0.950, 'eua_price': 112},
    2028: {'free_alloc': 0.900, 'eua_price': 125},
    2029: {'free_alloc': 0.775, 'eua_price': 137},
    2030: {'free_alloc': 0.515, 'eua_price': 150},
    2031: {'free_alloc': 0.390, 'eua_price': 174},
    2032: {'free_alloc': 0.265, 'eua_price': 192},
    2033: {'free_alloc': 0.140, 'eua_price': 215},
    2034: {'free_alloc': 0.000, 'eua_price': 248},
}
```

---

## 구현 명세

### `app.py` — 단일 파일 구조

```python
st.set_page_config(layout="wide", page_title="CBAM 리스크 대시보드")

@st.cache_data
def load_data():
    return pd.read_csv("data/CBAM_Final_Risk_Analysis_2026.csv")

df = load_data()

tab1, tab2, tab3 = st.tabs(["전체 현황", "품목별 분석", "CBAM 시뮬레이터"])
with tab1: ...
with tab2: ...
with tab3: ...
```

---

### Tab 1 — 전체 현황

**레이아웃**: 헤더(관세청 로고 + 제목) → KPI 카드 1행 → 차트 2개 (좌우) → 전체 테이블

**KPI 카드 (st.metric × 4)**
```
RED: 33개  |  YELLOW: 38개  |  GREEN: 92개  |  전체: 163개
```

**차트 좌 — 등급 분포 파이차트**
- RED(#E74C3C) / YELLOW(#F39C12) / GREEN(#27AE60)
- 호버: 개수, 비율

**차트 우 — 주요 리스크 요인 도넛차트**
- C1(#FF6B6B) / C2(#4D94FF) / C3(#66CC66)
- 전체 163개 기준 비중

**전체 테이블**
- `st.dataframe` 컬럼: hs6 / 품목명 / 카테고리 / Risk_Score / 등급 / 주요 요인
- 등급 컬럼 배경색 조건부 적용 (st.dataframe 스타일링)
- `st.download_button` 으로 CSV 다운로드 버튼 제공

---

### Tab 2 — 품목별 리스크 분석

**사이드바 필터 (3개 multiselect)**
```python
grade_filter    = st.sidebar.multiselect('등급', ['RED','YELLOW','GREEN'], default=['RED'])
category_filter = st.sidebar.multiselect('카테고리', ['철강','비료','알루미늄','시멘트','수소'])
factor_filter   = st.sidebar.multiselect('주요 요인', ['잠재 부담액(C1)','수출 의존도(C2)','탄소 격차(C3)'])
```

**차트 ① — 양방향(Diverging) 막대차트** (노트북 ② Plotly 이식)
- X: 기여값, Y: 품목명 (Risk_Score 내림차순)
- C1(#FF6B6B), C2(#4D94FF), C3 양수(#FFA500), C3 음수(#2ECC71)
- X=0 기준선 수직선 추가
- 호버: HS6코드 + 기여값

**차트 ② — 요인 그룹별 가로 바차트** (노트북 ③ Plotly 이식)
- Main_Risk_Factor 기준 정렬 → 같은 요인끼리 묶임
- 요인 그룹 경계에 수평 점선 추가
- 호버: 품목명, Risk_Score, 주요 요인

**품목 드릴다운**
- `st.selectbox` 로 품목 선택
- 선택 시 해당 품목 C1/C2/C3 기여값 수평 바 (3색)
- 해당 품목 기본 정보 `st.info` 블록 출력

---

### Tab 3 — CBAM 비용 시뮬레이터

**레이아웃**: 좌(입력 패널) / 우(차트 2개) / 하단(탭: 현행유지 vs 감축시나리오)

**좌측 입력 패널**

```python
# 품목 선택 → ci_kor 자동 입력 연동
hs6_selected = st.selectbox('HS6 품목 선택')
# → ci 기본값이 마스터 테이블의 ci_kor로 자동 설정

export_vol   = st.number_input('수출물량 (톤/년)', min_value=1, value=1000)
ci           = st.slider('탄소집약도 ci (tCO₂/t)', 0.1, 5.0, step=0.05)
kau_price    = st.slider('KAU 가격 (EUR/tCO₂)', 5, 50, value=10)
kr_free_alloc= st.slider('한국 무상할당 비율 (%)', 0, 100, value=90, step=5)
target_year  = st.slider('분석 연도', 2026, 2034, value=2030)
```

**우측 차트**
- 좌: 선택 연도 비용 구조 (한국 지불 vs EU CBAM) — Grouped Bar
- 우: 2026~2034 누적 비용 추이 — Stacked Area Chart

**하단 탭 — 감축 시나리오 비교 (추가 기능)**
```python
tab1, tab2 = st.tabs(['현행 유지', '감축 시나리오 비교'])

# tab2: 감축 후 ci 슬라이더 추가
ci_reduced = st.slider('감축 후 탄소집약도', 0.1, ci, value=ci*0.8)
# 현행 vs 감축 라인차트 비교 + 절감액 자동 계산
```

**인사이트 블록 (st.metric + st.success/warning)**
```python
st.metric('선택 연도 CBAM 비용', f'{eu_cost:,.0f} EUR', delta=...)
st.success(f'감축 시나리오 적용 시 {target_year}년 절감액: {saving:,.0f} EUR')
st.warning(f'현행 유지 시 2034년 누적 CBAM 비용: {total_2034:,.0f} EUR')
```

---

### `chart_helpers.py` — 차트 함수 모음

```python
def make_diverging_bar(df) -> go.Figure: ...
def make_grouped_factor_bar(df) -> go.Figure: ...
def make_grade_pie(df) -> go.Figure: ...
def make_factor_donut(df) -> go.Figure: ...
def make_cost_bar(kr_cost, eu_cost, year) -> go.Figure: ...
def make_cost_area(years, kr_costs, eu_costs) -> go.Figure: ...
def make_scenario_comparison(years, baseline, reduced) -> go.Figure: ...
```

---

## 색상 팔레트 (전체 통일)

관세청 엠블럼 기반. 상세 근거는 `DESIGN.md` 참조.

```python
COLORS = {
    # 등급
    'RED':    '#FF1300',   # 엠블럼 태극 적색
    'YELLOW': '#FEB325',   # 엠블럼 금색
    'GREEN':  '#27AE60',
    # 리스크 요인
    'C1':     '#0A55A3',   # 엠블럼 밝은 파랑
    'C2':     '#0C2577',   # 엠블럼 진한 네이비
    'C3_pos': '#FEB325',   # 엠블럼 금색
    'C3_neg': '#2ECC71',
    # 시뮬레이터
    'KR':     '#0A55A3',
    'EU':     '#FF1300',
}
```

---

## 구현 체크리스트

### Phase 0 — 환경 세팅
- [ ] `requirements.txt` 작성
- [ ] `data/CBAM_Final_Risk_Analysis_2026.csv` 복사 (`processed/` → `data/`)
- [ ] `.streamlit/config.toml` 작성 (DESIGN.md 테마 적용)
- [ ] `streamlit run app.py` 실행 확인

### Phase 1 — chart_helpers.py
- [ ] `make_grade_pie()` — 등급 분포 파이차트
- [ ] `make_factor_donut()` — 요인별 도넛차트
- [ ] `make_diverging_bar()` — 양방향 막대 (C3 음수 분리)
- [ ] `make_grouped_factor_bar()` — 요인 그룹 바차트
- [ ] `make_cost_bar()` — 연도별 비용 구조 바
- [ ] `make_cost_area()` — 2026~2034 누적 추이
- [ ] `make_scenario_comparison()` — 현행 vs 감축 라인차트

### Phase 2 — Tab 1 (전체 현황)
- [ ] 헤더: 관세청 로고(SVG) + 대시보드 제목
- [ ] KPI 카드 4개 (RED/YELLOW/GREEN/전체)
- [ ] 등급 파이차트 + 요인 도넛차트 배치
- [ ] 전체 테이블 (등급 컬럼 배경색)
- [ ] CSV 다운로드 버튼

### Phase 3 — Tab 2 (품목별 분석)
- [ ] 사이드바 필터 3개 (등급/카테고리/요인)
- [ ] 양방향 막대차트 (필터 연동)
- [ ] 요인 그룹 바차트 (필터 연동)
- [ ] 품목 드릴다운 selectbox + 상세 차트

### Phase 4 — Tab 3 (시뮬레이터)
- [ ] 입력 패널 (품목 선택 → ci 자동 연동)
- [ ] 선택 연도 비용 구조 바차트
- [ ] 2026~2034 누적 추이 stackplot
- [ ] 감축 시나리오 탭 + 비교 라인차트
- [ ] 인사이트 블록 (절감액 자동 계산)

### Phase 5 — 통합 및 배포
- [ ] `app.py` 에 st.tabs 3섹션 통합
- [ ] `@st.cache_data` 데이터 로드 캐싱 적용
- [ ] 전체 색상 COLORS 딕셔너리로 통일
- [ ] GitHub 레포 push
- [ ] Streamlit Community Cloud 배포

---

## 주의사항

- **한글 폰트**: Plotly는 시스템 폰트 자동 인식하므로 별도 설정 불필요. matplotlib 사용 금지.
- **C3 음수 처리**: Contribution_C3가 음수인 경우 `c3_neg` 색상(초록)으로 반대 방향 표시. 양수와 별도 시리즈.
- **ci_kor 연동**: 시뮬레이터 품목 선택 시 `C123_master_table.csv`의 `ci_kor` 최신값(2025년)을 기본값으로 자동 설정. 이 파일도 `data/` 에 복사 필요.
- **Bash 한글 금지**: 파일 Write 시 반드시 Write 툴 사용. Bash echo 금지.
- **노트북 ① 폐기**: `리스크 요인 시각화 및 시뮬레이터 제작.ipynb` 의 100% 누적 바는 C3 음수로 인해 100% 초과 발생 → 양방향 바(②)로 대체.
- **st 네이티브 차트 금지**: `st.bar_chart`, `st.line_chart` 등 네이티브 차트는 색상·호버 제어 불가. 전부 `st.plotly_chart(fig, use_container_width=True)` 사용.
