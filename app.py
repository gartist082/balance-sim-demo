import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# 페이지 기본 설정
st.set_page_config(page_title="Lost Ark Mobile - Class Balance Sim", layout="wide")

# -----------------------------------------------------------------------------
# 1. 데이터 로드 및 전처리 (Data Loading)
# -----------------------------------------------------------------------------
@st.cache_data
def load_data(uploaded_file):
    try:
        # 엑셀 파일에서 시트별로 데이터 로드
        xls = pd.ExcelFile(uploaded_file)
        stats_df = pd.read_excel(xls, 'Stats')
        skills_df = pd.read_excel(xls, 'Skills')
        
        # 컬럼명 공백 제거 및 소문자 변환 (오류 방지)
        stats_df.columns = stats_df.columns.str.strip()
        skills_df.columns = skills_df.columns.str.strip()
        
        return stats_df, skills_df
    except Exception as e:
        st.error(f"데이터 로드 중 오류 발생: {e}")
        return None, None

# -----------------------------------------------------------------------------
# 2. 시뮬레이션 엔진 (Core Logic) - 시간 흐름(Time-based) 방식
# -----------------------------------------------------------------------------
class Character:
    def __init__(self, stat_row, skills_df):
        self.name = stat_row['Class']
        self.base_atk = stat_row['Base_ATK']
        self.crit_rate = stat_row['Crit_Rate']
        self.crit_dmg = stat_row['Crit_Dmg']
        self.cdr = stat_row['Cooldown_Reduction'] # 쿨타임 감소
        
        # 해당 클래스의 스킬만 가져오기
        self.skills = skills_df[skills_df['Class'] == self.name].copy()
        # 쿨타임 관리용 컬럼 추가 (Next Available Time)
        self.skills['next_available'] = 0.0
        
        # 시뮬레이션 상태 변수
        self.current_time = 0.0
        self.is_casting = False
        self.cast_end_time = 0.0
        self.total_damage = 0
        self.damage_log = []

    def update(self, time_step):
        self.current_time += time_step
        
        # 1. 캐스팅 중인지 확인
        if self.is_casting:
            if self.current_time >= self.cast_end_time:
                self.is_casting = False # 캐스팅 완료
            else:
                return # 캐스팅 중에는 아무것도 안함
        
        # 2. 사용 가능한 스킬 탐색 (우선순위: 쿨타임 돌아온 것 중 데미지 계수 높은 순)
        # 실제 쿨타임 적용: cooldown * (1 - cdr)
        ready_skills = self.skills[self.skills['next_available'] <= self.current_time].sort_values(by='Damage_Coef', ascending=False)
        
        if not ready_skills.empty:
            skill = ready_skills.iloc[0]
            self.use_skill(skill)

    def use_skill(self, skill):
        skill_idx = skill.name
        
        # 데미지 계산
        is_crit = np.random.random() < self.crit_rate
        dmg_mult = self.crit_dmg if is_crit else 1.0
        damage = self.base_atk * skill['Damage_Coef'] * dmg_mult
        
        # 로그 기록
        self.total_damage += damage
        self.damage_log.append({
            'Time': round(self.current_time, 2),
            'Skill': skill['Skill_Name'],
            'Damage': round(damage),
            'Type': 'Critical' if is_crit else 'Hit',
            'Cumulative_Damage': round(self.total_damage)
        })
        
        # 상태 업데이트 (캐스팅 시작)
        self.is_casting = True
        self.cast_end_time = self.current_time + skill['Cast_Time']
        
        # 쿨타임 적용 (쿨감 반영)
        real_cooldown = skill['Cooldown'] * (1 - self.cdr)
        # 스킬 사용 완료 시점이 아니라 '사용 시작' 시점부터 쿨타임이 도는 것이 일반적 (게임따라 다름)
        self.skills.at[skill_idx, 'next_available'] = self.current_time + real_cooldown

