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
    try:
        spreadsheet = client.open_by_key(spreadsheet_id)
        worksheet = (
            spreadsheet.worksheet(sheet_name)
            if sheet_name
            else spreadsheet.get_worksheet(0)
        )

        rows = worksheet.get_all_values()
        if not rows or len(rows) <= header_row:
            return pd.DataFrame()

        headers = [str(h).strip() for h in rows[header_row]]
        data_rows = rows[header_row + 1 :]

        return pd.DataFrame(data_rows, columns=headers)

    except Exception as e:
        st.error(f"시트 읽기 오류: {e}")
        return None


# ----------------------------
# 브랜드 매핑
# ----------------------------
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
    if pd.isna(style_code) or not str(style_code).strip():
        return ""
    code = str(style_code).strip()[:2].lower()
    return BRAND_CODE_MAP.get(code, code.upper())


# ----------------------------
# 상태 판정
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
# 제목
# ----------------------------
st.title("브랜드 상품 흐름 대시보드")
st.caption("입고 · 출고 · 촬영 · 등록 · 판매개시 현황")

# ----------------------------
# Secrets → 시트 ID 수집
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


# ----------------------------
# Google 인증
# ----------------------------
creds_dict = None
try:
    if "gcp_service_account" in st.secrets:
        creds_dict = dict(st.secrets["gcp_service_account"])
    elif "google_service_account" in st.secrets:
        creds_dict = dict(st.secrets["google_service_account"])
except Exception:
    pass

gs_client = get_gsheet_client(creds_dict) if creds_dict else None

if not gs_client:
    st.error("Google 인증 정보가 Secrets에 없습니다.")
    st.stop()

spreadsheet_ids = get_spreadsheet_ids_from_secrets()

if not spreadsheet_ids:
    st.error("Secrets에 스프레드시트 ID가 없습니다.")
    st.stop()

# ----------------------------
# 🔥 시트 선택 UI (핵심 추가 부분)
# ----------------------------
selected_label = st.selectbox(
    "데이터 시트 선택",
    list(spreadsheet_ids.keys()),
)

spreadsheet_id = spreadsheet_ids[selected_label]

# ----------------------------
# 데이터 로드
# ----------------------------
items_df = load_sheet_as_dataframe(
    gs_client,
    spreadsheet_id,
    sheet_name=None,
    header_row=0,
)

if items_df is None or len(items_df) == 0:
    st.warning("시트에 데이터가 없습니다.")
    st.stop()

# ----------------------------
# 기본 전처리
# ----------------------------
items_df.columns = [str(c).strip() for c in items_df.columns]

if "styleCode" in items_df.columns:
    items_df["brand"] = items_df["styleCode"].apply(brand_from_style_code)

numeric_cols = [
    "inboundQty",
    "outboundQty",
    "stockQty",
    "salesQty",
    "isShot",
    "isRegistered",
    "isOnSale",
]

for col in numeric_cols:
    if col in items_df.columns:
        items_df[col] = (
            pd.to_numeric(items_df[col], errors="coerce")
            .fillna(0)
            .astype(int)
        )

items_df["verdict"] = items_df.apply(
    lambda r: get_verdict(
        r.get("inboundQty", 0),
        r.get("outboundQty", 0),
        r.get("isShot", 0),
        r.get("isRegistered", 0),
        r.get("isOnSale", 0),
    ),
    axis=1,
)

# ----------------------------
# 브랜드 필터
# ----------------------------
brands = sorted(items_df["brand"].unique())
brand = st.selectbox("브랜드", brands)

filtered_df = items_df[items_df["brand"] == brand].copy()

if len(filtered_df) == 0:
    st.info("해당 브랜드 데이터가 없습니다.")
    st.stop()

# ----------------------------
# 상세 테이블
# ----------------------------
st.subheader("상세 현황")

display_df = filtered_df.copy()
display_df.insert(0, "NO", range(1, len(display_df) + 1))

st.dataframe(display_df, use_container_width=True, hide_index=True)

# ----------------------------
# 엑셀 다운로드
# ----------------------------
def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="상세현황")
    return output.getvalue()

excel_data = to_excel(display_df)

st.download_button(
    label="Download",
    data=excel_data,
    file_name=f"{selected_label}_상세현황.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)
