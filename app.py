import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

SPREADSHEET_ID = st.secrets.get("SP_SPREADSHEET_ID")



worksheet = spreadsheet.get_worksheet(0)  # 첫 번째 탭
data = worksheet.get_all_records()

df = pd.DataFrame(data)

st.write("행 개수:", len(df))
st.write("컬럼 목록:", df.columns.tolist())
st.dataframe(df.head())
