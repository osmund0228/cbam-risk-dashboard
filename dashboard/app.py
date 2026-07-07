import os
import requests
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from chart_helpers import (
    COLORS, EU_SCHEDULE,
    make_grade_pie, make_factor_donut,
    make_diverging_bar, make_grouped_factor_bar,
    make_cost_bar, make_cost_area,
    make_three_scenario_comparison,
    make_competitor_cbam_bar,
    make_grade_migration_bar,
    compute_costs,
)

st.set_page_config(
    page_title="CBAM 리스크 조기경보 대시보드",
    page_icon="🛃",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ── Data ─────────────────────────────────────────────────────────────────

@st.cache_data
def load_data():
    df = pd.read_csv("data/CBAM_Final_Risk_Analysis_2026.csv", dtype={"hs6": str})
    master = pd.read_csv("data/C123_master_table.csv", dtype={"hs6": str})
    latest = master[master["year"] == master["year"].max()]
    ci_map = (
        latest[["hs6", "ci_kor"]]
        .drop_duplicates("hs6")
        .set_index("hs6")["ci_kor"]
        .to_dict()
    )
    eu_weight_map = (
        latest[["hs6", "kr_eu_export_weight_kg"]]
        .drop_duplicates("hs6")
        .set_index("hs6")["kr_eu_export_weight_kg"]
        .to_dict()
    )
    competitor_ci_maps = {
        iso: (
            latest[["hs6", f"ci_{iso}"]]
            .drop_duplicates("hs6")
            .set_index("hs6")[f"ci_{iso}"]
            .to_dict()
        )
        for iso in ["chn", "ind", "jpn", "tur", "usa"]
        if f"ci_{iso}" in latest.columns
    }
    return df, ci_map, eu_weight_map, competitor_ci_maps


df, ci_map, eu_weight_map, competitor_ci_maps = load_data()


# ── Helpers ──────────────────────────────────────────────────────────────

def kpi_card(container, label, value, color):
    container.markdown(
        f"""<div style="border-left:4px solid {color};background:#F0F4FA;
        padding:14px 18px;border-radius:6px">
        <div style="font-size:12px;color:#6B7280;margin-bottom:4px">{label}</div>
        <div style="font-size:26px;font-weight:700;color:{color}">{value}</div>
        </div>""",
        unsafe_allow_html=True,
    )


def get_ci_default(hs6):
    raw = ci_map.get(hs6, 2.0)
    try:
        v = float(raw)
        return v if v == v else 2.0
    except (TypeError, ValueError):
        return 2.0


# ETS 원화 기준 가격 (업데이트 필요 시 여기만 수정)
ETS_RAW = {
    "chn": (84.09,  "CNY"),   # 상하이 SEEE
    "usa": (28.81,  "USD"),   # 캘리포니아 CCA
    "jpn": (3000.0, "JPY"),   # GX ETS 중간값 (1700~4300)
    "ind": (875.0,  "INR"),   # CCTS 중간값 (250~1500)
}

@st.cache_data(ttl=3600)
def fetch_live_rates():
    """EUR 기준 환율 API (open.er-api.com). 실패 시 하드코딩 폴백."""
    defaults = {"CNY": 7.60, "USD": 1.045, "JPY": 163.0, "INR": 87.0, "KRW": 1576.0}
    try:
        resp = requests.get("https://open.er-api.com/v6/latest/EUR", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("result") == "success":
                r = data["rates"]
                return {
                    "CNY": r.get("CNY", defaults["CNY"]),
                    "USD": r.get("USD", defaults["USD"]),
                    "JPY": r.get("JPY", defaults["JPY"]),
                    "INR": r.get("INR", defaults["INR"]),
                    "KRW": r.get("KRW", defaults["KRW"]),
                    "updated": data.get("time_last_update_utc", ""),
                    "live": True,
                }
    except Exception:
        pass
    return {**defaults, "updated": "API 연결 실패", "live": False}


def ets_to_eur(raw_price, currency, fx):
    return raw_price / fx.get(currency, 1.0)


def get_eu_vol_default(hs6):
    raw = eu_weight_map.get(hs6, 0)
    try:
        v = float(raw)
        return max(1.0, v / 1000) if v == v else 1.0  # kg → 톤, NaN guard
    except (TypeError, ValueError):
        return 1.0


# ── Header ───────────────────────────────────────────────────────────────

LOGO = "data/Emblem_of_the_Korea_Customs_Service.svg"
col_logo, col_title = st.columns([1, 11])
with col_logo:
    if os.path.exists(LOGO):
        st.image(LOGO, width=68)
with col_title:
    st.markdown(
        "<h1 style='color:#0C2577;margin-bottom:2px'>CBAM 리스크 조기경보 대시보드</h1>"
        "<p style='color:#0A55A3;margin-top:0'>"
        "2026년 예측 기준&nbsp;·&nbsp;HS6 163개 품목&nbsp;·&nbsp;대한민국 관세청"
        "</p>",
        unsafe_allow_html=True,
    )
st.divider()


# ── Tabs ─────────────────────────────────────────────────────────────────

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 전체 현황", "🔍 품목별 분석",
    "💰 CBAM 비용 시뮬레이터", "🌍 C3 경쟁국 CBAM 비교",
    "⚠️ 전환 리스크 시나리오",
])


