# CBAM 대시보드 디자인 가이드

**기반**: 대한민국 관세청 엠블럼 (`Emblem_of_the_Korea_Customs_Service.svg`)  
**원칙**: 관세청 공식 색상을 primary로 사용, 리스크 등급·요인 색상에 일관 적용

---

## 브랜드 색상 (엠블럼 추출)

| 이름 | HEX | 출처 | 용도 |
|------|-----|------|------|
| 관세청 블루 | `#0A55A3` | 방패 좌측 | Primary / 강조 |
| 관세청 네이비 | `#0C2577` | 방패 우측·하단 원 | Secondary / 배경·텍스트 |
| 리스크 보라 | `#8E44AD` | — | C2 수출 의존도 차트 (블루와 구분) |
| 관세청 골드 | `#FEB325` | 수평 저울대·원 배경 | Accent / 경고 |
| 관세청 레드 | `#FF1300` | 태극 상단 | 위험 / RED 등급 |
| 딥 네이비 | `#1F2B65` | 태극 경계 | 텍스트 다크 |
| 화이트 | `#FFFFFF` | 문자·문양 | 배경·텍스트 |

---

## 색상 매핑 규칙

### 리스크 등급

```python
GRADE_COLORS = {
    'RED':    '#FF1300',   # 관세청 레드 — 고위험
    'YELLOW': '#FEB325',   # 관세청 골드 — 중위험
    'GREEN':  '#2ECC71',   # 중립 녹색   — 저위험
}
```

### 리스크 요인 (C1/C2/C3)

```python
FACTOR_COLORS = {
    '잠재 부담액(C1)': '#0A55A3',   # 관세청 블루
    '수출 의존도(C2)': '#8E44AD',   # 보라 (블루와 구분)
    '탄소 격차(C3)':   '#FEB325',   # 관세청 골드
}
```

### 시뮬레이터 비용 구조

```python
SIM_COLORS = {
    'KR':  '#0A55A3',   # 한국 지불 비용 — 관세청 블루
    'EU':  '#FF1300',   # EU CBAM 세금  — 관세청 레드
}
```

### C3 양방향 막대 (음수 분리)

```python
C3_COLORS = {
    'pos': '#FEB325',   # 탄소 경쟁력 열위 (리스크 증가)
    'neg': '#2ECC71',   # 탄소 경쟁력 우위 (방어력)
}
```

---

## Streamlit 테마 (`config.toml`)

```toml
# .streamlit/config.toml
[theme]
primaryColor        = "#0A55A3"   # 관세청 블루
backgroundColor     = "#FFFFFF"
secondaryBackgroundColor = "#F0F4FA"   # 블루 틴트 (사이드바·카드)
textColor           = "#1F2B65"   # 딥 네이비
font                = "sans serif"
```

---

## 헤더 레이아웃

Tab 1 최상단에 관세청 로고 + 제목 배치.

```python
col_logo, col_title = st.columns([1, 8])
with col_logo:
    st.image("data/Emblem_of_the_Korea_Customs_Service.svg", width=72)
with col_title:
    st.markdown(
        "<h1 style='color:#0C2577; margin-bottom:0'>CBAM 리스크 조기경보 대시보드</h1>"
        "<p style='color:#0A55A3; margin-top:4px'>2026년 예측 기준 · HS6 163개 품목</p>",
        unsafe_allow_html=True
    )
st.divider()
```

---

## KPI 카드 스타일

`st.metric` 기본 스타일 위에 CSS로 배경색 주입.

```python
st.markdown("""
<style>
[data-testid="stMetric"] {
    background: #F0F4FA;
    border-left: 4px solid #0A55A3;
    border-radius: 6px;
    padding: 12px 16px;
}
</style>
""", unsafe_allow_html=True)
```

등급별 카드는 border-left 색상을 GRADE_COLORS로 구분:

| 카드 | border-left |
|------|-------------|
| RED 33개 | `#FF1300` |
| YELLOW 38개 | `#FEB325` |
| GREEN 92개 | `#2ECC71` |
| 전체 163개 | `#0A55A3` |

---

## 차트 공통 스타일

모든 Plotly 차트에 아래 레이아웃 베이스 적용.

```python
BASE_LAYOUT = dict(
    font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif", color="#1F2B65"),
    paper_bgcolor="#FFFFFF",
    plot_bgcolor="#FFFFFF",
    margin=dict(l=20, r=20, t=48, b=20),
    hoverlabel=dict(
        bgcolor="#0C2577",
        font_color="#FFFFFF",
        font_size=13,
    ),
)
```

차트별 적용:
```python
fig.update_layout(**BASE_LAYOUT, title_font_color="#0C2577")
fig.update_xaxes(gridcolor="#E8EDF5", zerolinecolor="#0A55A3")
fig.update_yaxes(gridcolor="#E8EDF5")
```

---

## 타이포그래피

| 요소 | 스타일 |
|------|--------|
| 대시보드 제목 (H1) | `#0C2577`, 28px, bold |
| 섹션 제목 (H3) | `#0A55A3`, 18px, bold |
| 본문 / 레이블 | `#1F2B65`, 14px |
| 인사이트 강조 | `#FF1300` or `#FEB325` bold |
| 캡션 / 주석 | `#6B7280`, 12px |

---

## 색상 사용 금지 사항

- 임의의 파스텔·무채색 차트 색상 사용 금지 → 반드시 위 팔레트에서 선택
- `#FF6B6B`, `#66b3ff` 등 노트북 원본 색상 그대로 이식 금지 (관세청 팔레트로 대체)
- 차트 배경에 다크 테마 사용 금지 (`plot_bgcolor` 항상 `#FFFFFF`)
