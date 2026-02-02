import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import time

# 페이지 기본 설정
st.set_page_config(page_title="MMORPG Balance Verification System", layout="wide")

# -----------------------------------------------------------------------------
# 1. 데이터 로드 및 전처리
# -----------------------------------------------------------------------------
@st.cache_data
def load_data(uploaded_file):
    try:
        xls = pd.ExcelFile(uploaded_file)
        data_dict = {}
        for sheet_name in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name)
            df.columns = df.columns.str.strip()
            data_dict[sheet_name] = df
        return data_dict
    except Exception as e:
        return None

def interpolate_stat(level, growth_df, target_col):
    if level in growth_df['Level'].values:
        return growth_df.loc[growth_df['Level'] == level, target_col].values[0]
    lower = growth_df[growth_df['Level'] < level]
    upper = growth_df[growth_df['Level'] > level]
    if lower.empty: return upper.iloc[0][target_col]
    if upper.empty: return lower.iloc[-1][target_col]
    x1, y1 = lower.iloc[-1]['Level'], lower.iloc[-1][target_col]
    x2, y2 = upper.iloc[0]['Level'], upper.iloc[0][target_col]
    return y1 + (y2 - y1) * (level - x1) / (x2 - x1)

# -----------------------------------------------------------------------------
# 2. 시뮬레이션 엔진 (Original Logic 복구)
# -----------------------------------------------------------------------------
class Character:
    def __init__(self, stat_row, skills_df=None, back_attack_prob=0.5, multiplier=1.0):
        self.name = stat_row.get('Class', 'User')
        
        # 스탯 (과금 보정 적용)
        self.base_atk = stat_row['Base_ATK'] * multiplier
        self.crit_rate = stat_row.get('Crit_Rate', 0)
        self.crit_dmg = stat_row.get('Crit_Dmg', 1.5)
        self.cdr = stat_row.get('Cooldown_Reduction', 0)
        self.back_attack_bonus = stat_row.get('Back_Attack_Bonus', 1.0)
        
        # 방어/체력
        self.max_hp = stat_row.get('Base_HP', 1000) * multiplier
        self.current_hp = self.max_hp
        self.defense = stat_row.get('Base_DEF', 0) * multiplier
        
        # 자원 (MP)
        self.max_mp = stat_row.get('Max_MP', 100)
        self.mp_regen = stat_row.get('MP_Regen', 5)
        self.current_mp = self.max_mp
        
        # 시뮬레이션 설정
        self.back_attack_prob = back_attack_prob
        
        # 스킬 세팅
        if skills_df is not None:
            self.skills = skills_df[skills_df['Class'] == self.name].copy()
            self.skills['next_available'] = 0.0
        else:
            self.skills = pd.DataFrame() # 스킬 없음

        self.current_time = 0.0
        self.is_casting = False
        self.cast_end_time = 0.0
        self.total_damage = 0
        self.damage_log = []

    def update(self, time_step):
        self.current_time += time_step
        
        # MP 회복
        if self.current_mp < self.max_mp:
            self.current_mp += self.mp_regen * time_step
        
        # 행동 불가(캐스팅) 확인
        if self.is_casting:
            if self.current_time >= self.cast_end_time:
                self.is_casting = False
            else:
                return 0

        # 사용 가능 스킬 탐색 (쿨타임 & MP)
        if not self.skills.empty:
            ready_skills = self.skills[
                (self.skills['next_available'] <= self.current_time) &
                (self.skills['MP_Cost'] <= self.current_mp)
            ].sort_values(by='Damage_Coef', ascending=False)
            
            if not ready_skills.empty:
                return self.use_skill(ready_skills.iloc[0])
        
        # 스킬 못 쓰면 평타 (예시: 1초 쿨타임, 계수 1.0)
        # 실제로는 평타도 스킬 리스트에 넣는 게 좋음
        return 0 

    def use_skill(self, skill):
        skill_idx = skill.name
        self.current_mp -= skill['MP_Cost']
        
        total_skill_dmg = 0
        hit_count = int(skill.get('Hit_Count', 1))
        
        # 다단히트 로직
        for _ in range(hit_count):
            is_crit = np.random.random() < self.crit_rate
            dmg_mult = self.crit_dmg if is_crit else 1.0
            
            # 백어택 로직
            if skill.get('Is_BackAttack', False) and (np.random.random() < self.back_attack_prob):
                dmg_mult *= self.back_attack_bonus
            
            # 데미지 계산
            damage = (self.base_atk * skill['Damage_Coef'] / hit_count) * dmg_mult
            total_skill_dmg += damage
            
        self.total_damage += total_skill_dmg
        
        # 로그
        self.damage_log.append({
            'Time': round(self.current_time, 2),
            'Skill': skill['Skill_Name'],
            'Damage': int(total_skill_dmg),
            'Cumulative': int(self.total_damage)
        })
        
        # 상태 업데이트
        self.is_casting = True
        self.cast_end_time = self.current_time + skill['Cast_Time']
        self.skills.at[skill_idx, 'next_available'] = self.current_time + skill['Cooldown'] * (1 - self.cdr)
        
        return total_skill_dmg

# -----------------------------------------------------------------------------
# 3. 메인 UI
# -----------------------------------------------------------------------------
st.title("⚖️ MMORPG Balance Verification System")
uploaded_file = st.sidebar.file_uploader("Upload Data", type=['xlsx'])
default_file = "BalanceSheets.xlsx"

