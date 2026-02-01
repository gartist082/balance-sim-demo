import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import time

# 페이지 기본 설정
st.set_page_config(page_title="MMORPG Balance Sim Pro", layout="wide")

# -----------------------------------------------------------------------------
# 1. 데이터 로드 및 전처리
# -----------------------------------------------------------------------------
@st.cache_data
def load_data(uploaded_file):
    try:
        xls = pd.ExcelFile(uploaded_file)
        stats_df = pd.read_excel(xls, 'Stats')
        skills_df = pd.read_excel(xls, 'Skills')
        
        # 컬럼명 공백 제거
        stats_df.columns = stats_df.columns.str.strip()
        skills_df.columns = skills_df.columns.str.strip()
        
        return stats_df, skills_df
    except Exception as e:
        return None, None

# -----------------------------------------------------------------------------
# 2. 시뮬레이션 엔진 (Core Logic)
# -----------------------------------------------------------------------------
class Character:
    def __init__(self, stat_row, skills_df, back_attack_prob=0.0):
        self.name = stat_row['Class']
        # 기본 스탯
        self.base_atk = stat_row['Base_ATK']
        self.crit_rate = stat_row['Crit_Rate']
        self.crit_dmg = stat_row['Crit_Dmg']
        self.cdr = stat_row['Cooldown_Reduction']
        self.back_attack_bonus = stat_row.get('Back_Attack_Bonus', 1.0) # 없으면 1.0
        
        # 자원(MP) 스탯
        self.max_mp = stat_row.get('Max_MP', 100)
        self.mp_regen = stat_row.get('MP_Regen', 5)
        self.current_mp = self.max_mp
        
        # 시뮬레이션 설정
        self.back_attack_prob = back_attack_prob # 백어택 성공 확률
        
        # 스킬 세팅
        self.skills = skills_df[skills_df['Class'] == self.name].copy()
        self.skills['next_available'] = 0.0
        
        # 상태 변수
        self.current_time = 0.0
        self.is_casting = False
        self.cast_end_time = 0.0
        self.total_damage = 0
        self.damage_log = []

    def update(self, time_step):
        self.current_time += time_step
        
        # 1. MP 회복 (초당 회복량 * 시간)
        if self.current_mp < self.max_mp:
            self.current_mp += self.mp_regen * time_step
            if self.current_mp > self.max_mp:
                self.current_mp = self.max_mp

        # 2. 캐스팅 중인지 확인
        if self.is_casting:
            if self.current_time >= self.cast_end_time:
                self.is_casting = False # 캐스팅 완료
            else:
                return # 캐스팅 중엔 행동 불가
        
        # 3. 사용 가능한 스킬 탐색
        # 조건: 쿨타임 완료 AND 마나 충분
        available_skills = self.skills[
            (self.skills['next_available'] <= self.current_time) & 
            (self.skills['MP_Cost'] <= self.current_mp)
        ].sort_values(by='Damage_Coef', ascending=False) # 계수 높은 것 우선
        
        if not available_skills.empty:
            skill = available_skills.iloc[0]
            self.use_skill(skill)
        else:
            # 스킬을 못 쓰면 대기 (평타가 쿨타임 0, MP 0이면 평타를 치게 됨)
            pass

    def use_skill(self, skill):
        skill_idx = skill.name
        skill_name = skill['Skill_Name']
        hit_count = int(skill.get('Hit_Count', 1))
        mp_cost = skill.get('MP_Cost', 0)
        
        # 자원 소모
        self.current_mp -= mp_cost
        
        # 데미지 계산 (다단 히트 로직)
        total_skill_dmg = 0
        hits_info = [] # 로그용
        
        for _ in range(hit_count):
            # 1) 치명타 판정
            is_crit = np.random.random() < self.crit_rate
            dmg_mult = self.crit_dmg if is_crit else 1.0
            
            # 2) 백어택 판정 (스킬이 백어택 가능하고, 확률에 성공했을 때)
            is_back = False
            if skill['Is_BackAttack'] and (np.random.random() < self.back_attack_prob):
                is_back = True
                dmg_mult *= self.back_attack_bonus
            
            # 3) 최종 데미지 (계수를 타수만큼 나누지 않고, 기획 데이터가 '타당 데미지'가 아니라 '총 데미지'라면 나눠야 함)
            # 여기서는 편의상 입력된 Damage_Coef가 "총 계수"라고 가정하고 타수로 나눔
            damage = (self.base_atk * skill['Damage_Coef'] / hit_count) * dmg_mult
            
            total_skill_dmg += damage
            
        # 로그 기록 (타수 합산해서 기록)
        self.total_damage += total_skill_dmg
        self.damage_log.append({
            'Time': round(self.current_time, 2),
            'Skill': skill_name,
            'Damage': int(total_skill_dmg),
            'MP': int(self.current_mp),
            'Cumulative_Damage': int(self.total_damage)
        })
        
        # 상태 업데이트 (캐스팅 시작)
        self.is_casting = True
        self.cast_end_time = self.current_time + skill['Cast_Time']
        
        # 쿨타임 적용 (쿨감 반영)
        real_cooldown = skill['Cooldown'] * (1 - self.cdr)
        self.skills.at[skill_idx, 'next_available'] = self.current_time + real_cooldown

