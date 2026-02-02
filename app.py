import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
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
        # 모든 시트 다 읽기
        data_dict = {}
        for sheet_name in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name)
            # 컬럼명 공백 제거
            df.columns = df.columns.str.strip()
            data_dict[sheet_name] = df
            
        return data_dict
    except Exception as e:
        st.error(f"데이터 로드 중 오류: {e}")
        return None

# 선형 보간 함수 (레벨에 따른 스펙 추정용)
def interpolate_stat(level, growth_df, target_col):
    # 해당 레벨이 딱 있으면 그거 리턴
    if level in growth_df['Level'].values:
        return growth_df.loc[growth_df['Level'] == level, target_col].values[0]
    
    # 없으면 앞뒤 레벨 찾아서 보간 (Linear Interpolation)
    lower = growth_df[growth_df['Level'] < level]
    upper = growth_df[growth_df['Level'] > level]
    
    if lower.empty: return upper.iloc[0][target_col] # 최소 레벨보다 작음
    if upper.empty: return lower.iloc[-1][target_col] # 최대 레벨보다 큼
    
    x1, y1 = lower.iloc[-1]['Level'], lower.iloc[-1][target_col]
    x2, y2 = upper.iloc[0]['Level'], upper.iloc[0][target_col]
    
    # 직선 방정식: y = y1 + (y2-y1) * (x-x1) / (x2-x1)
    return y1 + (y2 - y1) * (level - x1) / (x2 - x1)

# -----------------------------------------------------------------------------
# 2. 시뮬레이션 엔진 (Core Logic)
# -----------------------------------------------------------------------------
class Character:
    def __init__(self, stat_row, skills_df, multiplier=1.0):
        self.name = stat_row.get('Class', 'User')
        # 과금 등급 보정치 적용 (기본 1.0)
        self.multiplier = multiplier
        
        self.base_atk = stat_row['Base_ATK'] * multiplier
        self.crit_rate = stat_row.get('Crit_Rate', 0)
        self.crit_dmg = stat_row.get('Crit_Dmg', 1.5)
        self.cdr = stat_row.get('Cooldown_Reduction', 0)
        self.back_attack_bonus = stat_row.get('Back_Attack_Bonus', 1.0)
        
        # 방어/체력 스탯 (없으면 기본값)
        self.max_hp = stat_row.get('Base_HP', 1000) * multiplier
        self.current_hp = self.max_hp
        self.defense = stat_row.get('Base_DEF', 0) * multiplier
        
        # 자원
        self.max_mp = stat_row.get('Max_MP', 100)
        self.mp_regen = stat_row.get('MP_Regen', 5)
        self.current_mp = self.max_mp
        
        # 스킬
        if skills_df is not None:
            self.skills = skills_df[skills_df['Class'] == self.name].copy()
            self.skills['next_available'] = 0.0
        else:
            self.skills = pd.DataFrame() # 스킬 없음 (평타만)
            
        self.current_time = 0.0
        self.is_casting = False
        self.cast_end_time = 0.0
        self.total_damage_dealt = 0

    def take_damage(self, damage):
        # 방어력 공식 (단순 뺄셈 공식: Dmg = Atk - Def)
        # 최소 데미지 1 보장
        actual_dmg = max(1, damage - self.defense)
        self.current_hp -= actual_dmg
        return actual_dmg

    def update_combat(self, time_step, target):
        self.current_time += time_step
        
        # MP 회복
        if self.current_mp < self.max_mp:
            self.current_mp += self.mp_regen * time_step
            
        # 행동 가능 확인
        if self.is_casting:
            if self.current_time >= self.cast_end_time:
                self.is_casting = False
            else:
                return 0 # 딜 못넣음

        # 스킬 사용 로직 (간소화: 쿨타임 되면 무조건 사용)
        damage_output = 0
        
        # 1. 사용 가능 스킬 찾기
        if not self.skills.empty:
            ready_skills = self.skills[
                (self.skills['next_available'] <= self.current_time) &
                (self.skills['MP_Cost'] <= self.current_mp)
            ].sort_values(by='Damage_Coef', ascending=False)
            
            if not ready_skills.empty:
                skill = ready_skills.iloc[0]
                damage_output = self.use_skill(skill)
        
        # 스킬이 없거나 못 썼으면 평타 (기본 공격)
        if damage_output == 0:
            # 평타: 쿨타임 1초 가정
            damage_output = self.base_atk 

        # 타겟에게 데미지 적용
        actual_dmg = target.take_damage(damage_output)
        self.total_damage_dealt += actual_dmg
        return actual_dmg

    def use_skill(self, skill):
        # 비용 소모
        self.current_mp -= skill['MP_Cost']
        
        # 데미지 계산
        is_crit = np.random.random() < self.crit_rate
        dmg = self.base_atk * skill['Damage_Coef'] * (self.crit_dmg if is_crit else 1.0)
        
        # 쿨타임 적용
        self.skills.at[skill.name, 'next_available'] = self.current_time + skill['Cooldown'] * (1 - self.cdr)
        
        # 캐스팅 적용
        self.is_casting = True
        self.cast_end_time = self.current_time + skill['Cast_Time']
        
        return dmg

