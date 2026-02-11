import streamlit as st
import pandas as pd

st.set_page_config(page_title="브랜드 상품 흐름 대시보드", layout="wide")

st.subheader("🔍 SP 시트 로딩 확인")

st.subheader("🔍 SP 시트 로딩 확인")

PHOTO_SPREADSHEET_ID = st.secrets.get("SP_SPREADSHEET_ID", "")

st.write("SP_SPREADSHEET_ID 값:", PHOTO_SPREADSHEET_ID)

if not PHOTO_SPREADSHEET_ID:
    st.error("❌ SP_SPREADSHEET_ID 값이 비어있음 (Secrets 확인)")
else:
    photo_df = load_sheet_as_dataframe(
        gs_client,
        PHOTO_SPREADSHEET_ID,
        sheet_name=None,
        header_row=0  # 필요하면 1로 바꿔서 테스트
    )

    if photo_df is None:
        st.error("❌ 시트 로딩 실패 (권한 또는 ID 문제)")
    elif len(photo_df) == 0:
        st.warning("⚠️ 시트는 열렸지만 데이터가 없음 (header_row 확인)")
    else:
        st.success(f"✅ 시트 로딩 성공 (행 개수: {len(photo_df)})")

        st.write("컬럼 목록:")
        st.write(photo_df.columns.tolist())

        st.write("상위 5개 데이터:")
        st.dataframe(photo_df.head())

