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
# 촬영 완료 판정: 리터칭완료일 등 날짜 컬럼
# ----------------------------
# 규칙: 머릿글 "리터칭완료일" 열에 "2026-01-20" 같은 날짜 값이 들어 있으면 그 행은 촬영 O로 표시.

def _normalize_col_name(name):
    """컬럼명 비교용: 앞뒤 공백·제어문자 제거, 공백 통일."""
    if name is None or not isinstance(name, str):
        return ""
    s = str(name).strip()
    s = "".join(c for c in s if ord(c) >= 32 or c in "\t\n\r")  # 제어문자 제거
    return s.replace(" ", "").replace("\u3000", "")

def _find_photo_date_column(df, preferred_name=None):
    """촬영 완료를 판정할 날짜 컬럼. 리터칭완료일 우선, 없으면 촬영일자/포토촬영일 등."""
    # 0순위: Secrets에 지정된 컬럼명이 있으면 정확히 그 컬럼 사용
    if preferred_name and str(preferred_name).strip():
        name = str(preferred_name).strip()
        for c in df.columns:
            if str(c).strip() == name:
                return c
        name_norm = _normalize_col_name(name)
        for c in df.columns:
            if _normalize_col_name(c) == name_norm:
                return c
    # 1순위: 머릿글 "리터칭완료일" 정확히 (공백/제어문자만 정규화)
    for c in df.columns:
        if _normalize_col_name(c) == "리터칭완료일":
            return c
    # 2순위: 리터칭 관련 (리터칭완료일, 리터칭일, 리터칭 일자 등)
    for c in df.columns:
        s = str(c).strip()
        s_nospace = _normalize_col_name(c)
        if "리터칭" in s_nospace or "retouch" in s.lower():
            return c
    # 3순위: 촬영일자, 포토촬영일, 보정완료일 등
    for c in df.columns:
        s = str(c).strip()
        s_nospace = _normalize_col_name(c)
        s_lower = s.lower()
        if (
            "포토촬영" in s_nospace
            or "촬영일" in s_nospace
            or "촬영일자" in s_nospace
            or "보정완료" in s_nospace
            or s in ("photoShotDate", "shotDate", "retouchDoneDate", "retouch_date", "촬영일자", "촬영 일자")
        ):
            return c
    # 4순위: 'OO완료일' 형태 중 등록/판매 제외
    for c in df.columns:
        s_nospace = _normalize_col_name(c)
        if "완료일" in s_nospace and "등록" not in s_nospace and "판매" not in s_nospace:
            return c
    return None

def _parse_date_series(ser):
    """다양한 날짜 형식 파싱 (문자열, Excel/구글 시트 일련번호 등). 공백/형식 차이 관대하게 처리."""
    out = pd.to_datetime(ser, errors="coerce")
    # 파싱 실패한 셀: 앞뒤 공백 제거 후 재시도
    still_na = out.isna()
    if still_na.any():
        try:
            cleaned = ser.astype(str).str.strip()
            out2 = pd.to_datetime(cleaned, errors="coerce")
            out = out.fillna(out2)
        except Exception:
            pass
    # "2025. 1. 15"처럼 점 앞뒤 공백 제거 후 재시도
    still_na = out.isna()
    if still_na.any():
        try:
            s = ser.astype(str).str.strip()
            s = s.str.replace(r"\s*\.\s*", ".", regex=True).str.replace(r"\s*-\s*", "-", regex=True)
            out3 = pd.to_datetime(s, errors="coerce")
            out = out.fillna(out3)
        except Exception:
            pass
    # 구글 시트/엑셀 날짜 일련번호(문자열 "45324" 등)
    if out.isna().any():
        numeric = pd.to_numeric(ser, errors="coerce")
        valid_num = numeric.notna() & (numeric > 10000) & (numeric < 1000000)
        if valid_num.any():
            fixed = pd.to_datetime(numeric[valid_num], unit="D", origin="1899-12-30")
            out = out.fillna(fixed)
    return out