# -----------------------------------------------------------------------------
# 3. UI 구성 (Streamlit)
# -----------------------------------------------------------------------------
st.title("⚔️ Lost Ark Mobile - Combat Balance Simulator")
st.markdown("""
이 시뮬레이터는 **Time-based Logic**을 사용하여 실제 인게임 전투 상황을 모사합니다.
쿨타임 감소, 캐스팅 시간, 크리티컬 확률이 모두 실시간으로 반영됩니다.
""")

# 사이드바: 설정
st.sidebar.header("Simulation Settings")

# 파일 업로더 (기본적으로 로컬 파일 찾기 시도)
uploaded_file = st.sidebar.file_uploader("Upload Excel File", type=['xlsx'])
default_file = "BalanceSheets.xlsx"

stats_df, skills_df = None, None

if uploaded_file:
    stats_df, skills_df = load_data(uploaded_file)
else:
    try:
        stats_df, skills_df = load_data(default_file)
        st.sidebar.success(f"기본 파일 로드됨: {default_file}")
    except:
        st.sidebar.warning("좌측 메뉴에서 엑셀 파일을 업로드해주세요.")

if stats_df is not None and skills_df is not None:
    # 클래스 선택
    selected_class = st.sidebar.selectbox("Select Class", stats_df['Class'].unique())
    
    # 시뮬레이션 시간 설정
    sim_duration = st.sidebar.slider("Combat Duration (sec)", 30, 300, 60)
    
    # 실행 버튼
    if st.sidebar.button("Run Simulation", type="primary"):
        
        # 선택된 클래스 데이터 추출
        stat_row = stats_df[stats_df['Class'] == selected_class].iloc[0]
        
        # 시뮬레이션 실행
        char = Character(stat_row, skills_df)
        time_step = 0.1 # 0.1초 단위 시뮬레이션
        
        with st.spinner('Simulating combat...'):
            for _ in range(int(sim_duration / time_step)):
                char.update(time_step)
        
        # 결과 데이터프레임
        log_df = pd.DataFrame(char.damage_log)
        
        if log_df.empty:
            st.error("데미지를 입힌 기록이 없습니다. 스탯이나 스킬 데이터를 확인해주세요.")
        else:
            # --- 결과 대시보드 ---
            dps = char.total_damage / sim_duration
            
            # 1. 핵심 지표 (KPI)
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Damage", f"{int(char.total_damage):,}")
            col2.metric("DPS (Damage Per Sec)", f"{int(dps):,}")
            col3.metric("Skill Count", f"{len(log_df)} times")
            
            # 2. 차트 영역
            tab1, tab2 = st.tabs(["📈 Damage Graph", "🥧 Skill Breakdown"])
            
            with tab1:
                # 시간대별 누적 데미지 그래프
                fig_line = px.line(log_df, x='Time', y='Cumulative_Damage', 
                                   title=f"{selected_class} - Damage Over Time",
                                   labels={'Cumulative_Damage': 'Total Damage'})
                st.plotly_chart(fig_line, use_container_width=True)
                
            with tab2:
                # 스킬별 데미지 비중
                skill_dmg = log_df.groupby('Skill')['Damage'].sum().reset_index()
                fig_pie = px.pie(skill_dmg, values='Damage', names='Skill', 
                                 title="Damage Distribution by Skill", hole=0.4)
                st.plotly_chart(fig_pie, use_container_width=True)

            # 3. 상세 전투 로그 (Expander)
            with st.expander("View Combat Log (Raw Data)"):
                st.dataframe(log_df, use_container_width=True)

            # 4. 사용된 스탯 정보 표시
            st.info(f"**Applied Stats:** Base ATK: {char.base_atk} | Crit Rate: {char.crit_rate*100}% | Crit Dmg: {char.crit_dmg}x | CDR: {char.cdr*100}%")

else:
    st.info("Please upload a balance data file to proceed.")
