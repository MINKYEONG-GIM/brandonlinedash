import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import re

st.set_page_config(page_title="브랜드 상품 흐름 대시보드", layout="wide")

# ----------------------------
# Google Sheets 연동
# ----------------------------
def get_gsheet_client(credentials_dict):
    if credentials_dict is None:
        return None
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
    if spreadsheet_id_or_url is None:
        return ""
    s = str(spreadsheet_id_or_url).strip()
    if not s:
        return ""
    m = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", s)
    if m:
        return m.group(1)
    m = re.search(r"(?:^|[?&])key=([a-zA-Z0-9-_]+)", s)
    if m:
        return m.group(1)
    return s

def open_or_create_spreadsheet(client, spreadsheet_id=None, spreadsheet_title=None, create_if_missing=False):
    """ID가 있으면 open_by_key, 없으면 title로 open(옵션으로 create)."""
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

# ----------------------------
# 데이터 불러오기
# ----------------------------
# Streamlit Secrets에 Google Service Account JSON을 넣어두고 불러오는 예시
# st.secrets["google_service_account"] 형태로 사용
gs_client = get_gsheet_client(st.secrets.get("google_service_account"))

# Clavis 리터칭 데이터 시트
CLAVIS_SHEET_URL = "https://docs.google.com/spreadsheets/d/1your_clavis_id_here/edit"
cv_ws = open_or_create_spreadsheet(gs_client, spreadsheet_id=CLAVIS_SHEET_URL).sheet1
cv_data = cv_ws.get_all_records()
cv_df = pd.DataFrame(cv_data)

# 웹에서 사용 중인 스타일 시트
WEB_SHEET_URL = "https://docs.google.com/spreadsheets/d/1your_items_id_here/edit"
web_ws = open_or_create_spreadsheet(gs_client, spreadsheet_id=WEB_SHEET_URL).sheet1
web_data = web_ws.get_all_records()
items_df = pd.DataFrame(web_data)

# ----------------------------
# 1개 누락 추적
# ----------------------------
with st.expander("🔎 1개 누락 추적"):

    df = cv_df.copy()

    df.columns = (
        df.columns.astype(str)
        .str.replace("\n", "", regex=False)
        .str.replace(" ", "", regex=False)
        .str.strip()
    )

    # 리터칭 있는 스타일
    retouch_styles = (
        df[df["리터칭완료일"].astype(str).str.strip() != ""]
        ["스타일코드"]
        .astype(str)
        .str.strip()
        .unique()
    )

    st.write("리터칭 스타일 총:", len(retouch_styles))

    # 웹에서 사용 중인 스타일
    web_styles = (
        items_df[items_df["brand"].astype(str).str.strip() == "클라비스"]
        ["styleCode"]
        .astype(str)
        .str.strip()
        .unique()
    )

    st.write("웹 스타일 총:", len(web_styles))

    # 차집합 확인
    missing = set(retouch_styles) - set(web_styles)

    st.write("웹에서 빠진 스타일:", missing)
    st.write("빠진 개수:", len(missing))
