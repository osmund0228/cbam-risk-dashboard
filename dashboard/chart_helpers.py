import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

COLORS = {
    'RED':    '#FF1300',
    'YELLOW': '#FEB325',
    'GREEN':  '#2ECC71',
    'C1':     '#0A55A3',   # 관세청 블루
    'C2':     '#8E44AD',   # 보라 (블루와 구분)
    'C3_pos': '#FEB325',   # 관세청 골드
    'C3_neg': '#2ECC71',   # 녹색 (경쟁 우위)
    'KR':     '#0A55A3',
    'EU':     '#FF1300',
}

GRADE_COLORS = {'RED': '#FF1300', 'YELLOW': '#FEB325', 'GREEN': '#2ECC71'}

FACTOR_COLORS = {
    '잠재 부담액(C1)': '#0A55A3',
    '수출 의존도(C2)': '#8E44AD',
    '탄소 격차(C3)':   '#FEB325',
}

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

BASE_LAYOUT = dict(
    font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif", color="#1F2B65"),
    paper_bgcolor="#FFFFFF",
    plot_bgcolor="#FFFFFF",
    margin=dict(l=20, r=20, t=48, b=20),
    hoverlabel=dict(bgcolor="#0C2577", font_color="#FFFFFF", font_size=13),
)


def make_grade_pie(df):
    counts = df['Risk_Grade'].value_counts().reset_index()
    counts.columns = ['등급', '품목 수']
    counts['등급'] = pd.Categorical(counts['등급'], categories=['RED', 'YELLOW', 'GREEN'], ordered=True)
    counts = counts.sort_values('등급')

    fig = go.Figure(go.Pie(
        labels=counts['등급'],
        values=counts['품목 수'],
        marker_colors=[GRADE_COLORS[g] for g in counts['등급']],
        textinfo='label+percent+value',
        hovertemplate='%{label}<br>%{value}개 (%{percent})<extra></extra>',
    ))
    fig.update_layout(
        **BASE_LAYOUT,
        title='등급별 품목 분포',
        title_font_color='#0C2577',
        height=360,
    )
    return fig


def make_factor_donut(df):
    counts = df['Main_Risk_Factor'].value_counts().reset_index()
    counts.columns = ['요인', '품목 수']

    fig = go.Figure(go.Pie(
        labels=counts['요인'],
        values=counts['품목 수'],
        marker_colors=[FACTOR_COLORS.get(f, '#999') for f in counts['요인']],
        hole=0.4,
        textinfo='label+percent+value',
        hovertemplate='%{label}<br>%{value}개 (%{percent})<extra></extra>',
    ))
    fig.update_layout(
        **BASE_LAYOUT,
        title='주요 리스크 요인 분포',
        title_font_color='#0C2577',
        height=360,
    )
    return fig


def make_diverging_bar(df):
    df = df.sort_values('Risk_Score', ascending=True).reset_index(drop=True)

    c1_pos = df['Contribution_C1'].clip(lower=0)
    c1_neg = df['Contribution_C1'].clip(upper=0)
    c2_pos = df['Contribution_C2'].clip(lower=0)
    c2_neg = df['Contribution_C2'].clip(upper=0)
    c3_pos = df['Contribution_C3'].clip(lower=0)
    c3_neg = df['Contribution_C3'].clip(upper=0)

    fig = go.Figure()

    # 리스크 증가 요인 (양수, 오른쪽)
    fig.add_trace(go.Bar(
        name='C1 잠재 부담액',
        y=df['hs6_name_kr'], x=c1_pos, orientation='h',
        marker_color=COLORS['C1'],
        customdata=df['hs6'].values,
        hovertemplate='<b>%{y}</b><br>HS6: %{customdata}<br>C1 기여: %{x:.3f}<extra></extra>',
    ))
    fig.add_trace(go.Bar(
        name='C2 수출 의존도',
        y=df['hs6_name_kr'], x=c2_pos, orientation='h',
        marker_color=COLORS['C2'],
        customdata=df['hs6'].values,
        hovertemplate='<b>%{y}</b><br>HS6: %{customdata}<br>C2 기여: %{x:.3f}<extra></extra>',
    ))
    fig.add_trace(go.Bar(
        name='C3 탄소 경쟁력 열위',
        y=df['hs6_name_kr'], x=c3_pos, orientation='h',
        marker_color=COLORS['C3_pos'],
        hovertemplate='<b>%{y}</b><br>C3(+) 탄소 열위: %{x:.3f}<extra></extra>',
    ))

    # 리스크 감소 요인 (음수, 왼쪽) — legend 숨김 (edge case)
    fig.add_trace(go.Bar(
        name='C1 방어',
        y=df['hs6_name_kr'], x=c1_neg, orientation='h',
        marker_color='rgba(10, 85, 163, 0.35)',
        showlegend=False,
        hovertemplate='<b>%{y}</b><br>C1(-) 부담 낮음: %{x:.3f}<extra></extra>',
    ))
    fig.add_trace(go.Bar(
        name='C2 방어 (수출 의존도 낮음)',
        y=df['hs6_name_kr'], x=c2_neg, orientation='h',
        marker_color='rgba(142, 68, 173, 0.35)',
        showlegend=False,
        hovertemplate='<b>%{y}</b><br>C2(-) EU 수출 의존도 낮음: %{x:.3f}<extra></extra>',
    ))
    fig.add_trace(go.Bar(
        name='C3 탄소 경쟁력 우위',
        y=df['hs6_name_kr'], x=c3_neg, orientation='h',
        marker_color=COLORS['C3_neg'],
        hovertemplate='<b>%{y}</b><br>C3(-) 탄소 우위: %{x:.3f}<extra></extra>',
    ))

    fig.add_vline(x=0, line_color='#1F2B65', line_width=1.5, line_dash='dash')
    fig.update_layout(
        **BASE_LAYOUT,
        barmode='relative',
        title='품목별 리스크 가중 요인(+) 및 상쇄 요인(-)',
        title_font_color='#0C2577',
        height=max(400, len(df) * 28),
        xaxis=dict(title='리스크 기여 점수', gridcolor='#E8EDF5', zerolinecolor='#0A55A3'),
        yaxis=dict(gridcolor='#E8EDF5'),
        legend=dict(orientation='h', yanchor='bottom', y=1.01, xanchor='right', x=1),
    )
    return fig


