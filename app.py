import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# 페이지 기본 설정
st.set_page_config(page_title="MMORPG Balance Verification Pro", layout="wide")

# -----------------------------------------------------------------------------
# 1. 데이터 로드 (캐시 무시 및 안전 로드)
# -----------------------------------------------------------------------------
@st.cache_data(ttl=0)
def load_data(uploaded_file):
    try:
        xls = pd.ExcelFile(uploaded_file)
        data_dict = {}
        
        sheet_names = xls.sheet_names
        required = ['Class_Job', 'Growth_Table', 'Skill_Data', 'Monster_Book', 'Dungeon_Config']
        normalized_names = {name.strip(): name for name in sheet_names}
        
        for req_sheet in required:
            if req_sheet in normalized_names:
                real_name = normalized_names[req_sheet]
                df = pd.read_excel(xls, real_name)
                df.columns = df.columns.str.strip()
                data_dict[req_sheet] = df
            else:
                st.error(f"❌ 엑셀 파일에 **'{req_sheet}'** 시트가 없습니다!")
                return None
        return data_dict
    except Exception as e:
        st.error(f"데이터 로드 중 오류 발생: {e}")
        return None

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
# 2. 캐릭터 클래스 (누락된 Cumulative 로직 복구됨)
# -----------------------------------------------------------------------------
class Character:
    def __init__(self, level, class_row, growth_df, skills_df):
        self.level = level
        self.name = class_row['Class_Name']
        self.role = class_row['Role']
        
        base_hp_pool = get_growth_stat(level, growth_df, 'Base_HP')
        base_mp_pool = get_growth_stat(level, growth_df, 'Base_MP')
        base_stat_pool = get_growth_stat(level, growth_df, 'Base_Primary_Stat')
        base_def_pool = get_growth_stat(level, growth_df, 'Base_DEF')
        
        self.max_hp = base_hp_pool * class_row['Base_HP_Mod']
        self.current_hp = self.max_hp
        self.max_mp = base_mp_pool
        self.current_mp = self.max_mp
        
        str_atk = base_stat_pool * class_row['Stat_Weight_Str']
        int_atk = base_stat_pool * class_row['Stat_Weight_Int']
        self.atk = max(str_atk, int_atk)
        
        self.defense = base_def_pool * class_row['Base_Def_Mod']
        
        if skills_df is not None:
            self.skills = skills_df[skills_df['Class_Name'] == self.name].copy()
            self.skills['next_available'] = 0.0
        else:
            self.skills = pd.DataFrame()

        self.current_time = 0.0
        self.is_casting = False
        self.cast_end_time = 0.0
        self.total_damage = 0
        self.damage_log = []

    def update(self, time_step):
        self.current_time += time_step
        
        mp_regen = self.max_mp * 0.05 * time_step
        if self.current_mp < self.max_mp:
            self.current_mp += mp_regen
        
        if self.is_casting:
            if self.current_time >= self.cast_end_time:
                self.is_casting = False
            else:
                return 0

        if not self.skills.empty:
            ready_skills = self.skills[
                (self.skills['next_available'] <= self.current_time) & 
                (self.skills['MP_Cost'] <= self.current_mp)
            ].sort_values(by='Dmg_Percent', ascending=False)
            
            if not ready_skills.empty:
                return self.use_skill(ready_skills.iloc[0])
        
        return self.basic_attack()

    def use_skill(self, skill):
        skill_idx = skill.name
        self.current_mp -= skill['MP_Cost']
        
        damage = self.atk * (skill['Dmg_Percent'] / 100.0)
        self.total_damage += damage
        
        # [복구완료] Cumulative 키 추가 (이게 없어서 에러가 났었습니다)
        self.damage_log.append({
            'Time': round(self.current_time, 2),
            'Type': 'Skill',
            'Name': skill['Skill_Name'],
            'Damage': int(damage),
            'Cumulative': int(self.total_damage), 
            'MP': int(self.current_mp)
        })
        
        self.is_casting = True
        self.cast_end_time = self.current_time + skill['Cast_Time']
        self.skills.at[skill_idx, 'next_available'] = self.current_time + skill['Cooldown']
        
        return damage

    def basic_attack(self):
        if int(self.current_time * 10) % 10 == 0: 
            damage = self.atk
            self.total_damage += damage
            
            # [복구완료] Cumulative 키 추가
            self.damage_log.append({
                'Time': round(self.current_time, 2),
                'Type': 'Attack',
                'Name': 'Basic Attack',
                'Damage': int(damage),
                'Cumulative': int(self.total_damage),
                'MP': int(self.current_mp)
            })
            return damage
        return 0

# -----------------------------------------------------------------------------
# 3. 메인 UI
# -----------------------------------------------------------------------------
st.title("⚖️ MMORPG Balance Verification System (Pro)")

uploaded_file = st.sidebar.file_uploader("Upload Data (BalanceSheets.xlsx)", type=['xlsx'])
default_file = "BalanceSheets.xlsx"

data = None
if uploaded_file: data = load_data(uploaded_file)
else: 
    try: data = load_data(default_file)
    except: pass

