import streamlit as st
import pandas as pd
import plotly.express as px
import urllib.parse

# -----------------------------------------------------------------------------
# 1. Streamlit 페이지 설정 및 한국투자증권 브랜드 커스텀 CSS
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="한국투자증권 | DB 가입자 명부 분석 대시보드",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 한국투자증권 브랜드 스타일 정의 (브라운 #7A4016, 블루 #0066B3, 웜화이트 #F9F8F6)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Noto Sans KR', sans-serif;
    }
    
    .header-container {
        display: flex;
        justify-content: space-between;
        align-items: center;
        background-color: #ffffff;
        padding: 18px 25px;
        border-bottom: 3px solid #7A4016;
        margin-bottom: 20px;
        border-radius: 8px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    
    .header-title {
        font-size: 1.55rem;
        font-weight: 700;
        color: #7A4016;
        margin: 0;
    }
    
    .header-subtitle {
        font-size: 0.88rem;
        color: #666666;
        margin-top: 4px;
    }
    
    .kis-logo-text {
        text-align: right;
        font-family: 'Arial', sans-serif;
    }
    
    .kis-brand-friend {
        font-size: 1.15rem;
        font-weight: 700;
        color: #7A4016;
        letter-spacing: -0.5px;
    }
    
    .kis-brand-friend span {
        color: #0066B3;
    }
    
    .kis-brand-name {
        font-size: 1.0rem;
        font-weight: 800;
        color: #111111;
        line-height: 1.1;
    }
    
    .kis-brand-sub {
        font-size: 0.72rem;
        color: #555555;
    }

    .metric-card {
        background-color: #F9F8F6;
        border: 1px solid #E5E0DA;
        border-top: 4px solid #7A4016;
        padding: 14px 16px;
        border-radius: 6px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.03);
    }
    
    .kpi-title {
        font-size: 0.85rem;
        color: #555555;
        font-weight: 600;
        margin-bottom: 4px;
    }
    
    .kpi-value {
        font-size: 1.45rem;
        color: #7A4016;
        font-weight: 700;
    }
    
    .kpi-sub {
        font-size: 0.80rem;
        color: #777777;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. GitHub 저장소 및 파일 경로 설정
# -----------------------------------------------------------------------------
GITHUB_USER = "skaruddlf123-wq"
GITHUB_REPO = "DBDC-DATA"
RAW_BASE_URL = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/main/"

def get_company_list():
    companies = []
    # 1~26: A사~Z사
    for i in range(26):
        companies.append(f"{chr(65+i)}사")
    # 27~50: AA사~AX사
    for i in range(24):
        first = chr(65 + i // 26)
        second = chr(65 + i % 26)
        companies.append(f"{first}{second}사")
    return companies

COMPANY_LIST = get_company_list()

# -----------------------------------------------------------------------------
# 3. 데이터 로딩 및 파싱 함수 (주민번호 성별코드 파싱 오류 수정)
# -----------------------------------------------------------------------------
@st.cache_data(ttl=3600)
def load_company_data(company_name):
    possible_paths = [
        f"DB가입자명부_{company_name}.xlsx",
        f"DB가입자명부_40개_사명변경/DB가입자명부_{company_name}.xlsx",
        f"DB가입자명부_10개_결과물산출용/DB가입자명부_{company_name}.xlsx"
    ]
    
    df = None
    for path in possible_paths:
        encoded_path = urllib.parse.quote(path)
        url = RAW_BASE_URL + encoded_path
        try:
            df = pd.read_excel(url)
            if df is not None and len(df) > 0:
                break
        except Exception:
            continue
            
    if df is None:
        return None

    # 임금피크 연령 파싱 (Z2 셀)
    peak_age_val = df.iloc[0]['임금피크 연령'] if '임금피크 연령' in df.columns else "만 55세"
    try:
        peak_age = int(str(peak_age_val).replace("만 ", "").replace("세", "").strip())
    except:
        peak_age = 55
        
    # [오류 수정] 주민등록번호 성별 코드를 정확히 하이픈 뒤 첫 번째 자리에서 추출
    def parse_rrn(rrn_val):
        rrn_str = str(rrn_val).strip()
        yy = int(rrn_str[:2])
        if '-' in rrn_str:
            g = rrn_str.split('-')[0]  # 하이픈 뒤 첫 번째 자리가 성별코드 (1, 2, 3, 4)
        else:
            g = rrn_str if len(rrn_str) > 6 else '1'
            
        birth_year = (1900 + yy) if g in ['1', '2'] else (2000 + yy)
        age_2026 = 2026 - birth_year
        return age_2026, birth_year

    df[['만나이', '출생연도']] = df['실명번호'].apply(lambda x: pd.Series(parse_rrn(x)))
    df['임금피크연령'] = peak_age
    
    return df

@st.cache_data(ttl=3600)
def get_all_companies_summary():
    summary_list = []
    for comp in COMPANY_LIST:
        df = load_company_data(comp)
        if df is not None:
            active_df = df[df['기퇴직자 여부'] == 'N'].copy()
            peak_age = active_df.iloc[0]['임금피크연령']
            target_min_age = peak_age - 2
            target_max_age = 59
            
            tot_active_cnt = len(active_df)
            tot_obligation = active_df['퇴직금추계액'].sum()
            avg_obligation = active_df['퇴직금추계액'].mean() if tot_active_cnt > 0 else 0
            
            target_df = active_df[(active_df['만나이'] >= target_min_age) & (active_df['만나이'] <= target_max_age)]
            target_cnt = len(target_df)
            target_ratio = (target_cnt / tot_active_cnt * 100) if tot_active_cnt > 0 else 0
            target_tot_obligation = target_df['퇴직금추계액'].sum()
            target_avg_obligation = target_df['퇴직금추계액'].mean() if target_cnt > 0 else 0
            
            summary_list.append({
                '기업명': comp,
                '임피연령': f"만 {peak_age}세",
                '전체가입자수': tot_active_cnt,
                '전체합산추계액': tot_obligation,
                '전체평균추계액': avg_obligation,
                '대상구간근로자수': target_cnt,
                '대상구간가입자비중': target_ratio,
                '대상구간합산추계액': target_tot_obligation,
                '대상구간평균추계액': target_avg_obligation
            })
            
    sum_df = pd.DataFrame(summary_list)
    return sum_df

# -----------------------------------------------------------------------------
# 4. 사이드바 및 헤더 (상단 로고 내장)
# -----------------------------------------------------------------------------
st.sidebar.title("🎯 영업 Target 대시보드")
st.sidebar.markdown("**한국투자증권 퇴직연금본부**")
main_menu = st.sidebar.radio("메뉴 선택", ["1. 개별 기업 상세 분석", "2. 전체 50개사 우선 영업 Target 순위 요약"])

# =============================================================================
# 페이지 1: 개별 기업 상세 분석
# =============================================================================
if main_menu == "1. 개별 기업 상세 분석":
    selected_company = st.sidebar.selectbox("🏢 기업 선택", COMPANY_LIST, index=0)
    
    with st.spinner(f"{selected_company} 데이터를 분석 중입니다..."):
        df = load_company_data(selected_company)
        all_sum_df = get_all_companies_summary()
        
    if df is not None and all_sum_df is not None:
        peak_age = df.iloc[0]['임금피크연령']
        target_min_age = peak_age - 2
        target_max_age = 59
        
        # 한국투자증권 전용 상단 헤더
        st.markdown(f"""
        <div class="header-container">
            <div>
                <div class="header-title">🏢 {selected_company} DB 가입자 명부 분석 및 영업 Target 명단</div>
                <div class="header-subtitle">기준일자: 2025-07-31 (현시점 2026-07-31 기준) | 설정 임금피크 연령: 만 {peak_age}세 | 분석 대상: 만 {target_min_age}세 ~ 만 {target_max_age}세</div>
            </div>
            <div class="kis-logo-text">
                <div class="kis-brand-friend">true <span>友</span> friend</div>
                <div class="kis-brand-name">Korea Investment</div>
                <div class="kis-brand-sub">& Securities Co., Ltd.</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        active_df = df[df['기퇴직자 여부'] == 'N'].copy()
        
        # [지표 3] 대상 구간 가입자 비중 타이틀 및 전체 50개사 평균 비교
        comp_summary = all_sum_df[all_sum_df['기업명'] == selected_company].iloc[0]
        comp_target_ratio = comp_summary['대상구간가입자비중']
        avg_target_ratio_50 = all_sum_df['대상구간가입자비중'].mean()
        
        st.markdown(f"### 📌 대상 구간 가입자 비중 : **<span style='color:#7A4016;'>{selected_company} : {comp_target_ratio:.1f}%</span> / 전체(50개사 평균) : {avg_target_ratio_50:.1f}%**", unsafe_allow_html=True)
        st.markdown("---")
        
        # [지표 2 상단 KPI]
        tot_cnt = comp_summary['전체가입자수']
        tot_ob = comp_summary['전체합산추계액']
        avg_ob = comp_summary['전체평균추계액']
        target_cnt = comp_summary['대상구간근로자수']
        target_avg_ob = comp_summary['대상구간평균추계액']
        
        kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
        
        with kpi_col1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="kpi-title">전체 가입자 수</div>
                <div class="kpi-value">{tot_cnt:,} 명</div>
                <div class="kpi-sub">재직자 기준</div>
            </div>
            """, unsafe_allow_html=True)
            
        with kpi_col2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="kpi-title">전체 가입자 합산 추계액</div>
                <div class="kpi-value">₩{tot_ob/100000000:,.1f} 억</div>
                <div class="kpi-sub">총 퇴직부채 규모</div>
            </div>
            """, unsafe_allow_html=True)
            
        with kpi_col3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="kpi-title">전체 가입자 평균 추계액</div>
                <div class="kpi-value">₩{avg_ob/10000:,.0f} 만원</div>
                <div class="kpi-sub">1인당 평균 퇴직금</div>
            </div>
            """, unsafe_allow_html=True)

        with kpi_col4:
            st.markdown(f"""
            <div class="metric-card">
                <div class="kpi-title">대상 구간(만 {target_min_age}~{target_max_age}세) 인원</div>
                <div class="kpi-value">{target_cnt:,} 명</div>
                <div class="kpi-sub">대상구간 평균: ₩{target_avg_ob/10000:,.0f}만원</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("---")

        # [지표 1] 연도별 도래 캘린더
        st.subheader(f"📅 1. 임금피크 진입 연도별 도래 캘린더 (만 {target_min_age}세 ~ 만 {target_max_age}세)")
        st.caption("언제(몇 년도 / 몇 년 후), 총 몇 명이 임금피크에 진입하는지 시점별 인원 및 추계액 합산 현황입니다.")
        
        target_df = active_df[(active_df['만나이'] >= target_min_age) & (active_df['만나이'] <= target_max_age)].copy()
        
        def calc_peak_entry(birth_year, p_age):
            peak_year = birth_year + p_age
            years_left = peak_year - 2026
            if years_left <= 0:
                status_str = "임금피크 해당자"
            else:
                status_str = f"{years_left}년 후 임금피크 도래자"
            return status_str, peak_year, years_left

        res = target_df.apply(lambda r: calc_peak_entry(r['출생연도'], peak_age), axis=1)
        target_df['임피진입_상태'] = [r[0] for r in res]
        target_df['임피진입_연도'] = [r[1] for r in res]
        target_df['임피_남은년수'] = [r[2] for r in res]

        cal_summary = target_df.groupby(['임피진입_연도', '임피진입_상태']).agg(
            인원수=('NO', 'count'),
            추계액합계=('퇴직금추계액', 'sum'),
            평균추계액=('퇴직금추계액', 'mean')
        ).reset_index().sort_values(by='임피진입_연도')

        # [오류 수정] st.columns(2)로 2개 인자 명시
        cal_col1, cal_col2 = st.columns(2)
        
        with cal_col1:
            fig_cal = px.bar(
                cal_summary, x='임피진입_연도', y='인원수',
                color='임피진입_상태', text='인원수',
                title=f"{selected_company} 임금피크 진입 연도별 인원 분포",
                labels={'임피진입_연도': '진입 예정 연도', '인원수': '인원 수(명)'},
                color_discrete_sequence=['#7A4016', '#0066B3', '#D97706', '#10B981', '#6B7280']
            )
            fig_cal.update_layout(plot_bgcolor='#ffffff', paper_bgcolor='#ffffff')
            st.plotly_chart(fig_cal, use_container_width=True)

        with cal_col2:
            st.markdown("#### 📌 시점별 도래 인원 및 추계액 합계표")
            disp_cal = cal_summary.copy()
            disp_cal['추계액합계'] = disp_cal['추계액합계'].apply(lambda x: f"₩{x/100000000:,.2f} 억원")
            disp_cal['평균추계액'] = disp_cal['평균추계액'].apply(lambda x: f"₩{x/10000:,.0f} 만원")
            disp_cal.rename(columns={
                '임피진입_연도': '진입연도',
                '임피진입_상태': '구분',
                '인원수': '인원(명)',
                '추계액합계': '합산 추계액',
                '평균추계액': '평균 추계액'
            }, inplace=True)
            st.dataframe(disp_cal[['진입연도', '구분', '인원(명)', '합산 추계액', '평균 추계액']], use_container_width=True, hide_index=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("---")

        # [지표 2 하단 명단]
        st.subheader(f"📋 2. 대상 구간(만 {target_min_age}세 ~ 만 {target_max_age}세) 가입자 상세 영업 명단")
        st.caption("퇴직금 추계액 규모가 큰 순서대로 정렬된 1:1 영업 타깃 명단입니다. (마케팅/TM/SMS 동의 여부 포함)")

        sorted_target_df = target_df.sort_values(by='퇴직금추계액', ascending=False).copy()
        
        display_df = sorted_target_df[[
            'NO', '가입자명', '실명번호', '만나이', '입사일자', '중간정산일자', 
            '임피진입_상태', '퇴직금추계액', '평균임금', 
            '마케팅동의', 'TM동의', 'SMS동의'
        ]].copy()

        display_df.rename(columns={
            '만나이': '만 나이',
            '임피진입_상태': '임피 진입시점 상태',
            '퇴직금추계액': '퇴직금 추계액(원)',
            '평균임금': '평균임금(원)',
            '마케팅동의': '마케팅 동의',
            'TM동의': 'TM 동의',
            'SMS동의': 'SMS 동의'
        }, inplace=True)

        st.dataframe(
            display_df.style.format({
                '퇴직금 추계액(원)': '₩{:,.0f}',
                '평균임금(원)': '₩{:,.0f}'
            }),
            use_container_width=True,
            height=450,
            hide_index=True
        )

# =============================================================================
# 페이지 2: 전체 50개사 우선 영업 Target 순위 요약
# =============================================================================
elif main_menu == "2. 전체 50개사 우선 영업 Target 순위 요약":
    st.markdown("""
    <div class="header-container">
        <div>
            <div class="header-title">🏆 전체 50개사 영업 Target 우선순위 LIST UP</div>
            <div class="header-subtitle">현 시점 기준으로 어디가 우선 영업 대상인지 4가지 주요 지표를 비교하여 순위를 정렬합니다.</div>
        </div>
        <div class="kis-logo-text">
            <div class="kis-brand-friend">true <span>友</span> friend</div>
            <div class="kis-brand-name">Korea Investment</div>
            <div class="kis-brand-sub">& Securities Co., Ltd.</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    with st.spinner("50개 기업 전체 데이터를 비교 분석 중입니다..."):
        all_sum_df = get_all_companies_summary()

    if all_sum_df is not None:
        avg_target_ratio_50 = all_sum_df['대상구간가입자비중'].mean()
        
        st.markdown(f"### 💡 전체 50개사 대상 구간 평균 가입자 비중 : **{avg_target_ratio_50:.1f}%**")
        st.markdown("---")

        st.subheader("⚙️ 순위 정렬 기준 선택")
        
        sort_criterion = st.radio(
            "어떤 지표를 기준으로 영업 우선순위(1위~50위)를 나열할까요?",
            [
                "1. 대상 구간 근로자 수 기준 (인원수가 많은 순)",
                "2. 대상 구간 합산 추계액 기준 (적립금 규모가 큰 순)",
                "3. 대상 구간 평균 추계액 기준 (고액 퇴직금 보유 순)",
                "4. 대상 구간 가입자 비중 기준 (고령화 비율이 높은 순)"
            ],
            index=0
        )

        if "1. 대상 구간 근로자 수" in sort_criterion:
            sort_col = '대상구간근로자수'
            title_suffix = "대상 구간 근로자 수 상위"
        elif "2. 대상 구간 합산 추계액" in sort_criterion:
            sort_col = '대상구간합산추계액'
            title_suffix = "대상 구간 합산 추계액 상위"
        elif "3. 대상 구간 평균 추계액" in sort_criterion:
            sort_col = '대상구간평균추계액'
            title_suffix = "대상 구간 평균 추계액 상위"
        else:
            sort_col = '대상구간가입자비중'
            title_suffix = "대상 구간 가입자 비중 상위"

        sorted_sum_df = all_sum_df.sort_values(by=sort_col, ascending=False).reset_index(drop=True)
        sorted_sum_df['순위'] = sorted_sum_df.index + 1

        st.markdown(f"#### 📊 영업 Target 순위 Top 10 ({title_suffix})")
        top10_df = sorted_sum_df.head(10).copy()
        
        if sort_col == '대상구간합산추계액':
            top10_df['표시값'] = top10_df[sort_col] / 100000000
        elif sort_col == '대상구간평균추계액':
            top10_df['표시값'] = top10_df[sort_col] / 10000
        else:
            top10_df['표시값'] = top10_df[sort_col]

        fig_rank = px.bar(
            top10_df, x='기업명', y='표시값',
            text='표시값', color='표시값',
            title=f"우선 영업 대상 Top 10 기업 ({title_suffix})",
            color_continuous_scale=['#7A4016', '#A0522D', '#CD853F', '#D2B48C', '#0066B3']
        )
        fig_rank.update_layout(plot_bgcolor='#ffffff', paper_bgcolor='#ffffff')
        st.plotly_chart(fig_rank, use_container_width=True)

        st.markdown("---")
        st.markdown("#### 📋 50개 전체 기업 영업 Target 순위 명단 (4개 주요 지표 완비)")

        rank_display_df = sorted_sum_df[[
            '순위', '기업명', '임피연령', 
            '대상구간근로자수', '대상구간합산추계액', '대상구간평균추계액', '대상구간가입자비중'
        ]].copy()

        rank_display_df.rename(columns={
            '임피연령': '임금피크 연령',
            '대상구간근로자수': '1. 대상구간 근로자수(명)',
            '대상구간합산추계액': '2. 대상구간 합산추계액(원)',
            '대상구간평균추계액': '3. 대상구간 평균추계액(원)',
            '대상구간가입자비중': '4. 대상구간 가입자비중(%)'
        }, inplace=True)

        st.dataframe(
            rank_display_df.style.format({
                '1. 대상구간 근로자수(명)': '{:,} 명',
                '2. 대상구간 합산추계액(원)': '₩{:,.0f}',
                '3. 대상구간 평균추계액(원)': '₩{:,.0f}',
                '4. 대상구간 가입자비중(%)': '{:.1f}%'
            }),
            use_container_width=True,
            height=600,
            hide_index=True
        )
