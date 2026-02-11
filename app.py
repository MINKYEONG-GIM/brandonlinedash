import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

# 1️⃣ Secrets에서 credentials 읽기
creds_dict = st.secrets.get("google_service_account")

# 2️⃣ gs_client 먼저 None으로 초기화
gs_client = None

if creds_dict:
    try:
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]

        credentials = Credentials.from_service_account_info(
            creds_dict,
            scopes=scopes
        )

        gs_client = gspread.authorize(credentials)
        st.success("✅ Google Sheets 연결 성공")

    except Exception as e:
        st.error(f"❌ 인증 실패: {e}")

else:
    st.error("❌ google_service_account secrets 없음")

# 3️⃣ 여기서부터 사용
if gs_client is not None:
    try:
        PHOTO_SPREADSHEET_ID = "여기에_SPREADSHEET_ID"

        spreadsheet = gs_client.open_by_key(PHOTO_SPREADSHEET_ID)
        worksheet = spreadsheet.worksheet("SP")  # 시트 이름 정확히 입력

        data = worksheet.get_all_values()

        st.write("🔍 SP 시트 로딩 확인")
        st.write("행 개수:", len(data))
        st.write("상위 5행:")
        st.write(data[:5])

    except Exception as e:
        st.error(f"❌ 시트 로딩 실패: {e}")
