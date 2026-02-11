import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="브랜드 상품 흐름 대시보드", layout="wide")

# ----------------------------
# 상태 판정 로직
# ----------------------------
def get_verdict(inbound, outbound, is_shot, is_registered, is_on_sale):
    if inbound > 0 and outbound == 0:
        return "입고"
    if outbound > 0 and is_shot == 0:
        return "출고"
    if is_shot == 1 and is_registered == 0:
        return "촬영"
    if is_registered == 1 and is_on_sale == 0:
        return "등록"
    if is_on_sale == 1:
        return "판매개시"
    return "대기"

# ----------------------------
# 스냅샷 증감 계산
# ----------------------------
def compute_flow_deltas(df):
    if len(df) < 2:
        return None
    this_week = df.iloc[0]
    last_week = df.iloc[1]
    return {
        "입고": this_week["inboundDone"] - last_week["inboundDone"],
        "출고": this_week["outboundDone"] - last_week["outboundDone"],
        "촬영": this_week["shotDone"] - last_week["shotDone"],
        "등록": this_week["registeredDone"] - last_week["registeredDone"],
        "판매개시": this_week["onSaleDone"] - last_week["onSaleDone"],
    }

# ----------------------------
# 제목
# ----------------------------
st.title("브랜드 상품 흐름 대시보드")

# ----------------------------
# 사이드바 데이터 업로드
# ----------------------------
st.sidebar.header("데이터 업로드")

items_file = st.sidebar.file_uploader("상품 데이터 (CSV)", type=["csv"])
snapshots_file = st.sidebar.file_uploader("스냅샷 데이터 (CSV)", type=["csv"])

if items_file is None:
    st.info("상품 CSV 파일을 업로드하세요.")
    st.stop()

items_df = pd.read_csv(items_file)

required_columns = [
    "brand","yearSeason","styleCode","productName",
    "colorCode","colorName","sizeCode",
    "inboundQty","outboundQty","stockQty","salesQty",
    "isShot","isRegistered","isOnSale"
]

missing = [col for col in required_columns if col not in items_df.columns]
if missing:
    st.error(f"필수 컬럼 누락: {missing}")
    st.stop()

# ----------------------------
# verdict 생성
# ----------------------------
items_df["verdict"] = items_df.apply(
    lambda r: get_verdict(
        r["inboundQty"],
        r["outboundQty"],
        r["isShot"],
        r["isRegistered"],
        r["isOnSale"],
    ),
    axis=1,
)

# ----------------------------
# 필터 영역
# ----------------------------
col1, col2 = st.columns(2)

with col1:
    brand = st.selectbox("브랜드", sorted(items_df["brand"].unique()))

with col2:
    year_season = st.selectbox("연도·시즌", sorted(items_df["yearSeason"].unique()))

filtered_df = items_df[
    (items_df["brand"] == brand)
    & (items_df["yearSeason"] == year_season)
]

search = st.text_input("스타일코드 / 판정 검색")

if search:
    filtered_df = filtered_df[
        filtered_df["styleCode"].str.contains(search, case=False, na=False)
        | filtered_df["verdict"].str.contains(search, case=False, na=False)
    ]

# ----------------------------
# 흐름 집계 카드
# ----------------------------
st.subheader("흐름 집계")

flow_types = ["입고", "출고", "촬영", "등록", "판매개시"]
flow_counts = filtered_df["verdict"].value_counts()

cols = st.columns(len(flow_types))
for i, flow in enumerate(flow_types):
    count = int(flow_counts.get(flow, 0))
    cols[i].metric(flow, count)

# ----------------------------
# 스냅샷 증감 표시
# ----------------------------
if snapshots_file:
    snapshots_df = pd.read_csv(snapshots_file)
    deltas = compute_flow_deltas(snapshots_df)
    if deltas:
        st.subheader("전주 대비 증감")
        cols = st.columns(len(flow_types))
        for i, flow in enumerate(flow_types):
            cols[i].metric(flow, deltas.get(flow, 0))

# ----------------------------
# 흐름 선택
# ----------------------------
selected_flow = st.radio("상세 보기 흐름 선택", flow_types, horizontal=True)

flow_df = filtered_df[filtered_df["verdict"] == selected_flow]

# ----------------------------
# 상세 테이블
# ----------------------------
st.subheader(f"상세 현황 · {selected_flow}")
st.dataframe(flow_df, use_container_width=True)

# ----------------------------
# 엑셀 다운로드
# ----------------------------
def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="상세현황")
    return output.getvalue()

excel_data = to_excel(flow_df)

st.download_button(
    label="엑셀 다운로드",
    data=excel_data,
    file_name=f"상세현황_{selected_flow}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)