def make_grouped_factor_bar(df):
    df = df.sort_values(
        by=['Main_Risk_Factor', 'Risk_Score'], ascending=[True, True]
    ).reset_index(drop=True)

    fig = px.bar(
        df,
        x='Risk_Score',
        y='hs6_name_kr',
        color='Main_Risk_Factor',
        color_discrete_map=FACTOR_COLORS,
        orientation='h',
        title='주요 위험요인별 품목 그룹 및 리스크 점수',
        labels={'Risk_Score': '리스크 점수', 'hs6_name_kr': '', 'Main_Risk_Factor': '주요 위험요인'},
        custom_data=['hs6', 'cbam_category', 'Risk_Grade'],
    )
    fig.update_traces(
        hovertemplate=(
            '<b>%{y}</b><br>HS6: %{customdata[0]}<br>'
            '카테고리: %{customdata[1]}<br>등급: %{customdata[2]}<br>'
            '점수: %{x:.3f}<extra></extra>'
        ),
    )

    factor_vals = df['Main_Risk_Factor'].values
    for i in range(1, len(factor_vals)):
        if factor_vals[i] != factor_vals[i - 1]:
            fig.add_hline(y=i - 0.5, line_color='#6B7280', line_dash='dot', line_width=1)

    fig.update_layout(
        **BASE_LAYOUT,
        title_font_color='#0C2577',
        height=max(400, len(df) * 28),
        xaxis=dict(gridcolor='#E8EDF5'),
        yaxis=dict(gridcolor='#E8EDF5'),
        legend=dict(orientation='h', yanchor='bottom', y=1.01, xanchor='right', x=1),
    )
    return fig


def make_cost_bar(kr_cost, eu_cost, year):
    fig = go.Figure()
    fig.add_trace(go.Bar(
        name='한국 탄소비용',
        y=['한국 탄소비용'],
        x=[kr_cost],
        orientation='h',
        marker_color=COLORS['KR'],
        text=[f"{kr_cost:,.0f} EUR"],
        textposition='auto',
        hovertemplate=f"한국 탄소비용: {kr_cost:,.0f} EUR<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        name='EU CBAM 세금',
        y=['EU CBAM 세금'],
        x=[eu_cost],
        orientation='h',
        marker_color=COLORS['EU'],
        text=[f"{eu_cost:,.0f} EUR"],
        textposition='auto',
        hovertemplate=f"EU CBAM 세금: {eu_cost:,.0f} EUR<extra></extra>",
    ))
    fig.update_layout(
        **BASE_LAYOUT,
        title=f"{year}년 비용 구조 상세",
        title_font_color='#0C2577',
        xaxis=dict(title='비용 (EUR)', gridcolor='#E8EDF5'),
        height=200,
    )
    return fig


