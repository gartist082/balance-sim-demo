import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# 페이지 기본 설정
st.set_page_config(page_title="MMORPG Balance Verification Pro", layout="wide")

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

# 레벨에 따른 스탯 보간 함수
def get_growth_stat(level, growth_df, target_col):
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
# 2. 캐릭터 클래스 (데이터 구조 반영)
# -----------------------------------------------------------------------------
class Character:
    def __init__(self, level, class_row, growth_df, skills_df):
        self.level = level
        self.name = class_row['Class_Name']
        self.role = class_row['Role']
        
        # 1. 기초 스탯 가져오기 (Growth Table)
        base_hp_pool = get_growth_stat(level, growth_df, 'Base_HP')
        base_mp_pool = get_growth_stat(level, growth_df, 'Base_MP')
        base_stat_pool = get_growth_stat(level, growth_df, 'Base_Primary_Stat')
        base_def_pool = get_growth_stat(level, growth_df, 'Base_DEF')
        
        # 2. 직업별 가중치 적용 (Class Job)
        # HP = 기초체력 * 직업보정
        self.max_hp = base_hp_pool * class_row['Base_HP_Mod']
        self.current_hp = self.max_hp
        
        self.max_mp = base_mp_pool
        self.current_mp = self.max_mp
        
        # 공격력 = (힘 가중치 * 스탯) + (지능 가중치 * 스탯)
        # 전사는 힘, 법사는 지능을 쓴다고 가정 (둘 중 하나만 적용됨)
        str_atk = base_stat_pool * class_row['Stat_Weight_Str']
        int_atk = base_stat_pool * class_row['Stat_Weight_Int']
        self.atk = max(str_atk, int_atk) # 둘 중 높은 것을 공격력으로 사용
        
        self.defense = base_def_pool * class_row['Base_Def_Mod']
        
        # 3. 스킬 세팅
        if skills_df is not None:
            self.skills = skills_df[skills_df['Class_Name'] == self.name].copy()
            self.skills['next_available'] = 0.0
        else:
            self.skills = pd.DataFrame()

        # 시뮬레이션 상태 변수
        self.current_time = 0.0
        self.is_casting = False
        self.cast_end_time = 0.0
        self.total_damage = 0
        self.damage_log = []

    def update(self, time_step):
        self.current_time += time_step
        
        # MP 회복 (초당 5% 가정)
        mp_regen = self.max_mp * 0.05 * time_step
        if self.current_mp < self.max_mp:
            self.current_mp += mp_regen
        
        # 캐스팅 중 체크
        if self.is_casting:
            if self.current_time >= self.cast_end_time:
                self.is_casting = False
            else:
                return 0

        # 스킬 사용 시도
        if not self.skills.empty:
            # 쿨타임 왔고 & 마나 충분한 스킬 중 '가장 강한 것(Dmg_Percent)' 우선 사용
            ready_skills = self.skills[
                (self.skills['next_available'] <= self.current_time) & 
                (self.skills['MP_Cost'] <= self.current_mp)
            ].sort_values(by='Dmg_Percent', ascending=False)
            
            if not ready_skills.empty:
                return self.use_skill(ready_skills.iloc[0])
        
        # 스킬 없으면 평타 (공격력의 100%, 1초 쿨타임 가정)
        return self.basic_attack()

    def use_skill(self, skill):
        skill_idx = skill.name
        self.current_mp -= skill['MP_Cost']
        
        # 데미지 계산: 공격력 * (계수/100)
        # 타수(Hit_Count)는 로그에는 남기되, 총 데미지는 합산해서 처리
        damage = self.atk * (skill['Dmg_Percent'] / 100.0)
        
        self.total_damage += damage
        self.damage_log.append({
            'Time': round(self.current_time, 2),
            'Type': 'Skill',
            'Name': skill['Skill_Name'],
            'Damage': int(damage),
            'MP': int(self.current_mp)
        })
        
        # 쿨타임 & 캐스팅 적용
        self.is_casting = True
        self.cast_end_time = self.current_time + skill['Cast_Time']
        self.skills.at[skill_idx, 'next_available'] = self.current_time + skill['Cooldown']
        
        return damage

    def basic_attack(self):
        damage = self.atk # 평타 계수 1.0 가정
        self.total_damage += damage
        # 평타는 로그를 너무 많이 남기지 않기 위해 생략하거나 간소화 가능
        # 여기서는 1초에 1번씩만 때린다고 가정 (Attack Speed 구현 대신 간소화)
        return damage

