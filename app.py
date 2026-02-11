import streamlit as st
import pandas as pd

# Google Sheets 클라이언트 생성 이후에만 실행

if gs_client is None:
    st.error("❌ gs_client 생성 실패 (Secrets 또는 서비스계정 확인)")
else:
    st.subheader("🔍 SP 시트 로딩 확인")

    PHOTO_SPREADSHEET_ID = st.secrets.get("SP_SPREADSHEET_ID", "")
    st.write("SP_SPREADSHEET_ID 값:", PHOTO_SPREADSHEET_ID)

    if not PHOTO_SPREADSHEET_ID:
        st.error("❌ SP_SPREADSHEET_ID가 비어있음")
    else:
        photo_df = load_sheet_as_dataframe(
            gs_client,
            PHOTO_SPREADSHEET_ID,
            sheet_name=None,
            header_row=0
        )

        if photo_df is None:
            st.error("❌ 시트 로딩 실패 (권한 문제 가능)")
        elif len(photo_df) == 0:
            st.warning("⚠️ 시트는 열렸지만 데이터 없음 (header_row 확인)")
        else:
            st.success(f"✅ 시트 로딩 성공 (행 개수: {len(photo_df)})")
            st.write("컬럼 목록:", photo_df.columns.tolist())
            st.dataframe(photo_df.head())
