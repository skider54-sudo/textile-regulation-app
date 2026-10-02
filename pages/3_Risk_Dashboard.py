"""등록 제품의 위험 현황을 집계하는 대시보드."""

import plotly.express as px
import streamlit as st

from utils.data_loader import load_products, load_regulations, merge_session_products
from utils.matching import build_dashboard_data
from utils.ui import page_heading, render_footer, setup_page


setup_page("Risk Dashboard")
page_heading(
    "PORTFOLIO OVERVIEW",
    "Risk Dashboard",
    "제품 포트폴리오의 위험 분포와 규제별 영향 범위를 확인합니다.",
)

products = merge_session_products(
    load_products(),
    st.session_state.get("registered_products", []),
)
regulations = load_regulations()
product_summary, impact_summary = build_dashboard_data(products, regulations)

counts = product_summary["위험도"].value_counts().to_dict()
metric_columns = st.columns(4)
metrics = [
    ("전체 등록 제품", len(product_summary)),
    ("고위험 제품", counts.get("높음", 0)),
    ("중위험 제품", counts.get("보통", 0)),
    ("저위험 제품", counts.get("낮음", 0)),
]
for column, (label, value) in zip(metric_columns, metrics):
    with column:
        st.metric(label, f"{value}개")

chart_col1, chart_col2 = st.columns([1.35, 1])
color_map = {"높음": "#D92D20", "보통": "#F79009", "낮음": "#12B76A"}

with chart_col1:
    st.markdown("#### 제품별 Risk Score")
    sorted_products = product_summary.sort_values("Risk Score", ascending=True)
    product_chart = px.bar(
        sorted_products,
        x="Risk Score",
        y="제품명",
        color="위험도",
        orientation="h",
        color_discrete_map=color_map,
        text="Risk Score",
        category_orders={"위험도": ["높음", "보통", "낮음"]},
    )
    product_chart.update_layout(
        height=max(340, len(sorted_products) * 48),
        margin=dict(l=10, r=15, t=10, b=20),
        xaxis=dict(range=[0, 105], title=None, gridcolor="#E8EDF2"),
        yaxis_title=None,
        legend_title=None,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Arial", color="#243B53"),
    )
    product_chart.update_traces(textposition="outside", cliponaxis=False)
    st.plotly_chart(product_chart, width="stretch", config={"displayModeBar": False})

with chart_col2:
    st.markdown("#### 위험도 분포")
    distribution = (
        product_summary.groupby("위험도", as_index=False)
        .size()
        .rename(columns={"size": "제품 수"})
    )
    donut = px.pie(
        distribution,
        names="위험도",
        values="제품 수",
        hole=0.62,
        color="위험도",
        color_discrete_map=color_map,
        category_orders={"위험도": ["높음", "보통", "낮음"]},
    )
    donut.update_layout(
        height=340,
        margin=dict(l=10, r=10, t=10, b=10),
        legend=dict(orientation="h", y=-0.08, x=0.5, xanchor="center"),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Arial", color="#243B53"),
    )
    donut.update_traces(textinfo="percent+label", sort=False)
    st.plotly_chart(donut, width="stretch", config={"displayModeBar": False})

st.markdown("#### 규제별 영향 제품 수")
if impact_summary.empty:
    st.info("현재 매칭된 규제가 없습니다.")
else:
    impact_chart = px.bar(
        impact_summary.sort_values("영향 제품 수", ascending=True),
        x="영향 제품 수",
        y="규제명",
        orientation="h",
        text="영향 제품 수",
        color_discrete_sequence=["#1428A0"],
    )
    impact_chart.update_layout(
        height=max(320, len(impact_summary) * 48),
        margin=dict(l=10, r=20, t=10, b=20),
        xaxis=dict(dtick=1, title=None, gridcolor="#E8EDF2"),
        yaxis_title=None,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Arial", color="#243B53"),
    )
    impact_chart.update_traces(textposition="outside", cliponaxis=False)
    st.plotly_chart(impact_chart, width="stretch", config={"displayModeBar": False})

with st.expander("제품별 진단 데이터 보기"):
    st.dataframe(
        product_summary.sort_values("Risk Score", ascending=False),
        width="stretch",
        hide_index=True,
        column_config={
            "Risk Score": st.column_config.ProgressColumn(
                "Risk Score", min_value=0, max_value=100, format="%d"
            )
        },
    )

render_footer()
