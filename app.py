import streamlit as st
import pandas as pd
import plotly.express as px
from data_manager import load_excel_data, get_growth_stat
from sim_engine import Character
import numpy as np

st.set_page_config(page_title="MMORPG Balance Verification Pro", layout="wide")

# 세션 초기화
if 'growth_result' not in st.session_state: st.session_state.growth_result = None
if 'raid_result' not in st.session_state: st.session_state.raid_result = None

# UI 타이틀
st.title("⚖️ MMORPG Balance Verification System")

# 파일 업로드
uploaded_file = st.sidebar.file_uploader("Upload Data (BalanceSheets.xlsx)", type=['xlsx'])
default_file = "BalanceSheets.xlsx"

data = None
if uploaded_file: data = load_excel_data(uploaded_file)
else: 
    try: data = load_excel_data(default_file)
    except: pass

if data:
    tab1, tab2, tab3, tab4 = st.tabs(["⚔️ 클래스 성장 검증", "🛡️ 레이드 난이도 검증", "💰 과금 밸런스 검증", "📊 데이터 열람"])

    # --- TAB 1: 클래스 성장 ---
    with tab1:
        st.subheader("1. Class Growth & DPS Simulation")
        
        # [수정] 폼(Form) 사용: 화면 튕김 방지
        with st.form("growth_form"):
            c1, c2, c3 = st.columns(3)
            with c1:
                if 'Class_Job' in data:
                    sel_class = st.selectbox("Select Class", data['Class_Job']['Class_Name'].unique())
                else: st.stop()
            with c2: sel_level = st.slider("Level", 1, 60, 60)
            with c3: sel_time = st.slider("Time (sec)", 10, 300, 60)
            
            # 폼 제출 버튼
            submitted = st.form_submit_button("▶️ Run Simulation")
            
            if submitted:
                class_row = data['Class_Job'][data['Class_Job']['Class_Name'] == sel_class].iloc[0]
                player = Character(sel_level, class_row, data['Growth_Table'], data['Skill_Data'])
                
                # 시뮬레이션
                steps = int(sel_time / 0.1)
                for _ in range(steps): player.update(0.1)
                
                target_dps = get_growth_stat(sel_level, data['Growth_Table'], 'Standard_DPS')
                actual_dps = player.total_damage / sel_time
                
                st.session_state.growth_result = {
                    "player": player, "actual": actual_dps, "target": target_dps, "log": player.damage_log
                }

        # 결과 표시 (폼 밖에서)
        if st.session_state.growth_result:
            res = st.session_state.growth_result
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Max HP", f"{int(res['player'].max_hp):,}")
            m2.metric("Attack Power", f"{int(res['player'].atk):,}")
            m3.metric("Actual DPS", f"{int(res['actual']):,}", delta=f"{int(res['actual'] - res['target']):,}")
            m4.metric("Target DPS", f"{int(res['target']):,}")
            
            ratio = res['actual'] / res['target'] if res['target'] > 0 else 0
            if 0.9 <= ratio <= 1.1: st.success(f"✅ Balanced ({ratio*100:.1f}%)")
            elif ratio > 1.1: st.warning(f"⚠️ Over Powered ({ratio:.2f}x) - 기획 의도보다 강함")
            else: st.error(f"⚠️ Under Powered ({ratio:.2f}x) - 기획 의도보다 약함")

            if res['log']:
                log_df = pd.DataFrame(res['log'])
                st.markdown("##### 📈 Damage Log")
                st.line_chart(log_df.set_index('Time')['Cumulative'])
                with st.expander("Detailed Log"): st.dataframe(log_df)

    # --- TAB 2: 레이드 검증 ---
    with tab2:
        st.subheader("2. Raid TTK Verification")
        
        # [수정] 폼(Form) 사용
        with st.form("raid_form"):
            run_raid = st.form_submit_button("🛡️ Run Raid Simulation")
            
            if run_raid:
                if 'Dungeon_Config' not in data: st.error("Dungeon_Config missing"); st.stop()
                
                dungeon_res = []
                for idx, row in data['Dungeon_Config'].iterrows():
                    mob_data = data['Monster_Book'][data['Monster_Book']['Mob_ID'] == row['Boss_Mob_ID']]
                    if mob_data.empty: continue
                    boss_hp = mob_data.iloc[0]['HP']
                    
                    std_dps = get_growth_stat(row['Min_Level'], data['Growth_Table'], 'Standard_DPS')
                    party_dps = std_dps * row['Rec_Party_Size']
                    ttk = boss_hp / party_dps if party_dps > 0 else 999999
                    
                    dungeon_res.append({
                        "Dungeon": row['Dungeon_Name'],
                        "Party": f"{row['Rec_Party_Size']}인",
                        "Boss HP": f"{boss_hp:,}",
                        "TTK (Sec)": int(ttk),
                        "Limit (Sec)": row['Time_Limit_Sec'],
                        "Result": "🟢 Clear" if ttk <= row['Time_Limit_Sec'] else "🔴 Fail"
                    })
                st.session_state.raid_result = pd.DataFrame(dungeon_res)

        if st.session_state.raid_result is not None:
            df = st.session_state.raid_result
            st.dataframe(df, use_container_width=True)
            fig = px.bar(df, x='Dungeon', y=['TTK (Sec)', 'Limit (Sec)'], barmode='group', title="예상 클리어 타임 vs 제한 시간")
            st.plotly_chart(fig, use_container_width=True)

    # --- TAB 3: 과금 밸런스 ---
    with tab3:
        st.subheader("3. Payment & Lanchester Analysis")
        if 'Payment_Grade' not in data:
            st.warning("Payment_Grade 시트가 없습니다.")
        else:
            # [수정] 폼 사용
            with st.form("balance_form"):
                t_lv = st.slider("Target Lv", 1, 60, 50)
                check_bal = st.form_submit_button("💰 Calculate Gap")
                
                if check_bal:
                    base_atk = get_growth_stat(t_lv, data['Growth_Table'], 'Base_Primary_Stat')
                    bal_res = []
                    for idx, row in data['Payment_Grade'].iterrows():
                        mult = row['Stat_Multiplier']
                        cp = base_atk * mult * 100 
                        bal_res.append({"Grade": row['Grade'], "Multiplier": mult, "CP": int(cp)})
                    st.session_state.bal_df = pd.DataFrame(bal_res)

            if 'bal_df' in st.session_state:
                df_b = st.session_state.bal_df
                st.dataframe(df_b, use_container_width=True)
                fig = px.bar(df_b, x='Grade', y='CP', color='Grade', title="전투력 격차")
                st.plotly_chart(fig, use_container_width=True)
                
                try:
                    h_cp = df_b[df_b['Grade'].str.contains("Heavy")]['CP'].values[0]
                    f_cp = df_b[df_b['Grade'].str.contains("Free")]['CP'].values[0]
                    ratio = np.sqrt(h_cp / f_cp)
                    st.success(f"⚔️ 란체스터 법칙: 헤비과금 1명 = 무과금 {ratio:.2f}명과 대등")
                except: pass

    # --- TAB 4 ---
    with tab4:
        st.subheader("4. Loaded Data View")
        sheet = st.selectbox("Select Sheet", list(data.keys()))
        st.dataframe(data[sheet], use_container_width=True)

else:
    st.info("👈 Please upload 'BalanceSheets.xlsx'")