def make_cost_area(years, kr_costs, eu_costs, target_year):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=years, y=kr_costs,
        name='한국 탄소비용',
        stackgroup='one',
        fillcolor='rgba(10, 85, 163, 0.6)',
        line=dict(color=COLORS['KR'], width=2),
        hovertemplate='%{x}년<br>한국: %{y:,.0f} EUR<extra></extra>',
    ))
    fig.add_trace(go.Scatter(
        x=years, y=eu_costs,
        name='EU CBAM 세금',
        stackgroup='one',
        fillcolor='rgba(255, 19, 0, 0.6)',
        line=dict(color=COLORS['EU'], width=2),
        hovertemplate='%{x}년<br>EU CBAM: %{y:,.0f} EUR<extra></extra>',
    ))
    fig.add_vline(
        x=target_year, line_color='#1F2B65', line_width=2, line_dash='dash',
        annotation_text=f" {target_year}년", annotation_font_color='#1F2B65',
    )
    fig.update_layout(
        **BASE_LAYOUT,
        title='2026~2034년 비용 증가 추이 (현행 유지)',
        title_font_color='#0C2577',
        xaxis=dict(title='연도', tickvals=years, ticktext=[str(y) for y in years], gridcolor='#E8EDF5'),
        yaxis=dict(title='누적 비용 (EUR)', gridcolor='#E8EDF5'),
        height=300,
    )
    return fig


def make_scenario_comparison(years, baseline_eu, reduced_eu, target_year):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=years + years[::-1],
        y=baseline_eu + reduced_eu[::-1],
        fill='toself',
        fillcolor='rgba(46, 204, 113, 0.15)',
        line=dict(color='rgba(0,0,0,0)'),
        showlegend=False,
        hoverinfo='skip',
    ))
    fig.add_trace(go.Scatter(
        x=years, y=baseline_eu,
        name='현행 유지',
        mode='lines+markers',
        line=dict(color=COLORS['EU'], width=2.5),
        marker=dict(size=7),
        hovertemplate='%{x}년<br>현행 CBAM: %{y:,.0f} EUR<extra></extra>',
    ))
    fig.add_trace(go.Scatter(
        x=years, y=reduced_eu,
        name='감축 시나리오',
        mode='lines+markers',
        line=dict(color=COLORS['KR'], width=2.5, dash='dash'),
        marker=dict(size=7),
        hovertemplate='%{x}년<br>감축 CBAM: %{y:,.0f} EUR<extra></extra>',
    ))
    fig.add_vline(x=target_year, line_color='#1F2B65', line_width=1.5, line_dash='dot')
    fig.update_layout(
        **BASE_LAYOUT,
        title='EU CBAM 세금 — 현행 유지 vs 감축 시나리오',
        title_font_color='#0C2577',
        xaxis=dict(title='연도', tickvals=years, ticktext=[str(y) for y in years], gridcolor='#E8EDF5'),
        yaxis=dict(title='EU CBAM 세금 (EUR)', gridcolor='#E8EDF5'),
        height=380,
        legend=dict(orientation='h', yanchor='bottom', y=1.01, xanchor='right', x=1),
    )
    return fig


def make_competitor_cbam_bar(country_data, target_year):
    """
    country_data: list of {'country': str, 'ci': float|None, 'ets_eur': float, 'is_korea': bool}
    ci=None 이면 데이터 없음으로 제외
    """
    import math
    eua_price = EU_SCHEDULE[target_year]['eua_price']

    rows = []
    for d in country_data:
        ci = d.get('ci')
        if ci is None or (isinstance(ci, float) and math.isnan(ci)):
            continue
        cbam = ci * max(0.0, eua_price - d['ets_eur'])
        rows.append({
            'country': d['country'],
            'cbam':    cbam,
            'color':   '#FF1300' if d['is_korea'] else '#0A55A3',
        })

    rows.sort(key=lambda r: r['cbam'])

    fig = go.Figure(go.Bar(
        x=[r['cbam'] for r in rows],
        y=[r['country'] for r in rows],
        orientation='h',
        marker_color=[r['color'] for r in rows],
        text=[f"{r['cbam']:,.1f}" for r in rows],
        textposition='auto',
        hovertemplate='%{y}<br>CBAM 부담: %{x:,.2f} EUR/tCO₂<extra></extra>',
    ))
    fig.update_layout(
        **BASE_LAYOUT,
        title=f'{target_year}년 국가별 톤당 CBAM 부담 (EUA {eua_price} EUR/tCO₂ 기준)',
        title_font_color='#0C2577',
        xaxis=dict(title='CBAM 부담 (EUR/tCO₂)', gridcolor='#E8EDF5'),
        height=340,
    )
    return fig