# -----------------------------------------------------------------------------
# 3. 메인 UI
# -----------------------------------------------------------------------------
st.title("⚖️ MMORPG Balance Verification System (Pro)")
st.markdown("""
**System Overview:**
* **Class & Job:** 직업별 역할(Tank/Deal/Heal)과 스탯 가중치 반영
* **Growth Curve:** 레벨별 지수 성장(Exponential Growth) 데이터 연동
* **Raid Sim:** 파티 규모와 보스 스펙을 고려한 클리어 타임(TTK) 검증
""")

uploaded_file = st.sidebar.file_uploader("Upload Data (BalanceSheets.xlsx)", type=['xlsx'])
default_file = "BalanceSheets.xlsx"

data = None
if uploaded_file: data = load_data(uploaded_file)
else: 
    try: data = load_data(default_file)
    except: pass

if data:
    tab1, tab2, tab3 = st.tabs(["⚔️ 클래스 성장 검증", "🛡️ 레이드 난이도 검증", "📊 데이터 열람"])

    # =========================================================================
    # TAB 1: 클래스 성장 검증 (Growth Verification)
    # =========================================================================
    with tab1:
        st.subheader("1. Class Growth & DPS Simulation")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            selected_class_name = st.selectbox("Select Class", data['Class_Job']['Class_Name'].unique())
        with col2:
            target_level = st.slider("Target Level", 1, 60, 60)
        with col3:
            sim_duration = st.slider("Combat Time (sec)", 10, 300, 60)
            
        if st.button("▶️ Run Growth Simulation"):
            # 데이터 추출
            class_row = data['Class_Job'][data['Class_Job']['Class_Name'] == selected_class_name].iloc[0]
            
            # 캐릭터 생성 & 시뮬레이션
            player = Character(target_level, class_row, data['Growth_Table'], data['Skill_Data'])
            
            # 시뮬레이션 루프
            with st.spinner("Simulating combat..."):
                steps = int(sim_duration / 0.1) # 0.1초 단위
                for _ in range(steps):
                    player.update(0.1)
            
            # 결과 분석
            dps = player.total_damage / sim_duration
            standard_dps = get_growth_stat(target_level, data['Growth_Table'], 'Standard_DPS')
            
            # 1. 핵심 지표
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Lv. Stats", f"HP {int(player.max_hp):,}")
            m2.metric("Attack Power", f"{int(player.atk):,}")
            m3.metric("Actual DPS", f"{int(dps):,}", delta=f"{int(dps - standard_dps):,}")
            m4.metric("Target DPS", f"{int(standard_dps):,}")
            
            # 2. 밸런스 코멘트
            ratio = dps / standard_dps
            if 0.9 <= ratio <= 1.1:
                st.success(f"✅ **Perfect Balance:** 기획 의도(Standard DPS)와 거의 일치합니다. ({ratio*100:.1f}%)")
            elif ratio > 1.1:
                st.warning(f"⚠️ **Over Powered:** 기획 의도보다 {ratio:.2f}배 강력합니다. 너프가 필요할 수 있습니다.")
            else:
                st.error(f"⚠️ **Under Powered:** 기획 의도보다 약합니다. ({ratio:.2f}배). 버프가 필요합니다.")
                
            # 3. 로그 차트
            if player.damage_log:
                log_df = pd.DataFrame(player.damage_log)
                st.markdown("##### 📈 Damage Log (Skill Usage)")
                
                # 스킬별 데미지 비중 파이차트 & 시간별 그래프
                c1, c2 = st.columns([1, 2])
                with c1:
                    skill_sum = log_df.groupby('Name')['Damage'].sum().reset_index()
                    fig_pie = px.pie(skill_sum, values='Damage', names='Name', title='Skill Contribution')
                    st.plotly_chart(fig_pie, use_container_width=True)
                with c2:
                    st.line_chart(log_df.set_index('Time')['Damage'].cumsum())

    # =========================================================================
    # TAB 2: 레이드 난이도 검증 (Raid TTK Verification)
    # =========================================================================
    with tab2:
        st.subheader("2. Raid & Dungeon TTK (Time To Kill) Analysis")
        st.markdown("**검증 목표:** 파티 규모와 유저 스펙을 고려할 때, 보스를 제한 시간 내에 잡을 수 있는가?")
        
        if st.button("🛡️ Run Raid Simulation"):
            dungeon_res = []
            
            for idx, row in data['Dungeon_Config'].iterrows():
                d_name = row['Dungeon_Name']
                boss_id = row['Boss_Mob_ID']
                min_lv = row['Min_Level']
                party_size = row['Rec_Party_Size']
                time_limit = row['Time_Limit_Sec']
                
                # 1. 몬스터 정보 가져오기
                mob_row = data['Monster_Book'][data['Monster_Book']['Mob_ID'] == boss_id].iloc[0]
                boss_hp = mob_row['HP']
                
                # 2. 유저 평균 DPS 가져오기 (Growth Table의 Standard_DPS 사용)
                # 실제로는 직업별 시뮬레이션을 돌려야 하지만, 여기선 '표준 DPS'를 기준으로 잡음 (검증의 기준점)
                std_dps = get_growth_stat(min_lv, data['Growth_Table'], 'Standard_DPS')
                
                # 3. 파티 전체 DPS (단순 합산)
                # 실제로는 시너지 효과(1.2배 등)를 넣을 수 있음
                party_dps = std_dps * party_size
                
                # 4. 예상 클리어 시간 (TTK)
                ttk_sec = boss_hp / party_dps
                
                # 5. 판정
                is_clear = ttk_sec <= time_limit
                gap_sec = time_limit - ttk_sec
                
                status = "🟢 Clear" if is_clear else "🔴 Fail (Time Over)"
                
                dungeon_res.append({
                    "Dungeon": d_name,
                    "Lv": min_lv,
                    "Party": f"{party_size}인",
                    "Boss HP": f"{boss_hp:,}",
                    "Party DPS": f"{int(party_dps):,}",
                    "TTK (Sec)": int(ttk_sec),
                    "Limit (Sec)": time_limit,
                    "Result": status,
                    "Gap": int(gap_sec)
                })
                
            res_df = pd.DataFrame(dungeon_res)
            st.dataframe(res_df, use_container_width=True)
            
            # 그래프: TTK vs Limit 비교
            fig = px.bar(res_df, x='Dungeon', y=['TTK (Sec)', 'Limit (Sec)'], barmode='group',
                         title="던전별 클리어 타임 예측 (Target vs Actual)")
            # 제한 시간 선 긋기 (가변적이라 어려움, 바 차트로 대체)
            st.plotly_chart(fig, use_container_width=True)
            
            st.info("""
            **💡 분석 가이드:**
            * **TTK (Time To Kill):** 파티원들이 쉼 없이 딜을 넣었을 때 보스가 죽는 시간입니다.
            * **Fail 원인 분석:** TTK가 Limit보다 길다면, **보스 체력이 너무 많거나** 유저들의 **표준 DPS(Standard DPS)가 너무 낮게 설정**된 것입니다.
            * **Gap:** 남은 시간입니다. 너무 많이 남으면(예: 300초 제한인데 50초 컷) 콘텐츠가 너무 쉬운 것입니다.
            """)

    # =========================================================================
    # TAB 3: 데이터 열람 (Raw Data)
    # =========================================================================
    with tab3:
        st.subheader("3. Loaded Balance Data")
        st.caption("현재 로드된 엑셀 데이터의 원본입니다.")
        
        sheet_names = data.keys()
        selected_sheet = st.selectbox("Select Sheet", sheet_names)
        st.dataframe(data[selected_sheet], use_container_width=True)
