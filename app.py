import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="브랜드 상품 흐름 대시보드", layout="wide")

# ----------------------------
# Google Sheets 연동
# ----------------------------
def get_gsheet_client(credentials_dict):
    if credentials_dict is None:
        return None
    import gspread
    from google.oauth2.service_account import Credentials
    scope = [
        "https://www.googleapis.com/auth/spreadsheets.readonly",
        "https://www.googleapis.com/auth/drive.readonly",
    ]
    creds = Credentials.from_service_account_info(
        credentials_dict, scopes=scope
    )
    return gspread.authorize(creds)

def load_sheet_as_dataframe(client, spreadsheet_id, sheet_name=None, header_row=0):
    """header_row: 0 = 첫 번째 행이 헤더(기본), 1 = 두 번째 행이 헤더 등"""
    try:
        spreadsheet = client.open_by_key(spreadsheet_id)
        worksheet = spreadsheet.worksheet(sheet_name) if sheet_name else spreadsheet.sheet1
        rows = worksheet.get_all_values()
        if not rows or len(rows) <= header_row:
            return pd.DataFrame()
        # 헤더·컬럼명 앞뒤 공백 제거
        headers = [str(h).strip() for h in rows[header_row]]
        data_rows = rows[header_row + 1:]
        return pd.DataFrame(data_rows, columns=headers)
    except Exception as e:
        st.error(f"시트 읽기 오류: {e}")
        return None

# 스타일코드 앞 2자리 → 브랜드 한글명
BRAND_CODE_MAP = {
    "sp": "스파오",
    "rm": "로엠",
    "mi": "미쏘",
    "wh": "후아유",
    "nb": "뉴발란스",
    "eb": "에블린",
    "hp": "슈펜",
    "cv": "클라비스",
    "nk": "뉴발란스키즈",
}

def brand_from_style_code(style_code):
    """스타일코드 앞 2자리로 브랜드명 반환 (소문자로 매핑)"""
    if pd.isna(style_code) or not str(style_code).strip():
        return ""
    code = str(style_code).strip()[:2].lower()
    return BRAND_CODE_MAP.get(code, code.upper())

# 시트 컬럼명 → 앱 필수 컬럼명 매핑 (한글/다른 표기 지원)
COLUMN_ALIASES = {
    "브랜드": "brand",
    "연도시즌": "yearSeason",
    "연도·시즌": "yearSeason",
    "연도 시즌": "yearSeason",
    "시즌(Now)": "yearSeason",
    "스타일코드": "styleCode",
    "스타일 코드": "styleCode",
    "스타일코드(Now)": "styleCode",
    "상품명": "productName",
    "컬러코드": "colorCode",
    "색상코드": "colorCode",
    "컬러 코드": "colorCode",
    "컬러명": "colorName",
    "색상": "colorName",
    "컬러 명": "colorName",
    "칼라(Now)": "colorName",
    "사이즈코드": "sizeCode",
    "사이즈 코드": "sizeCode",
    "입고수량": "inboundQty",
    "출고수량": "outboundQty",
    "재고수량": "stockQty",
    "판매수량": "salesQty",
    "누적입고량(물류+입고조정+브랜드간)": "inboundQty",
    "출고량[출고-반품](매장+고객+샘플+브랜드간)": "outboundQty",
    "누적 판매량": "salesQty",
    "판매재고량(입고량-누판량)": "stockQty",
    "촬영여부": "isShot",
    "is_shot": "isShot",
    "등록여부": "isRegistered",
    "is_registered": "isRegistered",
    "판매개시여부": "isOnSale",
    "is_on_sale": "isOnSale",
}

def ensure_year_season_from_columns(df):
    """년도(Now) + 시즌(Now) → yearSeason 조합"""
    if "yearSeason" in df.columns:
        return df
    if "년도(Now)" in df.columns and "시즌(Now)" in df.columns:
        df = df.copy()
        df["yearSeason"] = df["년도(Now)"].astype(str) + df["시즌(Now)"].astype(str)
    return df

def apply_column_aliases(df):
    """컬럼명 앞뒤 공백 제거 후 알려진 별칭으로 매핑"""
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    df = ensure_year_season_from_columns(df)
    rename = {}
    for col in list(df.columns):
        if col in COLUMN_ALIASES:
            target = COLUMN_ALIASES[col]
            # 이미 있는 컬럼으로 덮어쓰지 않음 (예: yearSeason은 년도+시즌으로 이미 채움)
            if target not in df.columns or col == target:
                rename[col] = target
    return df.rename(columns=rename) if rename else df

def fill_missing_required_columns(df, required_columns):
    """없는 필수 컬럼을 기본값으로 채움 (시트 구조가 다를 때 대시보드만 동작하도록)"""
    df = df.copy()
    for col in required_columns:
        if col not in df.columns:
            if col in ("isShot", "isRegistered", "isOnSale"):
                df[col] = 0
            elif col in ("inboundQty", "outboundQty", "stockQty", "salesQty"):
                df[col] = 0
            else:
                df[col] = ""
    return df

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
st.caption("입고 · 출고 · 촬영 · 등록 · 판매개시 현황")

