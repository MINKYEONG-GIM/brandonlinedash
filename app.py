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
    # 스프레드시트/워크시트를 "생성"까지 하려면 readonly 권한으로는 불가능합니다.
    # 읽기만 해도 아래 scope는 동작하며, 생성/추가 시트 등도 지원합니다.
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(
        credentials_dict, scopes=scope
    )
    return gspread.authorize(creds)


def _normalize_spreadsheet_id(spreadsheet_id_or_url):
    """스프레드시트 ID 또는 URL을 받아 ID로 정규화."""
    import re

    if spreadsheet_id_or_url is None:
        return ""
    s = str(spreadsheet_id_or_url).strip()
    if not s:
        return ""

    # URL: https://docs.google.com/spreadsheets/d/<ID>/edit...
    m = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", s)
    if m:
        return m.group(1)

    # 공유 링크에 key= 로 들어오는 케이스
    m = re.search(r"(?:^|[?&])key=([a-zA-Z0-9-_]+)", s)
    if m:
        return m.group(1)

    return s


def open_or_create_spreadsheet(client, spreadsheet_id=None, spreadsheet_title=None, create_if_missing=False):
    """ID가 있으면 open_by_key, 없으면 title로 open(옵션으로 create)."""
    import gspread

    sid = _normalize_spreadsheet_id(spreadsheet_id)
    if sid:
        return client.open_by_key(sid)

    title = (spreadsheet_title or "").strip() if spreadsheet_title else ""
    if not title:
        raise ValueError("스프레드시트 ID/URL 또는 제목(spreadsheet_title)이 필요합니다.")

    try:
        return client.open(title)
    except gspread.exceptions.SpreadsheetNotFound:
        if not create_if_missing:
            raise
        return client.create(title)


def load_sheet_as_dataframe(
    client,
    spreadsheet_id=None,
    sheet_name=None,
    header_row=0,
    spreadsheet_title=None,
    create_spreadsheet_if_missing=False,
    create_worksheet_if_missing=False,
):
    """header_row: 0 = 첫 번째 행이 헤더(기본), 1 = 두 번째 행이 헤더 등"""
    try:
        spreadsheet = open_or_create_spreadsheet(
            client,
            spreadsheet_id=spreadsheet_id,
            spreadsheet_title=spreadsheet_title,
            create_if_missing=create_spreadsheet_if_missing,
        )

        # 워크시트는 반드시 "스프레드시트를 연 뒤"에 가져옵니다.
        if sheet_name and str(sheet_name).strip():
            try:
                worksheet = spreadsheet.worksheet(str(sheet_name).strip())
            except Exception as e:
                # 없는 워크시트를 요청한 경우(옵션) 생성
                if create_worksheet_if_missing:
                    worksheet = spreadsheet.add_worksheet(title=str(sheet_name).strip(), rows=1000, cols=26)
                else:
                    raise e
        else:
            worksheet = spreadsheet.sheet1

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
# 포토촬영일 기준 촬영 스타일 수 (2025-01-01 ~ 2029-12-31)
# ----------------------------
def _find_photo_date_column(df):
    """포토촬영일 컬럼 후보: 이름에 포토촬영/촬영일 포함"""
    for c in df.columns:
        s = str(c).strip()
        if "포토촬영" in s or "촬영일" in s or s in ("photoShotDate", "shotDate"):
            return c
    return None

def _parse_date_series(ser):
    """다양한 날짜 형식 파싱 (문자열, Excel 일련번호 등)"""
    out = pd.to_datetime(ser, errors="coerce")
    # 숫자(Excel 일련번호)인데 아직 NaT인 경우
    if out.isna().any():
        numeric = pd.to_numeric(ser, errors="coerce")
        valid_num = numeric.notna() & (numeric > 10000) & (numeric < 1000000)
        if valid_num.any():
            out = out.fillna(pd.to_datetime(numeric[valid_num], unit="D", origin="1899-12-30"))
    return out

def count_styles_with_photo_date_in_range(df, start="2025-01-01", end="2029-12-31"):
    """포토촬영일이 start~end 사이인 행의 고유 styleCode 개수. 해당 컬럼 없거나 유효한 값 없으면 0."""
    date_col = _find_photo_date_column(df)
    if date_col is None:
        return 0
    ser = _parse_date_series(df[date_col])
    start_d = pd.Timestamp(start)
    end_d = pd.Timestamp(end)
    mask = ser.notna() & (ser >= start_d) & (ser <= end_d)
    return df.loc[mask, "styleCode"].nunique()

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


st.subheader("🔍 SP_SPREADSHEET_ID 확인")

sp_id = st.secrets.get("SP_SPREADSHEET_ID", None)

if sp_id is None:
    st.error("❌ SP_SPREADSHEET_ID 키 자체가 존재하지 않음")
else:
    if str(sp_id).strip() == "":
        st.error("❌ SP_SPREADSHEET_ID 값이 비어 있음")
    else:
        st.success("✅ SP_SPREADSHEET_ID 로딩 성공")
        st.write("값:", sp_id)
        st.write("길이:", len(sp_id))




st.subheader("🔍 SP 시트 첫 행 확인")

# 1. secrets에서 ID 가져오기
sp_id = st.secrets.get("SP_SPREADSHEET_ID")

if not sp_id:
    st.error("SP_SPREADSHEET_ID 값을 가져오지 못함")
else:
    st.write("SP_SPREADSHEET_ID:", sp_id)

    # 2. Google Sheets 클라이언트 생성
    creds_dict = st.secrets.get("google_service_account")
    client = get_gsheet_client(creds_dict)

    if client is None:
        st.error("Google Sheets 클라이언트 생성 실패")
    else:
        # 3. 시트 열기
        spreadsheet = client.open_by_key(sp_id)
        worksheet = spreadsheet.sheet1

        # 4. 전체 값 가져오기
        rows = worksheet.get_all_values()

        if not rows:
            st.error("시트에 데이터가 없음")
        else:
            first_row = rows[0]  # 첫 행 (헤더일 가능성 높음)

            st.success("첫 행 로딩 성공")
            st.write("첫 행 내용:")
            st.write(first_row)