def make_three_scenario_comparison(years, eu_baseline, eu_ci_reduced, eu_vol_reduced, target_year):
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=years + years[::-1],
        y=eu_baseline + eu_ci_reduced[::-1],
        fill='toself', fillcolor='rgba(10, 85, 163, 0.08)',
        line=dict(color='rgba(0,0,0,0)'),
        showlegend=False, hoverinfo='skip',
    ))
    fig.add_trace(go.Scatter(
        x=years + years[::-1],
        y=eu_baseline + eu_vol_reduced[::-1],
        fill='toself', fillcolor='rgba(230, 126, 34, 0.10)',
        line=dict(color='rgba(0,0,0,0)'),
        showlegend=False, hoverinfo='skip',
    ))
    fig.add_trace(go.Scatter(
        x=years, y=eu_baseline,
        name='현행 유지',
        mode='lines+markers',
        line=dict(color='#7F8C8D', width=2.5),
        marker=dict(size=7, symbol='circle'),
        hovertemplate='%{x}년<br>현행: %{y:,.0f} EUR<extra></extra>',
    ))
    fig.add_trace(go.Scatter(
        x=years, y=eu_ci_reduced,
        name='🏭 탈탄소 전략 (ci 감축)',
        mode='lines+markers',
        line=dict(color='#0A55A3', width=3, dash='dash'),
        marker=dict(size=8, symbol='diamond'),
        hovertemplate='%{x}년<br>탈탄소: %{y:,.0f} EUR<extra></extra>',
    ))
    fig.add_trace(go.Scatter(
        x=years, y=eu_vol_reduced,
        name='🌏 시장 다변화 (EU 물량 감소)',
        mode='lines+markers',
        line=dict(color='#E67E22', width=3, dash='dot'),
        marker=dict(size=8, symbol='square'),
        hovertemplate='%{x}년<br>다변화: %{y:,.0f} EUR<extra></extra>',
    ))

    fig.add_vline(x=target_year, line_color='#1F2B65', line_width=1.5, line_dash='dot')
    fig.update_layout(
        **BASE_LAYOUT,
        title='전략 비교 — 탈탄소(C1) vs 시장 다변화(C2)',
        title_font_color='#0C2577',
        xaxis=dict(title='연도', tickvals=years, ticktext=[str(y) for y in years], gridcolor='#E8EDF5'),
        yaxis=dict(title='EU CBAM 세금 (EUR)', gridcolor='#E8EDF5'),
        height=400,
        legend=dict(orientation='h', yanchor='bottom', y=1.01, xanchor='right', x=1),
    )
    return fig


def make_grade_migration_bar(scenario_results):
    """
    scenario_results: list of {'label': str, 'RED': int, 'YELLOW': int, 'GREEN': int}
    """
    labels  = [r['label']  for r in scenario_results]
    reds    = [r['RED']    for r in scenario_results]
    yellows = [r['YELLOW'] for r in scenario_results]
    greens  = [r['GREEN']  for r in scenario_results]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name='RED 고위험', x=labels, y=reds,
        marker_color=COLORS['RED'],
        text=reds, textposition='inside',
        hovertemplate='%{x}<br>RED: %{y}개<extra></extra>',
    ))
    fig.add_trace(go.Bar(
        name='YELLOW 중위험', x=labels, y=yellows,
        marker_color=COLORS['YELLOW'],
        text=yellows, textposition='inside',
        hovertemplate='%{x}<br>YELLOW: %{y}개<extra></extra>',
    ))
    fig.add_trace(go.Bar(
        name='GREEN 저위험', x=labels, y=greens,
        marker_color=COLORS['GREEN'],
        text=greens, textposition='inside',
        hovertemplate='%{x}<br>GREEN: %{y}개<extra></extra>',
    ))
    fig.update_layout(
        **BASE_LAYOUT,
        barmode='stack',
        title='시나리오별 등급 분포 변화 (CBAM factor 단계적 상승)',
        title_font_color='#0C2577',
        xaxis=dict(title='시나리오', gridcolor='#E8EDF5'),
        yaxis=dict(title='품목 수', gridcolor='#E8EDF5'),
        height=380,
        legend=dict(orientation='h', yanchor='bottom', y=1.01, xanchor='right', x=1),
    )
    return fig


def compute_costs(export_vol, ci, kau_price, kr_free_alloc):
    years = list(EU_SCHEDULE.keys())
    kr_costs, eu_costs = [], []
    kr_effective = kau_price * (1 - kr_free_alloc / 100)

    for y in years:
        billable = export_vol * ci * (1 - EU_SCHEDULE[y]['free_alloc'])
        kr_costs.append(billable * kr_effective)
        eu_costs.append(billable * max(0.0, EU_SCHEDULE[y]['eua_price'] - kr_effective))

    return years, kr_costs, eu_costs