# -----------------------------------------------------------------------------
# 3. 메인 UI 구성
# -----------------------------------------------------------------------------
st.title("⚖️ MMORPG Balance Verification System")
st.markdown("**데이터 기반 전투/성장/밸런스 통합 검증 도구**")

uploaded_file = st.sidebar.file_uploader("Upload Data (BalanceSheets.xlsx)", type=['xlsx'])
default_file = "BalanceSheets.xlsx"

data = None
if uploaded_file:
    data = load_data(uploaded_file)
else:
    try:
        data = load_data(default_file)
        st.sidebar.success("기본 데이터 로드 완료")
    except:
        st.sidebar.warning("데이터 파일을 업로드해주세요.")

if data:
    # 탭 구성
    tab1, tab2, tab3 = st.tabs(["⚔️ 전투 시뮬레이션", "🛡️ 플레이 검증 (생존 비율)", "💰 밸런스 검증 (과금 격차)"])

    # =========================================================================
    # TAB 1: 기존 전투 시뮬레이터 (단일 캐릭터 DPS 검증)
    # =========================================================================
    with tab1:
        st.subheader("Single Character DPS Simulation")
        stats_df = data['Stats']
        skills_df = data['Skills']
        
        selected_class = st.selectbox("Class Select", stats_df['Class'].unique())
        stat_row = stats_df[stats_df['Class'] == selected_class].iloc[0]
        
        if st.button("▶️ Run DPS Test (Single)"):
            char = Character(stat_row, skills_df)
            dummy_target = Character({'Base_HP':999999, 'Base_ATK':0, 'Base_DEF':0}, None) # 샌드백
            
            logs = []
            for t in range(600): # 60초 (0.1s step)
                dmg = char.update_combat(0.1, dummy_target)
                if dmg > 0:
                    logs.append({'Time': t*0.1, 'Damage': dmg})
            
            st.metric("Total Damage (60s)", f"{int(char.total_damage_dealt):,}")
            if logs:
                st.line_chart(pd.DataFrame(logs).set_index('Time')['Damage'].cumsum())

    # =========================================================================
    # TAB 2: 플레이 검증 (던전 난이도 & 생존 비율)
    # =========================================================================
    with tab2:
        st.subheader("PVE Dungeon Difficulty Verification")
        st.markdown("> **검증 로직:** `유저 생존 턴 / 몬스터 생존 턴 = 생존 비율` (높을수록 쉬움)")
        
        # 데이터 로드
        growth_df = data['User_Growth']
        monster_template_df = data['Monster_Template']
        dungeon_df = data['Dungeon_List']
        
        if st.button("🛡️ 전체 던전 검증 실행 (Batch Run)"):
            results = []
            
            for idx, row in dungeon_df.iterrows():
                d_name = row['Dungeon_Name']
                lvl = row['Unlock_Level']
                m_type = row['Monster_Type']
                target_ratio = row['Target_Survival_Ratio']
                
                # 1. 유저 스펙 생성 (보간법)
                user_hp = interpolate_stat(lvl, growth_df, 'Base_HP')
                user_atk = interpolate_stat(lvl, growth_df, 'Base_ATK')
                user_def = interpolate_stat(lvl, growth_df, 'Base_DEF')
                
                # 2. 몬스터 스펙 생성 (템플릿 비율 적용)
                m_template = monster_template_df[monster_template_df['Monster_Type'] == m_type].iloc[0]
                mon_hp = user_hp * m_template['HP_Ratio']
                mon_atk = user_atk * m_template['ATK_Ratio']
                mon_def = user_def * m_template['DEF_Ratio'] # 보통 몬스터 방어력은 유저보다 낮게 설정하지만 여기선 비율대로
                
                # 3. 전투 시뮬레이션 (간이 턴제 계산)
                # 유저 -> 몬스터 데미지
                dmg_to_mon = max(1, user_atk - mon_def)
                turns_to_kill_mon = mon_hp / dmg_to_mon
                
                # 몬스터 -> 유저 데미지
                dmg_to_user = max(1, mon_atk - user_def)
                turns_to_die = user_hp / dmg_to_user
                
                # 4. 생존 비율 계산
                survival_ratio = turns_to_die / turns_to_kill_mon
                
                # 판정
                # 목표 비율보다 크면 쉬움(Pass), 너무 작으면 어려움(Fail/Hard)
                # 여기서는 오차 범위 20% 내외를 적정으로 간주하거나, 단순 크기 비교
                status = "🟢 Pass" if survival_ratio >= target_ratio else "🔴 Fail (Too Hard)"
                if survival_ratio > target_ratio * 1.5: status = "🔵 Too Easy"
                
                results.append({
                    "Dungeon": d_name,
                    "Level": lvl,
                    "User HP": int(user_hp),
                    "Mon HP": int(mon_hp),
                    "User Survive Turn": round(turns_to_die, 1),
                    "Mon Survive Turn": round(turns_to_kill_mon, 1),
                    "Actual Ratio": round(survival_ratio, 2),
                    "Target Ratio": target_ratio,
                    "Result": status
                })
            
            res_df = pd.DataFrame(results)
            st.dataframe(res_df.style.applymap(lambda v: 'color: red;' if 'Fail' in str(v) else ('color: blue;' if 'Easy' in str(v) else None), subset=['Result']), use_container_width=True)
            
            # 시각화
            fig = px.bar(res_df, x='Dungeon', y=['Actual Ratio', 'Target Ratio'], barmode='group',
                         title="생존 비율 검증 결과 (Target vs Actual)")
            fig.add_hline(y=1.0, line_dash="dash", annotation_text="Balance Line (1.0)")
            st.plotly_chart(fig, use_container_width=True)

    # =========================================================================
    # TAB 3: 밸런스 검증 (과금 격차 & 란체스터)
    # =========================================================================
    with tab3:
        st.subheader("Payment Grade Balance & Lanchester's Law")
        
        grade_df = data['Payment_Grade']
        
        # 비교할 레벨 선택
        target_lv = st.slider("검증할 유저 레벨 (Target Level)", 1, 100, 50)
        
        # 기준 스펙 가져오기
        base_hp = interpolate_stat(target_lv, data['User_Growth'], 'Base_HP')
        base_atk = interpolate_stat(target_lv, data['User_Growth'], 'Base_ATK')
        
        if st.button("💰 과금 밸런스 분석 실행"):
            
            bal_results = []
            
            # 1. 등급별 전투력(CP) 계산
            for idx, row in grade_df.iterrows():
                mult = row['Stat_Multiplier']
                cp = (base_atk * mult) * (base_hp * mult) / 100  # 단순 CP 공식 예시
                bal_results.append({
                    "Grade": row['Grade'],
                    "Multiplier": mult,
                    "ATK": int(base_atk * mult),
                    "HP": int(base_hp * mult),
                    "Combat Power (CP)": int(cp)
                })
            
            bal_df = pd.DataFrame(bal_results)
            
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("#### 1. 등급별 스펙 & 전투력")
                st.dataframe(bal_df, use_container_width=True)
            
            with c2:
                st.markdown("#### 2. CP 격차 그래프")
                fig_cp = px.bar(bal_df, x='Grade', y='Combat Power (CP)', color='Grade')
                st.plotly_chart(fig_cp, use_container_width=True)
                
            # 2. 란체스터 법칙 검증 (헤비과금 vs 무과금)
            st.markdown("---")
            st.markdown("#### 3. 란체스터 법칙 (Square Law) 검증")
            st.info("💡 **란체스터 제2법칙:** 소수의 강자(A)가 다수의 약자(B)와 대등하게 싸우려면?  \n`N = sqrt( CP_A / CP_B )` 명의 약자가 필요함.")
            
            # 무과금 vs 헤비과금 추출
            try:
                heavy = bal_df[bal_df['Grade'].str.contains("Heavy")].iloc[0]
                free = bal_df[bal_df['Grade'].str.contains("Free")].iloc[0]
                
                cp_ratio = heavy['Combat Power (CP)'] / free['Combat Power (CP)']
                needed_users = np.sqrt(cp_ratio)
                
                col_l1, col_l2, col_l3 = st.columns(3)
                col_l1.metric("Heavy CP", f"{heavy['Combat Power (CP)']:,}")
                col_l2.metric("Free CP", f"{free['Combat Power (CP)']:,}")
                col_l3.metric("CP Ratio", f"{cp_ratio:.2f}배")
                
                st.success(f"⚔️ **검증 결과:** 헤비과금 유저 1명은 무과금 유저 **약 {needed_users:.2f}명**과 대등한 전투력을 가집니다.")
                
                if needed_users > 5:
                    st.warning("⚠️ **경고:** 격차가 너무 큽니다. (1 vs 5 이상). 소과금/무과금 유저의 박탈감이 우려됩니다.")
                else:
                    st.success("✅ **양호:** 적절한 수준의 우위입니다.")
                    
            except:
                st.error("데이터에 'Free' 또는 'Heavy' 등급이 명확하지 않아 계산 불가.")

