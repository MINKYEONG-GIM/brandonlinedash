import streamlit as st
import pandas as pd
from io import BytesIO
import unicodedata

# ======================================================
# 🔎 BASE vs CV 실제 스타일코드 매칭 확인
# ======================================================

import gspread
from google.oauth2.service_account import Credentials

st.markdown("## 🔎 BASE vs CV MERGE 확인")

# 1️⃣ 시트 ID 확인
base_sid = st.secrets.get("BASE_SPREADSHEET_ID")
cv_sid = st.secrets.get("CV_SPREADSHEET_ID")

st.write("BASE_SPREADSHEET_ID:", base_sid)
st.write("CV_SPREADSHEET_ID:", cv_sid)

# 2️⃣ 구글 시트 연결
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

creds = Credentials.from_service_account_info(
    st.secrets["google_service_account"], scopes=scope
)

gc = gspread.authorize(creds)

# 3️⃣ BASE 읽기
base_ws = gc.open_by_key(base_sid).sheet1
base_data = pd.DataFrame(base_ws.get_all_records())

st.write("BASE 행 개수:", len(base_data))
st.write("BASE 컬럼:", list(base_data.columns))

# 4️⃣ CV 읽기
cv_ws = gc.open_by_key(cv_sid).sheet1
cv_data = pd.DataFrame(cv_ws.get_all_records())

st.write("CV 행 개수:", len(cv_data))
st.write("CV 컬럼:", list(cv_data.columns))

# 5️⃣ 스타일코드 컬럼 자동 탐색
def find_style_col(df):
    for col in df.columns:
        if "스타일" in col or "style" in col.lower():
            return col
    return None

base_style_col = find_style_col(base_data)
cv_style_col = find_style_col(cv_data)

st.write("BASE 스타일컬럼:", base_style_col)
st.write("CV 스타일컬럼:", cv_style_col)

if base_style_col and cv_style_col:

    base_styles = (
        base_data[base_style_col]
        .astype(str)
        .str.strip()
        .unique()
    )

    cv_styles = (
        cv_data[cv_style_col]
        .astype(str)
        .str.strip()
        .unique()
    )

    intersection = set(base_styles) & set(cv_styles)

    st.markdown("### 📌 매칭 결과")
    st.write("BASE 스타일 개수:", len(base_styles))
    st.write("CV 스타일 개수:", len(cv_styles))
    st.write("교집합 개수:", len(intersection))

    if len(intersection) > 0:
        st.write("교집합 샘플:")
        st.write(list(intersection)[:10])
    else:
        st.error("❌ 스타일코드 매칭 0개 → merge 불가능 상태")

else:
    st.error("❌ 스타일코드 컬럼을 찾지 못함")

st.markdown("## 🔎 BASE vs CV 실제 매칭 확인")

import gspread
from google.oauth2.service_account import Credentials

scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

creds = Credentials.from_service_account_info(
    st.secrets["google_service_account"], scopes=scope
)

gc = gspread.authorize(creds)

base_sid = st.secrets["BASE_SPREADSHEET_ID"]
cv_sid = st.secrets["CV_SPREADSHEET_ID"]

base_df = pd.DataFrame(gc.open_by_key(base_sid).sheet1.get_all_records())
cv_df = pd.DataFrame(gc.open_by_key(cv_sid).sheet1.get_all_records())

st.write("BASE 행 개수:", len(base_df))
st.write("CV 행 개수:", len(cv_df))

base_styles = base_df.iloc[:,0].astype(str).str.strip().unique()
cv_styles = cv_df.iloc[:,0].astype(str).str.strip().unique()

intersection = set(base_styles) & set(cv_styles)

st.write("교집합 개수:", len(intersection))
st.write("교집합 샘플:", list(intersection)[:10])