# ----------------------------
# Google Sheets 연결 (Secrets만 사용, UI 없음)
# ----------------------------
SPREADSHEET_OPTIONS = {
    "BASE_SPREADSHEET_ID": "BASE",
    "SP_SPREADSHEET_ID": "SP",
    "MI_SPREADSHEET_ID": "MI",
    "CV_SPREADSHEET_ID": "CV",
    "WH_SPREADSHEET_ID": "WH",
    "RM_SPREADSHEET_ID": "RM",
    "EB_SPREADSHEET_ID": "EB",
}

def get_spreadsheet_ids_from_secrets():
    ids = {}
    for secret_key, label in SPREADSHEET_OPTIONS.items():
        try:
            val = st.secrets.get(secret_key, "")
            if val and str(val).strip():
                ids[label] = str(val).strip()
        except Exception:
            pass
    return ids

creds_dict = None
try:
    if "gcp_service_account" in st.secrets:
        creds_dict = dict(st.secrets["gcp_service_account"])
    elif "google_service_account" in st.secrets:
        creds_dict = dict(st.secrets["google_service_account"])
except Exception:
    pass
gs_client = get_gsheet_client(creds_dict) if creds_dict else None

spreadsheet_ids = get_spreadsheet_ids_from_secrets()
if not spreadsheet_ids:
    st.error("Secrets에 스프레드시트 ID가 없습니다. BASE_SPREADSHEET_ID 등을 설정하세요.")
    st.stop()

# 기본값: Secrets 첫 번째 시트, 첫 시트 탭, 헤더 1행
selected_label = list(spreadsheet_ids.keys())[0]
spreadsheet_id = spreadsheet_ids[selected_label]
items_sheet_name = ""
header_row = 1
snapshots_sheet_name = ""

if not gs_client:
    st.info("Streamlit Secrets에 **gcp_service_account** 또는 **google_service_account**를 설정해 주세요.")
    st.stop()
items_df = load_sheet_as_dataframe(
    gs_client,
    spreadsheet_id,
    sheet_name=items_sheet_name if items_sheet_name.strip() else None,
    header_row=int(header_row) - 1,
)
if items_df is None:
    st.stop()
if len(items_df) == 0:
    st.warning("시트에 데이터가 없습니다.")
    st.stop()

# 한글/다른 컬럼명을 필수 컬럼명으로 매핑
items_df = apply_column_aliases(items_df)

# 브랜드: 스타일코드(Now) 앞 2자리 → 매핑 테이블 한글명
if "styleCode" in items_df.columns:
    items_df["brand"] = items_df["styleCode"].apply(brand_from_style_code)

# 시트에서 읽은 값은 문자열이므로 숫자 컬럼 변환
numeric_cols = [
    "inboundQty", "outboundQty", "stockQty", "salesQty",
    "isShot", "isRegistered", "isOnSale"
]
for col in numeric_cols:
    if col in items_df.columns:
        items_df[col] = pd.to_numeric(items_df[col], errors="coerce").fillna(0).astype(int)

required_columns = [
    "brand", "yearSeason", "styleCode", "productName",
    "colorCode", "colorName", "sizeCode",
    "inboundQty", "outboundQty", "stockQty", "salesQty",
    "isShot", "isRegistered", "isOnSale"
]

missing = [col for col in required_columns if col not in items_df.columns]
if missing:
    items_df = fill_missing_required_columns(items_df, required_columns)
    st.warning(f"일부 컬럼이 없어 기본값으로 채웠습니다: {missing}. (브랜드/연도·시즌 등은 시트 컬럼 매핑을 확인하세요.)")

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

# 연도 컬럼 (필터용, yearSeason 앞 4자리)
items_df["_year"] = items_df["yearSeason"].astype(str).str[:4]

# ----------------------------
# 필터 영역
# ----------------------------
col1, col2, col3, col4 = st.columns(4)
with col1:
    brand = st.selectbox("브랜드", sorted(items_df["brand"].unique()))
with col2:
    years = sorted(items_df["_year"].dropna().unique())
    year = st.selectbox("연도", years, key="year") if years else None
with col3:
    season_options = sorted(
        items_df.loc[items_df["_year"] == year, "yearSeason"].unique()
    ) if year is not None else []
    year_seasons = st.multiselect(
        "시즌",
        season_options,
        default=season_options if season_options else [],
        key="season",
    )
with col4:
    search = st.text_input(
        "스타일코드 검색",
        placeholder="스타일코드 또는 판정 상태 검색",
    )

if year is not None and year_seasons:
    filtered_df = items_df[
        (items_df["brand"] == brand)
        & (items_df["_year"] == year)
        & (items_df["yearSeason"].isin(year_seasons))
    ].copy()
else:
    filtered_df = items_df[(items_df["brand"] == brand)].copy()
    if year is not None:
        filtered_df = filtered_df[filtered_df["_year"] == year]
    if year_seasons:
        filtered_df = filtered_df[filtered_df["yearSeason"].isin(year_seasons)]