data = None
if uploaded_file: data = load_data(uploaded_file)
else: 
    try: data = load_data(default_file)
    except: pass

if data:
    tab1, tab2, tab3 = st.tabs(["⚔️ 전투 시뮬레이션", "🛡️ 플레이 검증", "💰 밸런스 검증"])

    # === TAB 1: 전투 시뮬레이션 (복구완료) ===
    with tab1:
        st.subheader("Advanced Combat Simulator")
        stats_df = data['Stats']
        skills_df = data['Skills']
        
        c_class = st.selectbox("Class", stats_df['Class'].unique())
        stat_row = stats_df[stats_df['Class'] == c_class].iloc[0]
        
        # A/B Test 설정
        col1, col2 = st.columns(2)
        with col1:
            adj_atk = st.number_input("Base ATK", value=int(stat_row['Base_ATK']))
            back_prob = st.slider("Back Attack Prob", 0.0, 1.0, 0.5)
        with col2:
            sim_time = st.slider("Sim Duration (sec)", 30, 180, 60)
            
        # 튜닝된 스탯 적용
        tuned_stat = stat_row.copy()
        tuned_stat['Base_ATK'] = adj_atk

        b1, b2 = st.columns(2)
        run_single = b1.button("▶️ Single Run")
        run_monte = b2.button("🎲 Monte Carlo (100회)")
        
        if run_single:
            char = Character(tuned_stat, skills_df, back_prob)
            steps = int(sim_time / 0.1)
            for _ in range(steps): char.update(0.1)
            
            st.metric("Total Damage", f"{int(char.total_damage):,}")
            if char.damage_log:
                df_log = pd.DataFrame(char.damage_log)
                st.line_chart(df_log.set_index('Time')['Cumulative'])
                
        if run_monte:
            results = []
            progress = st.progress(0)
            with st.spinner("Simulating..."):
                for i in range(100):
                    c = Character(tuned_stat, skills_df, back_prob)
                    for _ in range(int(sim_time/0.1)): c.update(0.1)
                    results.append(c.total_damage/sim_time)
                    if i % 10 == 0: progress.progress(i/100)
            progress.progress(100)
            
            avg_dps = np.mean(results)
            st.metric("Average DPS", f"{int(avg_dps):,}")
            fig = px.histogram(results, nbins=20, title="DPS Distribution")
            fig.add_vline(x=avg_dps, line_dash="dash", line_color="red")
            st.plotly_chart(fig, use_container_width=True)

    # === TAB 2: 플레이 검증 (생존 비율) ===
    with tab2:
        st.subheader("PVE Difficulty Verification")
        if st.button("🛡️ Run Dungeon Verification"):
            growth_df = data['User_Growth']
            res_list = []
            for idx, row in data['Dungeon_List'].iterrows():
                lvl = row['Unlock_Level']
                # 유저 스펙
                u_hp = interpolate_stat(lvl, growth_df, 'Base_HP')
                u_atk = interpolate_stat(lvl, growth_df, 'Base_ATK')
                u_def = interpolate_stat(lvl, growth_df, 'Base_DEF')
                
                # 몬스터 스펙
                m_temp = data['Monster_Template'][data['Monster_Template']['Monster_Type'] == row['Monster_Type']].iloc[0]
                m_hp = u_hp * m_temp['HP_Ratio']
                m_atk = u_atk * m_temp['ATK_Ratio']
                m_def = u_def * m_temp['DEF_Ratio']
                
                # 생존 턴 계산 (간이)
                user_turns = u_hp / max(1, m_atk - u_def)
                mon_turns = m_hp / max(1, u_atk - m_def)
                ratio = user_turns / mon_turns
                
                status = "🟢 Pass" if ratio >= row['Target_Survival_Ratio'] else "🔴 Fail"
                res_list.append({
                    "Dungeon": row['Dungeon_Name'],
                    "Lvl": lvl,
                    "Ratio": round(ratio, 2),
                    "Target": row['Target_Survival_Ratio'],
                    "Result": status
                })
            st.dataframe(pd.DataFrame(res_list))

    # === TAB 3: 밸런스 검증 (란체스터) ===
    with tab3:
        st.subheader("Balance & Lanchester Check")
        target_lv = st.slider("Target Level", 1, 100, 50)
        if st.button("💰 Check Balance"):
            base_hp = interpolate_stat(target_lv, data['User_Growth'], 'Base_HP')
            base_atk = interpolate_stat(target_lv, data['User_Growth'], 'Base_ATK')
            
            res_b = []
            for idx, row in data['Payment_Grade'].iterrows():
                mult = row['Stat_Multiplier']
                cp = (base_atk * mult) * (base_hp * mult) / 100
                res_b.append({"Grade": row['Grade'], "CP": int(cp)})
            
            df_b = pd.DataFrame(res_b)
            st.dataframe(df_b)
            
            # 란체스터
            try:
                h_cp = df_b[df_b['Grade'].str.contains("Heavy")]['CP'].values[0]
                f_cp = df_b[df_b['Grade'].str.contains("Free")]['CP'].values[0]
                n_users = np.sqrt(h_cp / f_cp)
                st.success(f"헤비과금 1명 = 무과금 {n_users:.2f}명 (Lanchester Square Law)")
            except:
                st.warning("등급 이름에 'Heavy', 'Free'가 포함되어야 계산됩니다.")