if data:
    tab1, tab2, tab3 = st.tabs(["⚔️ 클래스 성장 검증", "🛡️ 레이드 난이도 검증", "📊 데이터 열람"])

    # === TAB 1: 클래스 성장 검증 ===
    with tab1:
        st.subheader("1. Class Growth & DPS Simulation")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            if 'Class_Job' in data:
                selected_class_name = st.selectbox("Select Class", data['Class_Job']['Class_Name'].unique())
            else:
                st.error("Class_Job 데이터가 없습니다.")
                st.stop()
        with col2:
            target_level = st.slider("Target Level", 1, 60, 60)
        with col3:
            sim_duration = st.slider("Combat Time (sec)", 10, 300, 60)
            
        if st.button("▶️ Run Growth Simulation"):
            class_row = data['Class_Job'][data['Class_Job']['Class_Name'] == selected_class_name].iloc[0]
            player = Character(target_level, class_row, data['Growth_Table'], data['Skill_Data'])
            
            with st.spinner("Simulating combat..."):
                steps = int(sim_duration / 0.1)
                for _ in range(steps):
                    player.update(0.1)
            
            dps = player.total_damage / sim_duration
            standard_dps = get_growth_stat(target_level, data['Growth_Table'], 'Standard_DPS')
            
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Max HP", f"{int(player.max_hp):,}")
            m2.metric("Attack Power", f"{int(player.atk):,}")
            m3.metric("Actual DPS", f"{int(dps):,}", delta=f"{int(dps - standard_dps):,}")
            m4.metric("Target DPS", f"{int(standard_dps):,}")
            
            ratio = dps / standard_dps
            if 0.9 <= ratio <= 1.1:
                st.success(f"✅ **Perfect Balance:** 기획 의도와 일치합니다. ({ratio*100:.1f}%)")
            elif ratio > 1.1:
                st.warning(f"⚠️ **Over Powered:** 기획 의도보다 {ratio:.2f}배 강력합니다.")
            else:
                st.error(f"⚠️ **Under Powered:** 기획 의도보다 약합니다. ({ratio:.2f}배).")

            if player.damage_log:
                log_df = pd.DataFrame(player.damage_log)
                st.markdown("##### 📈 Damage Log")
                
                # [에러 해결됨] 이제 'Cumulative' 컬럼이 있으므로 에러가 나지 않습니다.
                st.line_chart(log_df.set_index('Time')['Cumulative'])
                
                with st.expander("상세 로그 보기"):
                    st.dataframe(log_df)

    # =========================================================================
    # TAB 2: 레이드 난이도 검증 (화면 튕김 방지 Fix)
    # =========================================================================
    with tab2:
        st.subheader("2. Raid & Dungeon TTK Analysis")
        st.markdown("**검증 목표:** 파티 규모와 유저 스펙을 고려할 때, 보스를 제한 시간 내에 잡을 수 있는가?")
        
        # [수정] 폼(Form)을 사용하여 버튼 클릭 시 리로드 방지
        with st.form("raid_form"):
            run_raid = st.form_submit_button("🛡️ Run Raid Simulation")
            
            if run_raid:
                if 'Dungeon_Config' not in data:
                    st.error("Dungeon_Config 시트가 없습니다.")
                else:
                    dungeon_res = []
                    for idx, row in data['Dungeon_Config'].iterrows():
                        d_name = row['Dungeon_Name']
                        boss_id = row['Boss_Mob_ID']
                        min_lv = row['Min_Level']
                        party_size = row['Rec_Party_Size']
                        time_limit = row['Time_Limit_Sec']
                        
                        # 몬스터 정보
                        mob_row = data['Monster_Book'][data['Monster_Book']['Mob_ID'] == boss_id].iloc[0]
                        boss_hp = mob_row['HP']
                        
                        # 유저 스펙
                        std_dps = get_growth_stat(min_lv, data['Growth_Table'], 'Standard_DPS')
                        party_dps = std_dps * party_size
                        
                        # TTK 계산
                        ttk_sec = boss_hp / party_dps
                        
                        status = "🟢 Clear" if ttk_sec <= time_limit else "🔴 Fail"
                        
                        dungeon_res.append({
                            "Dungeon": d_name,
                            "Lv": min_lv,
                            "Party": f"{party_size}인",
                            "Boss HP": f"{boss_hp:,}",
                            "TTK (Sec)": int(ttk_sec),
                            "Limit (Sec)": time_limit,
                            "Result": status
                        })
                        
                    res_df = pd.DataFrame(dungeon_res)
                    st.dataframe(res_df, use_container_width=True)
                    
                    fig = px.bar(res_df, x='Dungeon', y=['TTK (Sec)', 'Limit (Sec)'], barmode='group', title="예상 클리어 타임 비교")
                    st.plotly_chart(fig, use_container_width=True)

    # === TAB 3: 데이터 열람 ===
    with tab3:
        st.subheader("3. Loaded Balance Data")
        sheet_names = list(data.keys())
        selected_sheet = st.selectbox("Select Sheet", sheet_names)
        st.dataframe(data[selected_sheet], use_container_width=True)

else:
    st.warning("👈 왼쪽 사이드바에서 'BalanceSheets.xlsx' 파일을 업로드해주세요.")
