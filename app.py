# ================================
# 🔎 CV_SPREADSHEET_ID + MERGE 디버그
# ================================

st.markdown("## 🔎 CV 디버그 시작")

# 1️⃣ CV_SPREADSHEET_ID 확인
cv_sid = st.secrets.get("CV_SPREADSHEET_ID")
st.write("CV_SPREADSHEET_ID:", cv_sid)

if not cv_sid:
    st.error("❌ CV_SPREADSHEET_ID가 secrets에 없습니다.")
else:
    st.success("✅ CV_SPREADSHEET_ID 정상 로딩")

# shot_reg_df / items_df 존재 여부 먼저 확인
if "shot_reg_df" not in locals():
    st.error("❌ shot_reg_df가 아직 생성되지 않았습니다. (이 코드는 merge 이후에 넣어야 함)")
elif "items_df" not in locals():
    st.error("❌ items_df가 아직 생성되지 않았습니다. (이 코드는 merge 이후에 넣어야 함)")
else:

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
