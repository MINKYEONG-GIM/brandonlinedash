st.subheader("🔍 SP 시트 로딩 확인")

PHOTO_SPREADSHEET_ID = st.secrets.get("SP_SPREADSHEET_ID", "")

st.write("SP_SPREADSHEET_ID 값:", PHOTO_SPREADSHEET_ID)
