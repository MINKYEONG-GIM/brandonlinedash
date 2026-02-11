import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

# 1️⃣ Secrets에서 값 가져오기
SPREADSHEET_ID = st.secrets.get("SP_SPREADSHEET_ID")
creds_dict = st.secrets["google_service_account"]

# 2️⃣ 인증 객체 생성
creds = Credentials.from_service_account_info(
    creds_dict,
    scopes=["https://www.googleapis.com/auth/spreadsheets"]
)

# 3️⃣ gspread 클라이언트 생성
client = gspread.authorize(creds)

# 4️⃣ 스프레드시트 열기
spreadsheet = client.open_by_key(SPREADSHEET_ID)

st.success("시트 열기 성공")
st.write("시트 제목:", spreadsheet.title)

# 5️⃣ 첫 번째 탭 가져오기
worksheet = spreadsheet.get_worksheet(0)

# 6️⃣ 데이터 읽기
data = worksheet.get_all_records()

df = pd.DataFrame(data)

# 7️⃣ 확인 출력
st.write("행 개수:", len(df))
st.write("컬럼 목록:", df.columns.tolist())
st.dataframe(df.head())