# ════════════════════════════════════════════════════════════════════════
# TAB 1 — 전체 현황
# ════════════════════════════════════════════════════════════════════════

with tab1:
    st.markdown("**163개 CBAM 대상 품목의 2026년 리스크 등급 분포와 주요 위험요인을 한눈에 파악합니다.**")
    st.caption("💡 지원 우선순위 식별은 여기서 시작하세요. 품목 상세는 [품목별 분석] 탭으로 이동하세요.")
    st.markdown("")
    grade_counts = df["Risk_Grade"].value_counts()

    k1, k2, k3, k4 = st.columns(4)
    kpi_card(k1, "RED  고위험",    f"{grade_counts.get('RED',    0)}개", "#FF1300")
    kpi_card(k2, "YELLOW  중위험", f"{grade_counts.get('YELLOW', 0)}개", "#FEB325")
    kpi_card(k3, "GREEN  저위험",  f"{grade_counts.get('GREEN',  0)}개", "#2ECC71")
    kpi_card(k4, "전체 분석 품목", f"{len(df)}개",                        "#0A55A3")

    st.markdown("<br>", unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(make_grade_pie(df), use_container_width=True)
    with c2:
        st.plotly_chart(make_factor_donut(df), use_container_width=True)

    st.divider()
    st.subheader("전체 품목 리스트")

    GRADE_TEXT_COLORS = {"RED": "#C0392B", "YELLOW": "#B7770D", "GREEN": "#1E8449"}

    def color_grade(val):
        return f"color: {GRADE_TEXT_COLORS.get(val, '#000')}; font-weight: bold"

    display_df = (
        df[["hs6", "hs6_name_kr", "cbam_category", "Risk_Score", "Risk_Grade", "Main_Risk_Factor"]]
        .copy()
        .rename(columns={
            "hs6": "HS6", "hs6_name_kr": "품목명", "cbam_category": "카테고리",
            "Risk_Score": "리스크 점수", "Risk_Grade": "등급", "Main_Risk_Factor": "주요 위험요인",
        })
        .sort_values("리스크 점수", ascending=False)
    )

    st.dataframe(
        display_df.style.map(color_grade, subset=["등급"]),
        use_container_width=True,
        height=420,
    )

    st.download_button(
        "📥 CSV 다운로드",
        data=display_df.to_csv(index=False, encoding="utf-8-sig"),
        file_name="CBAM_리스크_2026.csv",
        mime="text/csv",
    )

    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("📋 관세청 활용 가이드 — 대시보드를 이용한 지원 대상 식별 절차"):
        red_n    = grade_counts.get("RED",    0)
        yellow_n = grade_counts.get("YELLOW", 0)
        green_n  = grade_counts.get("GREEN",  0)
        st.markdown(f"""
#### 🔴 RED {red_n}개 품목 — 즉시 지원 개시

| 순서 | 조치 | 이동 탭 |
|------|------|---------|
| ① | 리스크 점수 상위 품목의 수출 기업 명단 추출 | 품목별 분석 |
| ② | 탄소집약도(ci) 및 주요 위험요인 확인 | 품목별 분석 |
| ③ | 실측 데이터 전환 시 비용 절감 효과 산출 | CBAM 비용 시뮬레이터 |
| ④ | 탈탄소·시장 다변화 전략 비교 | CBAM 비용 시뮬레이터 |
| ⑤ | 2030·2034 전환 시나리오에서 비용 충격 사전 점검 | 전환 리스크 시나리오 |

**지원 수단**: 저탄소 전환 정책금융 · 검증기관 비용 지원 · CBAM 컴플라이언스 로드맵 제공

---

#### 🟡 YELLOW {yellow_n}개 품목 — 선제 모니터링

| 순서 | 조치 | 이동 탭 |
|------|------|---------|
| ① | 2030년 시나리오에서 RED 등급 진입 위험 여부 확인 | 전환 리스크 시나리오 |
| ② | EU 의존도 높은 품목 시장 다변화 절감 효과 시뮬레이션 | CBAM 비용 시뮬레이터 |

**지원 수단**: CBAM 컴플라이언스 컨설팅 · 배출량 측정 인프라 안내

---

#### 🟢 GREEN {green_n}개 품목 — 정기 모니터링 + 기회 발굴

| 조치 | 이동 탭 |
|------|---------|
| C3 음수(탄소 경쟁력 우위) 품목 → EU 수출 확대 가능성 검토 | C3 경쟁국 CBAM 비교 |
| CBAM 적용 범위 확대(다운스트림 포함) 동향 주시 | — |

**지원 수단**: 수출 마케팅 · EU 탄소중립 인증 취득 지원
""")



# ════════════════════════════════════════════════════════════════════════
# TAB 2 — 품목별 분석
# ════════════════════════════════════════════════════════════════════════

with tab2:
    st.markdown("**등급·카테고리·위험요인 필터로 관심 품목을 좁히고, 드릴다운으로 C1/C2/C3 기여 구조를 확인합니다.**")
    st.caption("💡 필터를 RED + 잠재 부담액(C1)으로 설정하면 즉각 탈탄소 투자가 필요한 품목을 빠르게 추립니다.")
    st.markdown("")
    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        grade_filter = st.multiselect("등급", ["RED", "YELLOW", "GREEN"], default=["RED"])
    with fc2:
        cat_filter = st.multiselect("카테고리", sorted(df["cbam_category"].unique()))
    with fc3:
        factor_filter = st.multiselect("주요 위험요인", df["Main_Risk_Factor"].unique().tolist())

    filtered = df.copy()
    if grade_filter:
        filtered = filtered[filtered["Risk_Grade"].isin(grade_filter)]
    if cat_filter:
        filtered = filtered[filtered["cbam_category"].isin(cat_filter)]
    if factor_filter:
        filtered = filtered[filtered["Main_Risk_Factor"].isin(factor_filter)]

    st.caption(f"{len(filtered)}개 품목 표시 중")

    if filtered.empty:
        st.warning("필터 조건에 해당하는 품목이 없습니다.")
    else:
        st.plotly_chart(make_diverging_bar(filtered), use_container_width=True)
        st.plotly_chart(make_grouped_factor_bar(filtered), use_container_width=True)

        st.divider()
        st.subheader("품목 드릴다운")

        item_map = {
            f"{r['hs6_name_kr']} ({r['hs6']})": r["hs6"]
            for _, r in filtered.iterrows()
        }
        selected_label = st.selectbox("품목 선택", list(item_map.keys()))
        row = filtered[filtered["hs6"] == item_map[selected_label]].iloc[0]

        d1, d2, d3 = st.columns(3)
        d1.metric("리스크 점수",   f"{row['Risk_Score']:.3f}")
        d2.metric("등급",          row["Risk_Grade"])
        d3.metric("주요 위험요인", row["Main_Risk_Factor"])

        c1v, c2v, c3v = row["Contribution_C1"], row["Contribution_C2"], row["Contribution_C3"]
        fig_drill = go.Figure(go.Bar(
            x=[c1v, c2v, c3v],
            y=["C1 잠재 부담액", "C2 수출 의존도", "C3 탄소 격차"],
            orientation="h",
            marker_color=[COLORS["C1"], COLORS["C2"], COLORS["C3_pos"] if c3v >= 0 else COLORS["C3_neg"]],
            text=[f"{c1v:.3f}", f"{c2v:.3f}", f"{c3v:.3f}"],
            textposition="outside",
            hovertemplate="%{y}: %{x:.3f}<extra></extra>",
        ))
        fig_drill.add_vline(x=0, line_color="#1F2B65", line_width=1.5)
        fig_drill.update_layout(
            title=f"{row['hs6_name_kr']} — 요인별 기여도",
            title_font_color="#0C2577",
            height=220,
            margin=dict(l=20, r=60, t=44, b=20),
            paper_bgcolor="#FFFFFF",
            plot_bgcolor="#FFFFFF",
            font=dict(color="#1F2B65"),
            xaxis=dict(gridcolor="#E8EDF5"),
        )
        st.plotly_chart(fig_drill, use_container_width=True)


# ════════════════════════════════════════════════════════════════════════
# TAB 3 — CBAM 비용 시뮬레이터
# ════════════════════════════════════════════════════════════════════════

with tab3:
    st.markdown("**품목과 기업 조건을 설정하면 탈탄소·시장 다변화 전략의 CBAM 절감 효과를 비교합니다.**")
    st.caption("💡 품목을 선택하면 탄소집약도(ci)와 EU 수출물량이 자동 입력됩니다. 슬라이더로 전략 효과를 즉시 확인하세요.")
    st.markdown("")

    inp, chart = st.columns([1, 2], gap="large")

    with inp:
        sim_map = {
            f"{r['hs6_name_kr']} ({r['hs6']})": r["hs6"]
            for _, r in df.iterrows()
        }
        sim_label      = st.selectbox("HS6 품목 선택", list(sim_map.keys()), key="sim_item")
        sim_hs6        = sim_map[sim_label]
        ci_default     = get_ci_default(sim_hs6)
        eu_vol_default = get_eu_vol_default(sim_hs6)

        export_vol    = st.number_input(
            "EU 수출물량 (톤/년)", min_value=1,
            value=max(1, int(eu_vol_default)), step=100,
            help="최근 연도 실적 자동 입력 (kg → 톤 변환)",
        )
        ci            = st.slider("탄소집약도 ci (tCO₂/t)", 0.10, 5.00,
                                  value=float(min(max(ci_default, 0.10), 5.00)), step=0.05,
                                  help="품목 선택 시 ci_kor 기준으로 자동 설정됩니다.")
        kau_price     = st.slider("KAU 가격 (EUR/tCO₂)", 5, 50, value=10)
        kr_free_alloc = st.slider("한국 무상할당 비율 (%)", 0, 100, value=90, step=5)
        target_year   = st.slider("분석 연도", 2026, 2034, value=2030)

        st.divider()
        st.markdown("**전략 시나리오 설정**")

        if ci > 0.10:
            ci_reduced = st.slider(
                "🏭 탈탄소 — 감축 후 ci (tCO₂/t)",
                min_value=0.10, max_value=float(ci),
                value=round(min(ci * 0.8, ci - 0.05), 2), step=0.05,
                help="EAF 전환·CCUS 등 탈탄소 투자 효과",
            )
        else:
            ci_reduced = ci
            st.info("탄소집약도가 최솟값(0.10)입니다.")

        eu_reduction = st.slider(
            "🌏 시장 다변화 — EU 수출 비중 감소율 (%)",
            min_value=0, max_value=100, value=20, step=5,
            help="비EU 시장(동남아·중동 등)으로 전환하는 비율",
        )

    with chart:
        years, kr_costs, eu_costs  = compute_costs(export_vol, ci,        kau_price, kr_free_alloc)
        _,     _,        eu_ci_red = compute_costs(export_vol, ci_reduced, kau_price, kr_free_alloc)
        _,     _,        eu_vol_red = compute_costs(
            export_vol * (1 - eu_reduction / 100), ci, kau_price, kr_free_alloc,
        )
        idx = years.index(target_year)

        saving_c1 = eu_costs[idx] - eu_ci_red[idx]
        saving_c2 = eu_costs[idx] - eu_vol_red[idx]
        pct_c1 = f"-{saving_c1 / eu_costs[idx] * 100:.1f}%" if eu_costs[idx] > 0 else "N/A"
        pct_c2 = f"-{saving_c2 / eu_costs[idx] * 100:.1f}%" if eu_costs[idx] > 0 else "N/A"

        m1, m2, m3 = st.columns(3)
        m1.metric("현행 CBAM 세금",          f"{eu_costs[idx]:,.0f} EUR")
        m2.metric("🏭 탈탄소 절감",           f"{saving_c1:,.0f} EUR", delta=pct_c1, delta_color="inverse")
        m3.metric("🌏 시장 다변화 절감",      f"{saving_c2:,.0f} EUR", delta=pct_c2, delta_color="inverse")

        st.plotly_chart(make_cost_bar(kr_costs[idx], eu_costs[idx], target_year),
                        use_container_width=True)

        st.plotly_chart(
            make_three_scenario_comparison(years, eu_costs, eu_ci_red, eu_vol_red, target_year),
            use_container_width=True,
        )


# ════════════════════════════════════════════════════════════════════════
# TAB 4 — C3 경쟁국 CBAM 부담 비교
# ════════════════════════════════════════════════════════════════════════

with tab4:
    st.markdown("**경쟁국 ETS 가격과 탄소집약도를 기반으로 EU 시장에서의 국가별 CBAM 부담(EUR/톤)을 비교합니다.**")
    st.caption("💡 CBAM 부담이 낮을수록 EU 시장 가격 경쟁력이 높습니다. 슬라이더로 각국 ETS 가격 변화 시 경쟁 구도를 시뮬레이션하세요.")
    st.markdown("")

    # 환율 실시간 조회
    fx = fetch_live_rates()
    if fx.get("live"):
        st.success(f"✅ 환율 실시간 연동 완료 — {fx['updated']} (open.er-api.com)")
    else:
        st.warning(f"⚠️ 환율 API 연결 실패 — 기본값 사용 중 ({fx['updated']})")

    # EUR 환산 기본값 계산
    def_chn = round(ets_to_eur(*ETS_RAW["chn"], fx), 1)
    def_usa = round(ets_to_eur(*ETS_RAW["usa"], fx), 1)
    def_jpn = round(ets_to_eur(*ETS_RAW["jpn"], fx), 1)
    def_ind = round(ets_to_eur(*ETS_RAW["ind"], fx), 1)
    krw_per_eur = fx.get("KRW", 1576.0)

    c3_inp, c3_chart = st.columns([1, 2], gap="large")

    with c3_inp:
        c3_label = st.selectbox("품목 선택", list(sim_map.keys()), key="c3_item")
        c3_hs6   = sim_map[c3_label]
        c3_year  = st.slider("분석 연도", 2026, 2034, 2030, key="c3_year")

        st.divider()
        st.markdown("**경쟁국 ETS 가격 (EUR/tCO₂)**")
        st.caption(f"환율 자동 환산 · 1 EUR = {krw_per_eur:,.0f}원 기준. 직접 수정 가능합니다.")

        kau_c3  = st.slider("🇰🇷 한국 KAU",               0.0, 60.0, 10.0, 0.5, key="c3_kau")
        ets_chn = st.slider("🇨🇳 중국 전국 ETS",           0.0, 60.0, def_chn, 0.5, key="c3_chn",
                            help=f"84.09 CNY → {def_chn} EUR (상하이 SEEE)")
        ets_usa = st.slider("🇺🇸 미국 캘리포니아 CCA",     0.0, 60.0, def_usa, 0.5, key="c3_usa",
                            help=f"28.81 USD → {def_usa} EUR")
        ets_jpn = st.slider("🇯🇵 일본 GX ETS (중간값)",    0.0, 60.0, def_jpn, 0.5, key="c3_jpn",
                            help=f"3,000 JPY → {def_jpn} EUR (회랑 1,700~4,300 중간값)")
        ets_ind = st.slider("🇮🇳 인도 CCTS (중간값)",      0.0, 60.0, def_ind, 0.5, key="c3_ind",
                            help=f"875 INR → {def_ind} EUR (예측가 250~1,500 중간값)")
        st.markdown("🇹🇷 **튀르키예**: 공식 가격 미형성 → 0 EUR 적용")

    with c3_chart:
        def safe_ci(iso):
            raw = competitor_ci_maps.get(iso, {}).get(c3_hs6)
            try:
                v = float(raw)
                return None if pd.isna(v) else v
            except (TypeError, ValueError):
                return None

        country_data = [
            {"country": "🇰🇷 한국",       "ci": get_ci_default(c3_hs6), "ets_eur": kau_c3,  "is_korea": True},
            {"country": "🇨🇳 중국",       "ci": safe_ci("chn"),          "ets_eur": ets_chn, "is_korea": False},
            {"country": "🇺🇸 미국(CA)",   "ci": safe_ci("usa"),          "ets_eur": ets_usa, "is_korea": False},
            {"country": "🇯🇵 일본",       "ci": safe_ci("jpn"),          "ets_eur": ets_jpn, "is_korea": False},
            {"country": "🇮🇳 인도",       "ci": safe_ci("ind"),          "ets_eur": ets_ind, "is_korea": False},
            {"country": "🇹🇷 튀르키예",   "ci": safe_ci("tur"),          "ets_eur": 0.0,     "is_korea": False},
        ]

        st.plotly_chart(
            make_competitor_cbam_bar(country_data, c3_year),
            use_container_width=True,
        )

        # 인사이트
        eua = EU_SCHEDULE[c3_year]["eua_price"]
        kor_cbam = get_ci_default(c3_hs6) * max(0.0, eua - kau_c3)

        worse  = [d["country"] for d in country_data
                  if not d["is_korea"] and d["ci"] is not None
                  and d["ci"] * max(0.0, eua - d["ets_eur"]) > kor_cbam]
        better = [d["country"] for d in country_data
                  if not d["is_korea"] and d["ci"] is not None
                  and d["ci"] * max(0.0, eua - d["ets_eur"]) < kor_cbam]

        if better:
            st.warning(f"⚠️ 한국보다 CBAM 부담 낮은 경쟁국 (EU 시장 가격 우위): **{', '.join(better)}**")
        if worse:
            st.success(f"✅ 한국보다 CBAM 부담 높은 경쟁국 (한국 유리): **{', '.join(worse)}**")

        st.divider()
        usd_krw = krw_per_eur / fx.get("USD", 1.045)
        cny_krw = krw_per_eur / fx.get("CNY", 7.60)
        jpy_krw = krw_per_eur / fx.get("JPY", 163.0) * 100
        inr_krw = krw_per_eur / fx.get("INR", 87.0)
        rggi_eur = round(ets_to_eur(45.38, "USD", fx), 1)

        st.markdown(f"""
**ETS 원화 가격 기준** (환율 {'실시간' if fx.get('live') else '기본값'})

| 국가 | 현지 가격 | EUR 환산 | 비고 |
|------|----------|---------|------|
| 🇨🇳 중국 | 84.09 CNY | ~{def_chn} EUR | 상하이 환경에너지거래소(SEEE) |
| 🇺🇸 미국(CA) | 28.81 USD | ~{def_usa} EUR | 캘리포니아 CCA |
| 🇺🇸 미국(RGGI) | 45.38 USD | ~{rggi_eur} EUR | 동부 주 연합 (참고용) |
| 🇯🇵 일본 | 1,700~4,300 JPY | {round(ets_to_eur(1700,'JPY',fx),1)}~{round(ets_to_eur(4300,'JPY',fx),1)} EUR | GX ETS 회랑 가격 |
| 🇮🇳 인도 | 250~1,500 INR | {round(ets_to_eur(250,'INR',fx),1)}~{round(ets_to_eur(1500,'INR',fx),1)} EUR | CCTS 예측가 |
| 🇹🇷 튀르키예 | 미형성 | 0 EUR | 시범 단계 |
""")
        st.caption(
            f"적용 환율: USD {usd_krw:,.1f}원 / CNY {cny_krw:,.1f}원 / "
            f"JPY {jpy_krw:,.1f}원(100엔) / INR {inr_krw:,.1f}원 / EUR {krw_per_eur:,.0f}원"
        )


# ════════════════════════════════════════════════════════════════════════
# TAB 5 — 전환 리스크 시나리오 (스트레스 테스트)
# ════════════════════════════════════════════════════════════════════════

with tab5:
    st.markdown("**EU 무상할당 단계적 폐지 일정에 따라 CBAM 부담이 커질 때 등급이 어떻게 이동하는지 확인합니다.**")
    st.caption(
        "💡 2030년이 핵심 전환점(factor 2.5% → 48.5%)입니다. "
        "슬라이더로 연도를 바꾸며 RED 신규 진입 품목을 확인하고 선제 지원 대상을 식별하세요. "
        "※ 근사 모델(C1 기여값 × 배율) — 방향성 판단 용도"
    )
    st.markdown("")

    CBAM_2026  = 1 - EU_SCHEDULE[2026]["free_alloc"]   # 0.025
    thresh_red    = df["Risk_Score"].quantile(0.80)
    thresh_yellow = df["Risk_Score"].quantile(0.50)

    STRESS_YEARS = [2026, 2028, 2030, 2031, 2034]

    scenario_results = []
    all_stress = {}

    for yr in STRESS_YEARS:
        cbam_yr = 1 - EU_SCHEDULE[yr]["free_alloc"]
        ratio   = cbam_yr / CBAM_2026

        ds = df.copy()
        ds["rs_stress"] = (
            ds["Contribution_C1"] * ratio
            + ds["Contribution_C2"]
            + ds["Contribution_C3"]
        )
        ds["grade_stress"] = ds["rs_stress"].apply(
            lambda s: "RED" if s >= thresh_red else ("YELLOW" if s >= thresh_yellow else "GREEN")
        )

        gc = ds["grade_stress"].value_counts()
        scenario_results.append({
            "label":  f"{yr}년\n(factor {cbam_yr*100:.0f}%)",
            "RED":    gc.get("RED",    0),
            "YELLOW": gc.get("YELLOW", 0),
            "GREEN":  gc.get("GREEN",  0),
        })
        all_stress[yr] = ds

    sel_yr = st.select_slider(
        "스트레스 시나리오 연도",
        options=STRESS_YEARS,
        value=2030,
        format_func=lambda y: (
            f"{y}년 — CBAM factor {(1 - EU_SCHEDULE[y]['free_alloc'])*100:.1f}%"
            f"  ({(1 - EU_SCHEDULE[y]['free_alloc']) / CBAM_2026:.1f}× 배율)"
        ),
    )

    cbam_sel   = 1 - EU_SCHEDULE[sel_yr]["free_alloc"]
    ratio_sel  = cbam_sel / CBAM_2026
    ds_sel     = all_stress[sel_yr]
    gc_sel     = ds_sel["grade_stress"].value_counts()

    k1, k2, k3, k4 = st.columns(4)
    kpi_card(k1, f"RED 예상 ({sel_yr}년)",    f"{gc_sel.get('RED',    0)}개", "#FF1300")
    kpi_card(k2, f"YELLOW 예상 ({sel_yr}년)", f"{gc_sel.get('YELLOW', 0)}개", "#FEB325")
    kpi_card(k3, f"GREEN 예상 ({sel_yr}년)",  f"{gc_sel.get('GREEN',  0)}개", "#2ECC71")
    kpi_card(k4, "CBAM factor 배율",           f"{ratio_sel:.1f}×",            "#0A55A3")

    st.markdown("<br>", unsafe_allow_html=True)
    st.plotly_chart(make_grade_migration_bar(scenario_results), use_container_width=True)

    st.divider()
    st.subheader("등급 전환 위험 품목")

    at_risk = ds_sel[ds_sel["Risk_Grade"] != ds_sel["grade_stress"]].copy()
    at_risk["등급 변화"] = at_risk["Risk_Grade"] + " → " + at_risk["grade_stress"]

    new_red    = at_risk[at_risk["grade_stress"] == "RED"   ].sort_values("rs_stress", ascending=False)
    new_yellow = at_risk[at_risk["grade_stress"] == "YELLOW"].sort_values("rs_stress", ascending=False)

    RENAME_ST = {
        "hs6": "HS6", "hs6_name_kr": "품목명", "cbam_category": "카테고리",
        "등급 변화": "등급 변화", "rs_stress": "예상 점수",
    }

    col_l, col_r = st.columns(2)
    with col_l:
        st.markdown(f"**🔴 RED 신규 진입 — {len(new_red)}개**")
        if new_red.empty:
            st.info("해당 없음")
        else:
            st.dataframe(
                new_red[["hs6", "hs6_name_kr", "cbam_category", "등급 변화", "rs_stress"]]
                .rename(columns=RENAME_ST),
                use_container_width=True,
                height=340,
            )

    with col_r:
        st.markdown(f"**🟡 YELLOW 신규 진입 — {len(new_yellow)}개**")
        if new_yellow.empty:
            st.info("해당 없음")
        else:
            st.dataframe(
                new_yellow[["hs6", "hs6_name_kr", "cbam_category", "등급 변화", "rs_stress"]]
                .rename(columns=RENAME_ST),
                use_container_width=True,
                height=340,
            )
