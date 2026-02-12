import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# ----------------------------
# 1️⃣ Google 인증
# ----------------------------
credentials = Credentials.from_service_account_info(
    st.secrets["google_service_account"],
    scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
)

gc = gspread.authorize(credentials)

BASE_SPREADSHEET_ID = "1CMYhX0SDGfhBs-jMv4OcRC3qrHDRL-7LtCt8McDkrns"
CV_SPREADSHEET_ID = "1lY7UAyUcAR7petLecdNMTC9kgWoi7a9lbqSwp2eiB5k"

# ----------------------------
# 2️⃣ 시트 열기 (첫 번째 워크시트 사용)
# ----------------------------
base_sheet = gc.open_by_key(BASE_SPREADSHEET_ID).sheet1
cv_sheet = gc.open_by_key(CV_SPREADSHEET_ID).sheet1

# ----------------------------
# 3️⃣ DataFrame 생성
# ----------------------------
base_df = pd.DataFrame(base_sheet.get_all_records())
cv_df = pd.DataFrame(cv_sheet.get_all_records())

# ----------------------------
# 4️⃣ 컬럼 확인
# ----------------------------
st.write("=== BASE 컬럼 목록 ===")
st.write(base_df.columns.tolist())

st.write("=== CV 컬럼 목록 ===")
st.write(cv_df.columns.tolist())

# strip 처리
base_df.columns = base_df.columns.astype(str).str.strip()
cv_df.columns = cv_df.columns.astype(str).str.strip()

st.write("=== strip 후 BASE 컬럼 ===")
st.write(base_df.columns.tolist())

st.write("=== strip 후 CV 컬럼 ===")
st.write(cv_df.columns.tolist())

# 정확 존재 여부
st.write("BASE에 '스타일코드(Now)' 존재:",
         "스타일코드(Now)" in base_df.columns)

st.write("CV에 '스타일코드' 존재:",
         "스타일코드" in cv_df.columns)
