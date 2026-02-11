import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

SPREADSHEET_ID = st.secrets.get("SP_SPREADSHEET_ID")

creds_dict = st.secrets["google_service_account"]

creds = Credentials.from_service_account_info(
    creds_dict,
    scopes=["https://www.googleapis.com/auth/spreadsheets"]
)

client = gspread.authorize(creds)

try:
    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    st.success("시트 열기 성공")
    st.write("시트 제목:", spreadsheet.title)
except Exception as e:
    st.error(f"시트 열기 실패: {e}")
