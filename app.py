import streamlit as st
import pandas as pd
import plotly.express as px
from data_manager import load_excel_data, get_growth_stat
from sim_engine import Character
import numpy as np

st.set_page_config(page_title="MMORPG Balance Verification Pro", layout="wide")
PLOT_CONFIG = {'displayModeBar': False, 'staticPlot': True}

# -----------------------------------------------------------------------------
# [핵심 수정] 세션 상태 초기화 (탭 유지 & 데이터 유지)
# -----------------------------------------------------------------------------
if 'growth_res' not in st.session_state: st.session_state.growth_res = None
if 'monte_res' not in st.session_state: st.session_state.monte_res = None
if 'raid_res' not in st.session_state: st.session_state.raid_res = None
# 탭 상태 저장은 Streamlit 구버전에서는 어려우나, 데이터 유지를 통해 UX 개선

st.title("⚖️ MMORPG Balance Verification System")

uploaded_file = st.sidebar.file_uploader("Upload Data (BalanceSheets.xlsx)", type=['xlsx'])
default_file = "BalanceSheets.xlsx"

data = None
if uploaded_file: data = load_excel_data(uploaded_file)
else: 
    try: data = load_excel_data(default_file)
    except: pass

if data:
    # 탭 구성
    tab1, tab2, tab3, tab4 = st.tabs(["1. 클래스 성장/전투 검증", "2. 레이드 난이도 검증", "3. 과금 밸런스 검증", "4. 데이터 열람"])

    # =========================================================================
    # TAB 1: 클래스 성장 & 전투
    # =========================================================================
    with tab1:
        st.subheader("1. Class Growth & Combat Simulation")
        
        # A/B 테스트 패널
        with st.expander("⚙️ 시뮬레이션 설정 및 튜닝 (A/B Testing)", expanded=True):
            c1, c2, c3 = st.columns(3)
            with c1:
                if 'Class_Job' in data:
                    # key를 지정하여 리로드 시 값 유지
                    sel_class = st.selectbox("직업 선택", data['Class_Job']['Class_Name'].unique(), key="t1_class")
                else: st.stop()
            with c2: sel_level = st.slider("테스트 레벨", 1, 60, 60, key="t1_level")
            with c3: sel_time = st.slider("전투 시간 (초)", 10, 300, 60, key="t1_time")
            
            st.markdown("---")
            t_col1, t_col2 = st.columns(2)
            with t_col1:
                adj_atk_pct = st.number_input("공격력 보정 (%)", value=100, step=10, key="t1_atk")
            with t_col2:
                adj_crit_bonus = st.slider("치명타 확률 추가 (%)", 0, 50, 0, key="t1_crit")

        col_b1, col_b2 = st.columns(2)
        with col_b1:
            # 폼 대신 일반 버튼 사용 (탭 튕김 방지를 위해 키 분리)
            btn_single = st.button("▶️ 단일 전투 실행 (로그 분석)", key="btn_single")
        with col_b2:
            btn_monte = st.button("🎲 몬테카를로 실행 (편차 확인)", key="btn_monte")

        class_row = data['Class_Job'][data['Class_Job']['Class_Name'] == sel_class].iloc[0]
        target_dps = get_growth_stat(sel_level, data['Growth_Table'], 'Standard_DPS')

        if btn_single:
            player = Character(sel_level, class_row, data['Growth_Table'], data['Skill_Data'])
            player.atk = player.atk * (adj_atk_pct / 100.0)
            player.crit_rate += (adj_crit_bonus / 100.0)
            
            steps = int(sel_time / 0.1)
            for _ in range(steps): player.update(0.1)
            
            st.session_state.growth_res = {
                "type": "single", "player": player, "time": sel_time, "target": target_dps
            }
            st.session_state.monte_res = None

        if btn_monte:
            results = []
            progress_bar = st.progress(0)
            for i in range(20):
                p = Character(sel_level, class_row, data['Growth_Table'], data['Skill_Data'])
                p.atk = p.atk * (adj_atk_pct / 100.0)
                p.crit_rate += (adj_crit_bonus / 100.0)
                for _ in range(int(sel_time / 0.1)): p.update(0.1)
                results.append(p.total_damage / sel_time)
                progress_bar.progress((i + 1) / 20)
            
            st.session_state.monte_res = {"data": results, "target": target_dps}
            st.session_state.growth_res = None

        # 결과 표시 (데이터가 존재할 경우)
        if st.session_state.growth_res:
            res = st.session_state.growth_res
            ratio = (res['player'].total_damage / res['time']) / res['target'] if res['target'] > 0 else 0
            
            st.divider()
            m1, m2, m3 = st.columns(3)
            m1.metric("실제 DPS", f"{int(res['player'].total_damage / res['time']):,}")
            m2.metric("목표 DPS", f"{int(res['target']):,}")
            m3.metric("달성률", f"{ratio*100:.1f}%")
            
            if res['player'].damage_log:
                log_df = pd.DataFrame(res['player'].damage_log)
                st.line_chart(log_df.set_index('Time')['Cumulative'])
                with st.expander("상세 로그"): st.dataframe(log_df)

        if st.session_state.monte_res:
            data_list = st.session_state.monte_res['data']
            avg = np.mean(data_list)
            st.divider()
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("평균 DPS", f"{int(avg):,}")
            c2.metric("최소", f"{int(np.min(data_list)):,}")
            c3.metric("최대", f"{int(np.max(data_list)):,}")
            c4.metric("표준편차", f"{int(np.std(data_list)):,}")
            
            fig = px.histogram(data_list, nbins=10, title="DPS 분포")
            fig.add_vline(x=avg, line_dash="dash", line_color="red")
            st.plotly_chart(fig, use_container_width=True, config=PLOT_CONFIG)

    # =========================================================================
    # TAB 2: 레이드 난이도 검증 (수정됨)
    # =========================================================================
    with tab2:
        st.subheader("2. Raid & Dungeon TTK Analysis")
        
        with st.expander("⚙️ 조건 설정", expanded=True):
            # [수정] 용어 변경 및 범위 표시
            party_spec_ratio = st.slider(
                "파티원 평균 전투력 비율 (Party Avg CP Ratio)", 
                min_value=50, max_value=150, value=100, step=10, format="%d%%",
                key="t2_slider" # 키 지정으로 탭 튕김 방지
            )
            st.caption(f"설정 범위: 최소 50% (저스펙) ~ 최대 150% (고스펙)")

        # [수정] 폼 제거하고 일반 버튼 사용 (키 지정 필수)
        if st.button("🛡️ 레이드 검증 실행", key="btn_raid"):
            if 'Dungeon_Config' not in data: st.error("Dungeon_Config 없음"); st.stop()
            
            dungeon_res = []
            for idx, row in data['Dungeon_Config'].iterrows():
                mob = data['Monster_Book'][data['Monster_Book']['Mob_ID'] == row['Boss_Mob_ID']].iloc[0]
                std_dps = get_growth_stat(row['Min_Level'], data['Growth_Table'], 'Standard_DPS')
                
                final_party_dps = std_dps * row['Rec_Party_Size'] * (party_spec_ratio / 100.0)
                ttk = mob['HP'] / final_party_dps if final_party_dps > 0 else 999999
                limit = row['Time_Limit_Sec']
                
                status = "🟢 Clear" if ttk <= limit else "🔴 Fail"
                dungeon_res.append({
                    "던전명": row['Dungeon_Name'],
                    "권장Lv": int(row['Min_Level']),
                    "보스체력": f"{mob['HP']:,}",
                    "예상소요": int(ttk),
                    "제한시간": limit,
                    "판정": status
                })
            
            st.session_state.raid_res = pd.DataFrame(dungeon_res)

        if st.session_state.raid_res is not None:
            df = st.session_state.raid_res
            st.markdown("##### 📊 검증 결과 리포트")
            st.dataframe(df, use_container_width=True)
            
            fig = px.bar(df, x='던전명', y=['예상소요', '제한시간'], barmode='group', config=PLOT_CONFIG)
            st.plotly_chart(fig, use_container_width=True)

    # =========================================================================
    # TAB 3: 과금 밸런스 검증
    # =========================================================================
    with tab3:
        st.subheader("3. Payment & Lanchester Analysis")
        
        if 'Payment_Grade' not in data:
            st.error("❌ 'Payment_Grade' 시트가 없습니다.")
        else:
            t_lv = st.slider("비교할 레벨", 1, 60, 60, key="t3_slider")
            
            if st.button("💰 밸런스 분석 실행", key="btn_balance"):
                base_atk = get_growth_stat(t_lv, data['Growth_Table'], 'Base_Primary_Stat')
                bal_res = []
                for idx, row in data['Payment_Grade'].iterrows():
                    mult = row['Stat_Multiplier']
                    cp = base_atk * mult * 100 
                    bal_res.append({"Grade": row['Grade'], "Multiplier": mult, "Combat Power": int(cp)})
                st.session_state.bal_df = pd.DataFrame(bal_res)

            if 'bal_df' in st.session_state:
                df_b = st.session_state.bal_df
                c1, c2 = st.columns(2)
                with c1: st.dataframe(df_b, use_container_width=True)
                with c2:
                    fig = px.bar(df_b, x='Grade', y='Combat Power', color='Grade', title="전투력 격차")
                    st.plotly_chart(fig, use_container_width=True, config=PLOT_CONFIG)
                
                try:
                    h_cp = df_b[df_b['Grade'].str.contains("Heavy", case=False)]['Combat Power'].values[0]
                    f_cp = df_b[df_b['Grade'].str.contains("Free", case=False)]['Combat Power'].values[0]
                    ratio = np.sqrt(h_cp / f_cp)
                    st.info(f"⚔️ **란체스터 분석:** 헤비과금 1명은 무과금 {ratio:.2f}명과 대등합니다.")
                except: pass

    # =========================================================================
    # TAB 4: 데이터 열람
    # =========================================================================
    with tab4:
        st.subheader("4. Loaded Balance Data")
        sheet_names = list(data.keys())
        if sheet_names:
            selected_sheet = st.selectbox("시트 선택", sheet_names, key="t4_select")
            st.dataframe(data[selected_sheet], use_container_width=True)
        else:
            st.warning("데이터가 없습니다.")

else:
    st.info("👈 Please upload 'BalanceSheets.xlsx'")
