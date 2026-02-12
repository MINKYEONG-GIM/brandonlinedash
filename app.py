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

# 1️⃣ 컬럼명 원본 출력
st.write("=== BASE 원본 컬럼 목록 ===")
st.write(base_df.columns.tolist())

st.write("=== CV 원본 컬럼 목록 ===")
st.write(cv_df.columns.tolist())


# 2️⃣ 컬럼명 strip 처리
base_df.columns = base_df.columns.astype(str).str.strip()
cv_df.columns = cv_df.columns.astype(str).str.strip()

st.write("=== BASE strip 후 컬럼 목록 ===")
st.write(base_df.columns.tolist())

st.write("=== CV strip 후 컬럼 목록 ===")
st.write(cv_df.columns.tolist())


# 3️⃣ 정확히 존재하는지 확인
st.write("=== 정확 일치 여부 ===")

base_has = "스타일코드(Now)" in base_df.columns
cv_has = "스타일코드" in cv_df.columns

st.write("BASE에 '스타일코드(Now)' 존재 여부:", base_has)
st.write("CV에 '스타일코드' 존재 여부:", cv_has)


# 4️⃣ 유사 컬럼 찾기 (혹시 보이지 않는 문자 있을 경우 대비)
st.write("=== BASE 유사 컬럼 후보 ===")
st.write([c for c in base_df.columns if "스타일" in c])

st.write("=== CV 유사 컬럼 후보 ===")
st.write([c for c in cv_df.columns if "스타일" in c])