def _looks_like_date_value(val):
    """셀 값이 날짜처럼 보이면 True (파싱 실패해도 '값 있음'으로 촬영 완료 처리용)."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return False
    s = str(val).strip()
    if not s or s in ("-", ".", "미정", "n/a", "N/A", "—"):
        return False
    # 숫자 4자리 이상 + 구분자(-./) 있으면 날짜로 간주
    if any(sep in s for sep in ("-", ".", "/")) and any(c.isdigit() for c in s):
        return True
    # 숫자만 있는 경우(엑셀 시리얼)
    if s.isdigit() and 10000 <= int(s) <= 1000000:
        return True
    return False


def compute_shot_done_series(df, preferred_date_column=None):
    """촬영 완료 여부(0/1) 시리즈를 생성.

    리터칭완료일에 값(날짜)이 있으면 그 행은 촬영 완료(O).
    리터칭완료일 컬럼이 없으면 촬영일자/포토촬영일 등 다른 날짜 컬럼, 없으면 isShot(0/1) 폴백.
    """
    date_col = _find_photo_date_column(df, preferred_name=preferred_date_column)
    if date_col is not None and date_col in df.columns:
        ser = _parse_date_series(df[date_col])
        done = ser.notna().astype(int)
        # 파싱은 실패했지만 값이 날짜 형태인 경우(공백/형식 이슈) O 처리
        if (done == 0).any():
            raw = df[date_col].astype(str).str.strip()
            fallback = raw.apply(_looks_like_date_value).astype(int)
            done = done.where(done == 1, fallback)
        return done

    if "isShot" in df.columns:
        return (pd.to_numeric(df["isShot"], errors="coerce").fillna(0).astype(int) == 1).astype(int)

    return pd.Series([0] * len(df), index=df.index, dtype="int64")

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
spreadsheet_title = None
create_spreadsheet_if_missing = False

if not spreadsheet_ids:
    # ID가 없으면(옵션) 제목으로 열기/생성할 수 있게 지원
    # - AUTO_CREATE_SPREADSHEET=true 이고
    # - SPREADSHEET_TITLE(또는 BASE_SPREADSHEET_TITLE)가 있으면
    # 스프레드시트를 생성/오픈 후 계속 진행합니다.
    auto_create = str(st.secrets.get("AUTO_CREATE_SPREADSHEET", "")).strip().lower() in ("1", "true", "yes", "y")
    spreadsheet_title = str(st.secrets.get("SPREADSHEET_TITLE", "")).strip() or str(st.secrets.get("BASE_SPREADSHEET_TITLE", "")).strip()
    if auto_create and spreadsheet_title:
        selected_label = "AUTO"
        spreadsheet_id = None
        create_spreadsheet_if_missing = True
    else:
        st.error("Secrets에 스프레드시트 ID가 없습니다. BASE_SPREADSHEET_ID 등을 설정하거나, AUTO_CREATE_SPREADSHEET=true 와 SPREADSHEET_TITLE을 설정하세요.")
        st.stop()
else:
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
    spreadsheet_title=spreadsheet_title,
    create_spreadsheet_if_missing=create_spreadsheet_if_missing,
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

# ----------------------------
# 촬영 완료 여부 계산 (__shot_done)
# - 리터칭완료일 등 날짜가 있으면 O로 표시
# ----------------------------
# Secrets에 촬영 날짜 컬럼명 지정 가능 (시트 컬럼명이 다를 때)
preferred_shot_date_col = (st.secrets.get("SHOT_DATE_COLUMN") or "").strip() or None
items_df["__shot_done"] = compute_shot_done_series(items_df, preferred_date_column=preferred_shot_date_col)
shot_date_column = _find_photo_date_column(items_df, preferred_name=preferred_shot_date_col)  # 화면에서 원인 확인용

# ----------------------------
# verdict 생성
# ----------------------------
items_df["verdict"] = items_df.apply(
    lambda r: get_verdict(
        r["inboundQty"],
        r["outboundQty"],
        r["__shot_done"],
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

# 발주 스타일 수(고유 styleCode), 입고/출고 등은 스타일 수로 집계
total_n = filtered_df["styleCode"].nunique()
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
# 흐름 집계 카드 (스타일 수 기준: 해당 단계 1건이라도 있으면 스타일 포함)
# ----------------------------
flow_types = ["입고", "출고", "촬영", "등록", "판매개시"]
# 흐름별 조건: 해당 조건을 만족하는 행이 하나라도 있는 스타일 수
_flow_conditions = {
    "입고": (filtered_df["inboundQty"] > 0),
    "출고": (filtered_df["outboundQty"] > 0),
    "촬영": (filtered_df["__shot_done"] == 1),
    "등록": (filtered_df["isRegistered"] == 1),
    "판매개시": (filtered_df["isOnSale"] == 1),
}
flow_counts = pd.Series({
    flow: filtered_df.loc[cond]["styleCode"].nunique()
    for flow, cond in _flow_conditions.items()
})

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

flow_df = filtered_df.loc[_flow_conditions[selected_flow]].copy()

# 스타일 단위: styleCode 기준 집계 (수량 합산, 촬영/등록/판매개시는 하나라도 1이면 1)
if view_mode == "스타일" and len(flow_df) > 0:
    group_cols = ["brand", "yearSeason", "styleCode"]
    agg_dict = {
        "inboundQty": "sum",
        "outboundQty": "sum",
        "stockQty": "sum",
        "salesQty": "sum",
        "isShot": "max",
        "__shot_done": "max",
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
flow_df["_촬영"] = flow_df["__shot_done"].map(lambda x: "O" if int(x) == 1 else "X")
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

# ----------------------------
# 촬영 O/X 원인 확인 (디버그)
# ----------------------------
with st.expander("🔍 촬영 열이 X로 나오는 이유 확인"):
    st.caption("특정 스타일코드가 촬영 O가 아니라 X로 나올 때, 어떤 컬럼·값으로 판정했는지 확인합니다.")
    debug_style = st.text_input("스타일코드", value="SPABGA9A51", key="debug_style")
    if shot_date_column:
        st.write(f"**촬영 판정에 사용 중인 컬럼:** `{shot_date_column}` (여기에 유효한 날짜가 있으면 O)")
    else:
        st.write("**촬영 판정에 사용 중인 컬럼:** 없음 → `isShot`(촬영여부) 값으로 판정 중.")
        st.caption("시트에서 읽은 컬럼 이름 중에 촬영/리터칭 날짜 컬럼이 있어야 O로 표시됩니다. 아래 목록에서 해당 컬럼 이름을 확인한 뒤, Streamlit Secrets에 **SHOT_DATE_COLUMN** = 그 이름(따옴표 포함)으로 넣으면 해당 컬럼으로 촬영 O/X를 판정합니다.")
        all_cols = list(items_df.columns)
        # 촬영/날짜와 연관될 수 있는 이름만 강조해서 보여주기
        date_like = [c for c in all_cols if any(k in str(c) for k in ("촬영", "리터칭", "보정", "완료", "일자", "날짜", "date", "shot", "retouch"))]
        if date_like:
            st.write("연관 컬럼 후보:", ", ".join(f"`{c}`" for c in date_like))
        st.write("전체 컬럼:", ", ".join(f"`{c}`" for c in all_cols[:30]) + (" …" if len(all_cols) > 30 else ""))
    if debug_style and "styleCode" in items_df.columns:
        rows = items_df[items_df["styleCode"].astype(str).str.strip() == str(debug_style).strip()]
        if len(rows) == 0:
            st.warning(f"스타일코드 '{debug_style}'에 해당하는 행이 없습니다. (필터 조건이나 시트 데이터 확인)")
        else:
            cols_show = ["styleCode", "__shot_done"]
            if shot_date_column and shot_date_column in items_df.columns:
                cols_show.insert(1, shot_date_column)
            cols_show = [c for c in cols_show if c in rows.columns]
            debug_df = rows[cols_show].copy()
            debug_df["촬영 표시"] = debug_df["__shot_done"].map(lambda x: "O" if int(x) == 1 else "X")
            st.dataframe(debug_df, use_container_width=True, hide_index=True)
            st.caption("위 표에서 **촬영 표시가 X**인 이유: 해당 행의 날짜 컬럼 값이 비어 있거나, 날짜로 인식되지 않았거나, '날짜처럼 보이는 값' 조건에 맞지 않음.")