# -----------------------------------------------------------------------------
# 3. 메인 UI (Streamlit)
# -----------------------------------------------------------------------------
st.title("⚔️ MMORPG Balance Simulator (Pro Ver.)")
st.markdown("### 데이터 기반 전투 검증 및 몬테카를로 시뮬레이션")

# 사이드바 설정
st.sidebar.header("1. Data & Settings")
uploaded_file = st.sidebar.file_uploader("Upload BalanceSheets.xlsx", type=['xlsx'])
default_file = "BalanceSheets.xlsx"

if uploaded_file:
    stats_df, skills_df = load_data(uploaded_file)
else:
    try:
        stats_df, skills_df = load_data(default_file)
        st.sidebar.success(f"기본 파일 로드됨: {default_file}")
    except:
        stats_df, skills_df = None, None
        st.sidebar.error("엑셀 파일을 업로드하거나 폴더에 넣어주세요.")

if stats_df is not None and skills_df is not None:
    
    # 클래스 선택
    selected_class = st.sidebar.selectbox("Class Select", stats_df['Class'].unique())
    original_stat = stats_df[stats_df['Class'] == selected_class].iloc[0]
    
    # -------------------------------------------------------------------------
    # A/B 테스트 설정 (수치 조정 시뮬레이션)
    # -------------------------------------------------------------------------
    st.sidebar.header("2. Stat Tuning (A/B Test)")
    st.sidebar.info("아래 수치를 조정하여 원본과 비교해보세요.")
    
    adj_atk = st.sidebar.number_input("Base ATK", value=int(original_stat['Base_ATK']))
    adj_crit = st.sidebar.slider("Crit Rate", 0.0, 1.0, float(original_stat['Crit_Rate']))
    adj_cdr = st.sidebar.slider("Cooldown Reduction", 0.0, 0.5, float(original_stat['Cooldown_Reduction']))
    
    # 백어택 확률 (플레이어 컨트롤 실력 변수)
    back_attack_prob = st.sidebar.slider("Back Attack Success Rate (Control)", 0.0, 1.0, 0.5, help="백어택 스킬 사용 시 성공할 확률")
    sim_duration = st.sidebar.slider("Combat Time (sec)", 30, 180, 60)

    # -------------------------------------------------------------------------
    # 메인 화면: 실행 및 결과
    # -------------------------------------------------------------------------
    
    col_act1, col_act2 = st.columns(2)
    with col_act1:
        run_single = st.button("▶️ 단일 전투 실행 (Single Run)", type="primary")
    with col_act2:
        run_monte = st.button("🎲 몬테카를로 시뮬레이션 (100회)", type="secondary")

    # 조정된 스탯으로 새 데이터 생성
    tuned_stat = original_stat.copy()
    tuned_stat['Base_ATK'] = adj_atk
    tuned_stat['Crit_Rate'] = adj_crit
    tuned_stat['Cooldown_Reduction'] = adj_cdr

    # === 기능 1: 단일 전투 실행 (로그 확인용) ===
    if run_single:
        # A: 원본, B: 튜닝
        char_a = Character(original_stat, skills_df, back_attack_prob)
        char_b = Character(tuned_stat, skills_df, back_attack_prob)
        
        time_step = 0.1
        steps = int(sim_duration / time_step)
        
        for _ in range(steps):
            char_a.update(time_step)
            char_b.update(time_step)
            
        # 결과 표시
        dps_a = char_a.total_damage / sim_duration
        dps_b = char_b.total_damage / sim_duration
        gap = ((dps_b - dps_a) / dps_a) * 100
        
        st.subheader("📊 Single Run Result")
        m1, m2, m3 = st.columns(3)
        m1.metric("Original DPS", f"{int(dps_a):,}")
        m2.metric("Tuned DPS", f"{int(dps_b):,}", delta=f"{gap:.2f}%")
        m3.metric("Skill Uses (Tuned)", len(char_b.damage_log))
        
        # 그래프: 시간대별 누적 딜량 비교
        df_a = pd.DataFrame(char_a.damage_log)
        df_b = pd.DataFrame(char_b.damage_log)
        df_a['Version'] = 'Original'
        df_b['Version'] = 'Tuned'
        
        if not df_a.empty and not df_b.empty:
            combined_df = pd.concat([df_a, df_b])
            fig = px.line(combined_df, x='Time', y='Cumulative_Damage', color='Version', 
                          title="Damage Comparison Over Time", markers=True)
            st.plotly_chart(fig, use_container_width=True)
            
            with st.expander("상세 전투 로그 (Tuned Ver)"):
                st.dataframe(df_b)

    # === 기능 2: 몬테카를로 시뮬레이션 (확률 분포 확인용) ===
    if run_monte:
        st.subheader("🎲 Monte Carlo Simulation")
        
        # 테스트를 위해 횟수를 1,000 -> 100으로 줄임
        SIM_COUNT = 100  
        
        results = []
        progress_bar = st.progress(0)
        status_text = st.empty() # 진행상황 텍스트 표시용
        
        start_time = time.time()
        
        # Spinner 추가
        with st.spinner(f'전투 {SIM_COUNT}회를 시뮬레이션 중입니다... 잠시만 기다려주세요!'):
            for i in range(SIM_COUNT):
                # 튜닝된 스탯으로만 시뮬레이션
                sim_char = Character(tuned_stat, skills_df, back_attack_prob)
                
                step = 0.1
                max_step = int(sim_duration / step)
                for _ in range(max_step):
                    sim_char.update(step)
                
                results.append(sim_char.total_damage / sim_duration) # DPS 저장
                
                # 진행률 업데이트
                if i % 10 == 0:
                    progress_bar.progress((i + 1) / SIM_COUNT)
                    status_text.text(f"진행률: {int((i+1)/SIM_COUNT*100)}% 완료")
        
        progress_bar.progress(100)
        status_text.text("✅ 시뮬레이션 완료!")
        elapsed = time.time() - start_time
        
        # 결과 분석
        avg_dps = np.mean(results)
        min_dps = np.min(results)
        max_dps = np.max(results)
        std_dev = np.std(results) # 표준편차
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Average DPS", f"{int(avg_dps):,}")
        c2.metric("Min DPS (Unlucky)", f"{int(min_dps):,}")
        c3.metric("Max DPS (Lucky)", f"{int(max_dps):,}")
        c4.metric("Stability (Std Dev)", f"{int(std_dev):,}")
        
        st.success(f"Simulation Complete in {elapsed:.2f} seconds! (N={SIM_COUNT})")
        
        # 히스토그램 (분포도)
        fig_hist = px.histogram(results, nbins=30, title=f"DPS Distribution (N={SIM_COUNT})",
                                labels={'value': 'DPS', 'count': 'Frequency'})
        fig_hist.add_vline(x=avg_dps, line_dash="dash", line_color="red", annotation_text="Avg")
        st.plotly_chart(fig_hist, use_container_width=True)
        
        st.markdown("""
        **💡 분석 가이드:**
        * 그래프가 **뾰족할수록(표준편차가 낮을수록)** 운에 좌우되지 않는 안정적인 딜러입니다.
        * 그래프가 **넓게 퍼져있다면**, 치명타나 확률형 스킬 의존도가 높다는 뜻입니다.
        """)