if search:
    filtered_df = filtered_df[
        filtered_df["styleCode"].astype(str).str.contains(search, case=False, na=False)
        | filtered_df["verdict"].str.contains(search, case=False, na=False)
    ]

total_n = len(filtered_df)
if total_n == 0:
    st.info("선택한 조건에 맞는 데이터가 없습니다.")
    st.stop()

# 스냅샷 증감 (카드에 함께 표시용)
deltas = None
if snapshots_sheet_name and snapshots_sheet_name.strip():
    snapshots_df = load_sheet_as_dataframe(
        gs_client, spreadsheet_id, sheet_name=snapshots_sheet_name.strip()
    )
    if snapshots_df is not None and len(snapshots_df) >= 2:
        snap_cols = ["inboundDone", "outboundDone", "shotDone", "registeredDone", "onSaleDone"]
        for c in snap_cols:
            if c in snapshots_df.columns:
                snapshots_df[c] = pd.to_numeric(snapshots_df[c], errors="coerce").fillna(0).astype(int)
        deltas = compute_flow_deltas(snapshots_df)

# ----------------------------
# 흐름 집계 카드 (클릭하면 해당 흐름 상세 현황 표시)
# ----------------------------
flow_types = ["입고", "출고", "촬영", "등록", "판매개시"]
flow_counts = filtered_df["verdict"].value_counts()

if "selected_flow" not in st.session_state:
    st.session_state.selected_flow = flow_types[0]

card_cols = st.columns(len(flow_types) + 1)
for i, flow in enumerate(flow_types):
    count = int(flow_counts.get(flow, 0))
    delta_val = deltas.get(flow, 0) if deltas else None
    delta_str = f"▲{delta_val}" if (delta_val is not None and delta_val > 0) else (str(delta_val) if delta_val is not None else "")
    with card_cols[i]:
        btn_label = f"{flow}\n{count}/{total_n}"
        if delta_str:
            btn_label += f"  {delta_str}"
        if st.button(btn_label, key=f"flow_btn_{flow}", use_container_width=True):
            st.session_state.selected_flow = flow
        if st.session_state.selected_flow == flow:
            st.caption("✓ 선택됨")

with card_cols[-1]:
    view_mode = st.radio(
        "보기 단위",
        ["스타일", "단품"],
        horizontal=True,
        label_visibility="collapsed",
        key="view_mode",
    )

selected_flow = st.session_state.selected_flow

flow_df = filtered_df[filtered_df["verdict"] == selected_flow].copy()

# 스타일 단위: styleCode 기준 집계 (수량 합산, 촬영/등록/판매개시는 하나라도 1이면 1)
if view_mode == "스타일" and len(flow_df) > 0:
    group_cols = ["brand", "yearSeason", "styleCode"]
    agg_dict = {
        "inboundQty": "sum",
        "outboundQty": "sum",
        "stockQty": "sum",
        "salesQty": "sum",
        "isShot": "max",
        "isRegistered": "max",
        "isOnSale": "max",
    }
    if "productName" in flow_df.columns:
        agg_dict["productName"] = "first"
    if "colorName" in flow_df.columns:
        agg_dict["colorName"] = lambda s: " / ".join(s.dropna().astype(str).unique()[:5])
    flow_df = flow_df.groupby(group_cols, dropna=False).agg(agg_dict).reset_index()

flow_df["verdict"] = selected_flow

# 표시용 컬럼: 촬영 O/X, 등록 O/X, 판매 상태
flow_df["_촬영"] = flow_df["isShot"].map(lambda x: "O" if x == 1 else "X")
flow_df["_등록"] = flow_df["isRegistered"].map(lambda x: "O" if x == 1 else "X")
flow_df["_판매"] = flow_df.apply(
    lambda r: "판매개시" if r["isOnSale"] == 1 else ("출고전" if r["outboundQty"] == 0 else "출고"),
    axis=1,
)

# ----------------------------
# 상세 테이블 (NO, 스타일코드, 상품명, 컬러, 입고/출고/재고/판매량, 촬영, 등록, 판매)
# ----------------------------
st.subheader(f"상세 현황 · {selected_flow}")

display_df = flow_df.copy()
display_df.insert(0, "NO", range(1, len(display_df) + 1))
show_cols = ["NO", "styleCode", "productName", "colorName", "inboundQty", "outboundQty", "stockQty", "salesQty", "_촬영", "_등록", "_판매"]
show_cols = [c for c in show_cols if c in display_df.columns]
display_df = display_df[show_cols]
display_df = display_df.rename(columns={
    "styleCode": "스타일코드",
    "productName": "상품명",
    "colorName": "컬러",
    "inboundQty": "입고량",
    "outboundQty": "출고량",
    "stockQty": "재고량",
    "salesQty": "판매량",
    "_촬영": "촬영",
    "_등록": "등록",
    "_판매": "판매",
})

st.dataframe(display_df, use_container_width=True, hide_index=True)

def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="상세현황")
    return output.getvalue()

excel_data = to_excel(display_df)
st.download_button(
    label="Download",
    data=excel_data,
    file_name=f"상세현황_{selected_flow}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)
