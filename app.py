import streamlit as st
import pandas as pd
from io import BytesIO
import unicodedata



st.set_page_config(page_title="브랜드 상품 흐름 대시보드", layout="wide")

# ----------------------------
# Google Sheets 연동
# ----------------------------
def get_gsheet_client(credentials_dict):
    if credentials_dict is None:
        return None
    import gspread
    from google.oauth2.service_account import Credentials
    # 스프레드시트/워크시트를 "생성"까지 하려면 readonly 권한으로는 불가능합니다.
    # 읽기만 해도 아래 scope는 동작하며, 생성/추가 시트 등도 지원합니다.
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(
        credentials_dict, scopes=scope
    )
    return gspread.authorize(creds)

# ================================
# 🔎 CV_SPREADSHEET_ID + MERGE 디버그
# ================================

st.markdown("## 🔎 CV 디버그 시작")

# 1️⃣ CV_SPREADSHEET_ID 확인
cv_sid = secrets.get("CV_SPREADSHEET_ID")
st.write("CV_SPREADSHEET_ID:", cv_sid)

if not cv_sid:
    st.error("❌ CV_SPREADSHEET_ID가 secrets에 없습니다.")
else:
    st.success("✅ CV_SPREADSHEET_ID 정상 로딩")

# 2️⃣ shot_reg_df 안에 클라비스 데이터 존재 여부
st.markdown("### 2️⃣ shot_reg_df 내 클라비스 데이터 확인")

if "brand" in shot_reg_df.columns:
    cv_shot_df = shot_reg_df[shot_reg_df["brand"] == "클라비스"]
    st.write("shot_reg_df 내 클라비스 행 개수:", len(cv_shot_df))
    st.write("shot_reg_df 클라비스 샘플:", cv_shot_df.head())
else:
    st.error("❌ shot_reg_df에 brand 컬럼이 없습니다.")

# 3️⃣ BASE ↔ CV merge 매칭 확인
st.markdown("### 3️⃣ BASE ↔ CV merge 확인")

if "_styleCode" in shot_reg_df.columns and "_styleCode" in items_df.columns:

    cv_styles = shot_reg_df[
        shot_reg_df["brand"] == "클라비스"
    ]["_styleCode"].unique()

    base_cv = items_df[
        items_df["_styleCode"].isin(cv_styles)
    ]

    st.write("CV 스타일코드 개수:", len(cv_styles))
    st.write("BASE에서 매칭된 CV 스타일 개수:", len(base_cv))

    if len(base_cv) > 0:
        st.write("매칭 샘플:")
        st.write(base_cv[["_styleCode", "brand", "__shot_done"]].head())
    else:
        st.warning("⚠ BASE와 CV 스타일코드가 매칭되지 않음")

else:
    st.error("❌ _styleCode 컬럼이 존재하지 않음")

st.markdown("## 🔎 CV 디버그 종료")

