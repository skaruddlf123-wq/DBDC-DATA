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

# 한국투자증권 브랜드 스타일 정의
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
    
    .welcome-card {
        background-color: #ffffff;
        border: 1px solid #E5E0DA;
        border-radius: 8px;
        padding: 30px;
        margin-top: 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
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
# 3. 데이터 로딩 및 파싱 함수
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
        try
