import streamlit as st
import pandas as pd
from io import BytesIO
import unicodedata



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
        items_df[items_df["brand"] == "클라비스"]
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
        items_df[items_df["brand"] == "클라비스"]
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
