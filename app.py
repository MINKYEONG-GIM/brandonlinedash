import streamlit as st
import pandas as pd

st.set_page_config(page_title="브랜드 상품 흐름 대시보드", layout="wide")

gs_client = get_gsheet_client(creds_dict) if creds_dict else None

# 🔽 여기 아래에 넣어야 함
st.subheader("🔍 SP 시트 로딩 확인")

PHOTO_SPREADSHEET_ID = st.secrets.get("SP_SPREADSHEET_ID", "")
st.write("SP_SPREADSHEET_ID 값:", PHOTO_SPREADSHEET_ID)

if PHOTO_SPREADSHEET_ID and gs_client:
    photo_df = load_sheet_as_dataframe(
        gs_client,
        PHOTO_SPREADSHEET_ID,
        sheet_name=None,
        header_row=0
    )

    st.write("행 개수:", len(photo_df) if photo_df is not None else "None")
    if photo_df is not None:
        st.write("컬럼 목록:", photo_df.columns.tolist())
        st.dataframe(photo_df.head())
