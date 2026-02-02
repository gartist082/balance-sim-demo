import streamlit as st
import pandas as pd
import plotly.express as px
from data_manager import load_excel_data, get_growth_stat
from sim_engine import Character
import numpy as np

st.set_page_config(page_title="MMORPG Balance Verification Pro", layout="wide")
PLOT_CONFIG = {'displayModeBar': False, 'staticPlot': True}

# 세션 초기화
if 'growth_res' not in st.session_state: st.session_state.growth_res = None
if 'monte_res' not in st.session_state: st.session_state.monte_res = None
if 'raid_res' not in st.session_state: st.session_state.raid_res = None

st.title("⚖️ MMORPG Balance Verification System")

uploaded_file = st.sidebar.file_uploader("Upload Data (BalanceSheets.xlsx)", type=['xlsx'])
default_file = "BalanceSheets.xlsx"

data = None
if uploaded_file: data = load_excel_data(uploaded_file)
else: 
    try: data = load_excel_data(default_file)
    except: pass

if data:
    tab1, tab2, tab3, tab4 = st.tabs(["1. 클래스 성장/전투 검증", "2. 레이드 난이도 검증", "3. 과금 밸런스 검증", "4. 데이터 열람"])

    # --------------------------------------------------------------------------------
    # TAB 1: 클래스 성장 & 전투 (A/B 테스트 및 로그 복구)
    # --------------------------------------------------------------------------------
    with tab1:
        st.subheader("1. Class Growth & Combat Simulation")
        
        # [복구] A/B 테스트를 위한 설정 패널
        with st.expander("⚙️ 시뮬레이션 설정 및 튜닝 (A/B Testing)", expanded=True):
            c1, c2, c3 = st.columns(3)
            with c1:
                if 'Class_Job' in data:
                    sel_class = st.selectbox("직업 선택", data['Class_Job']['Class_Name'].unique())
                else: st.stop()
            with c2: sel_level = st.slider("테스트 레벨", 1, 60, 60)
            with c3: sel_time = st.slider("전투 시간 (초)", 10, 300, 60)
            
            # 튜닝 옵션
            st.markdown("---")
            st.caption("👇 **스탯 튜닝 (Tuning):** 값을 변경하여 밸런스 변화를 예측해보세요.")
            t_col1, t_col2 = st.columns(2)
            with t_col1:
                adj_atk_pct = st.number_input("공격력 보정 (%)", value=100, step=10, help="기본 공격력의 N%")
            with t_col2:
                adj_crit_bonus = st.slider("치명타 확률 추가 (%)", 0, 50, 0)

        # 실행 버튼
        col_b1, col_b2 = st.columns(2)
        with col_b1:
            btn_single = st.button("▶️ 단일 전투 실행 (로그 분석)", type="primary")
        with col_b2:
            btn_monte = st.button("🎲 몬테카를로 실행 (편차 확인)")

        # 데이터 준비
        class_row = data['Class_Job'][data['Class_Job']['Class_Name'] == sel_class].iloc[0]
        target_dps = get_growth_stat(sel_level, data['Growth_Table'], 'Standard_DPS')

        # [1] 단일 전투 로직
        if btn_single:
            player = Character(sel_level, class_row, data['Growth_Table'], data['Skill_Data'])
            
            # A/B 테스트 적용 (공격력 보정 / 치명타 보정)
            player.atk = player.atk * (adj_atk_pct / 100.0)
            player.crit_rate += (adj_crit_bonus / 100.0)
            
            steps = int(sel_time / 0.1)
            for _ in range(steps): player.update(0.1)
            
            actual_dps = player.total_damage / sel_time
            
            # 결과 저장
            st.session_state.growth_res = {
                "player": player, "actual": actual_dps, "target": target_dps, "log": player.damage_log
            }
            st.session_state.monte_res = None # 화면 정리

        # [2] 몬테카를로 로직
        if btn_monte:
            results = []
            progress_bar = st.progress(0)
            for i in range(20): # 20회
                p = Character(sel_level, class_row, data['Growth_Table'], data['Skill_Data'])
                # A/B 테스트 적용
                p.atk = p.atk * (adj_atk_pct / 100.0)
                p.crit_rate += (adj_crit_bonus / 100.0)
                
                for _ in range(int(sel_time / 0.1)): p.update(0.1)
                results.append(p.total_damage / sel_time)
                progress_bar.progress((i + 1) / 20)
            
            st.session_state.monte_res = {"data": results, "target": target_dps}
            st.session_state.growth_res = None

        # === 결과 화면 출력 ===
        
        # (A) 단일 전투 결과
        if st.session_state.growth_res:
            res = st.session_state.growth_res
            ratio = res['actual'] / res['target'] if res['target'] > 0 else 0
            
            st.divider()
            m1, m2, m3 = st.columns(3)
            m1.metric("실제 DPS", f"{int(res['actual']):,}")
            m2.metric("목표 DPS", f"{int(res['target']):,}")
            m3.metric("달성률", f"{ratio*100:.1f}%")
            
            # [복구] 상세 로그 그래프
            if res['log']:
                log_df = pd.DataFrame(res['log'])
                st.markdown("##### 📈 시간대별 누적 데미지")
                st.line_chart(log_df.set_index('Time')['Cumulative'])
                
                with st.expander("🔎 상세 스킬 사용 로그 (Dataframe)"):
                    st.dataframe(log_df, use_container_width=True)
            else:
                st.warning("⚠️ 데미지 로그가 없습니다.")

        # (B) 몬테카를로 결과
        if st.session_state.monte_res:
            data_list = st.session_state.monte_res['data']
            avg = np.mean(data_list)
            min_v = np.min(data_list)
            max_v = np.max(data_list)
            std = np.std(data_list)
            
            st.divider()
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("평균 DPS", f"{int(avg):,}")
            c2.metric("최소", f"{int(min_v):,}")
            c3.metric("최대", f"{int(max_v):,}")
            c4.metric("표준편차", f"{int(std):,}")
            
            fig = px.histogram(data_list, nbins=10, title="DPS 분포도")
            fig.add_vline(x=avg, line_dash="dash", line_color="red")
            st.plotly_chart(fig, use_container_width=True, config=PLOT_CONFIG)

    # --------------------------------------------------------------------------------
    # TAB 2: 레이드 검증
    # --------------------------------------------------------------------------------
    with tab2:
        st.subheader("2. Raid & Dungeon TTK Analysis")
        
        with st.expander("⚙️ 조건 설정", expanded=True):
            party_spec_ratio = st.slider("파티원 스펙 비율", 50, 150, 100, format="%d%%")
            st.caption("100%=정상, 80%=미숙, 120%=고스펙")

        if st.button("🛡️ 레이드 검증 실행"):
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
            st.dataframe(df, use_container_width=True)
            fig = px.bar(df, x='던전명', y=['예상소요', '제한시간'], barmode='group')
            st.plotly_chart(fig, use_container_width=True, config=PLOT_CONFIG)

    # --------------------------------------------------------------------------------
    # TAB 3: 밸런스 검증
    # --------------------------------------------------------------------------------
    with tab3:
        st.subheader("3. Payment & Lanchester Analysis")
        
        if 'Payment_Grade' not in data:
            st.error("❌ 'Payment_Grade' 시트가 없습니다.")
        else:
            t_lv = st.slider("비교할 레벨", 1, 60, 60)
            
            if st.button("💰 밸런스 분석 실행"):
                base_atk = get_growth_stat(t_lv, data['Growth_Table'], 'Base_Primary_Stat')
                bal_res = []
                for idx, row in data['Payment_Grade'].iterrows():
                    mult = row['Stat_Multiplier']
                    cp = base_atk * mult * 100 
                    bal_res.append({"Grade": row['Grade'], "CP": int(cp)})
                
                df_b = pd.DataFrame(bal_res)
                
                c1, c2 = st.columns(2)
                with c1: st.dataframe(df_b, use_container_width=True)
                with c2:
                    fig = px.bar(df_b, x='Grade', y='CP', color='Grade', title="전투력 격차")
                    st.plotly_chart(fig, use_container_width=True, config=PLOT_CONFIG)
                
                try:
                    h_cp = df_b[df_b['Grade'].str.contains("Heavy")]['CP'].values[0]
                    f_cp = df_b[df_b['Grade'].str.contains("Free")]['CP'].values[0]
                    ratio = np.sqrt(h_cp / f_cp)
                    st.info(f"⚔️ **란체스터 분석:** 헤비과금 1명은 무과금 {ratio:.2f}명과 대등합니다.")
                except: pass

    # --------------------------------------------------------------------------------
    # TAB 4: 데이터 열람
    # --------------------------------------------------------------------------------
    with tab4:
        st.subheader("4. Loaded Balance Data")
        sheet_names = list(data.keys())
        if sheet_names:
            selected_sheet = st.selectbox("시트 선택", sheet_names)
            st.dataframe(data[selected_sheet], use_container_width=True)
        else:
            st.warning("데이터가 없습니다.")

else:
    st.info("👈 Please upload 'BalanceSheets.xlsx'")
