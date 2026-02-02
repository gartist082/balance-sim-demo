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
if 'bal_df' not in st.session_state: st.session_state.bal_df = None
if 'view_df' not in st.session_state: st.session_state.view_df = None

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

    # =========================================================================
    # TAB 1: 클래스 성장 & 전투
    # =========================================================================
    with tab1:
        st.subheader("1. Class Growth & Combat Simulation")
        st.info("📝 **검증 목적:** 기획된 '목표 DPS' 달성 여부와 확률 변수(치명타)에 따른 딜 편차를 확인합니다.")

        with st.form("combat_form"):
            c1, c2, c3 = st.columns(3)
            with c1:
                if 'Class_Job' in data:
                    sel_class = st.selectbox("직업 선택", data['Class_Job']['Class_Name'].unique())
                else: st.stop()
            with c2: sel_level = st.slider("테스트 레벨", 1, 60, 60)
            with c3: sel_time = st.slider("전투 시간 (초)", 10, 300, 60)
            
            # 튜닝 옵션
            st.markdown("---")
            st.caption("⚙️ **스탯 튜닝 (Optional):**")
            tc1, tc2 = st.columns(2)
            with tc1: adj_atk = st.number_input("공격력 보정 (%)", 10, 500, 100)
            with tc2: adj_crit = st.slider("치명타율 추가 (%)", 0, 50, 0)

            col_b1, col_b2 = st.columns(2)
            with col_b1:
                btn_single = st.form_submit_button("▶️ 단일 전투 실행")
            with col_b2:
                btn_monte = st.form_submit_button("🎲 몬테카를로 실행")

            class_row = data['Class_Job'][data['Class_Job']['Class_Name'] == sel_class].iloc[0]
            target_dps = get_growth_stat(sel_level, data['Growth_Table'], 'Standard_DPS')
            
            if btn_single:
                player = Character(sel_level, class_row, data['Growth_Table'], data['Skill_Data'])
                player.atk = player.atk * (adj_atk / 100.0)
                player.crit_rate += (adj_crit / 100.0)
                
                steps = int(sel_time / 0.1)
                for _ in range(steps): player.update(0.1)
                
                st.session_state.growth_res = {
                    "type": "single", "player": player, "time": sel_time, "target": target_dps
                }
                st.session_state.monte_res = None

            if btn_monte:
                results = []
                with st.spinner("Simulating 10 battles..."):
                    for i in range(10):
                        p = Character(sel_level, class_row, data['Growth_Table'], data['Skill_Data'])
                        p.atk = p.atk * (adj_atk / 100.0)
                        p.crit_rate += (adj_crit / 100.0)
                        for _ in range(int(sel_time / 0.1)): p.update(0.1)
                        results.append(p.total_damage / sel_time)
                
                st.session_state.monte_res = {"data": results, "target": target_dps}
                st.session_state.growth_res = None

        # 결과 1: 단일
        if st.session_state.growth_res:
            res = st.session_state.growth_res
            actual_dps = res['player'].total_damage / res['time']
            ratio = actual_dps / res['target'] if res['target'] > 0 else 0
            
            st.divider()
            m1, m2, m3 = st.columns(3)
            m1.metric("실제 DPS", f"{int(actual_dps):,}")
            m2.metric("목표 DPS", f"{int(res['target']):,}")
            m3.metric("달성률", f"{ratio*100:.1f}%")
            
            if ratio > 1.1: st.warning("⚠️ **OP 경고:** 기획 의도보다 데미지가 높습니다.")
            elif ratio < 0.9: st.error("⚠️ **UP 경고:** 딜이 부족합니다.")
            else: st.success("✅ **Pass:** 기획 의도와 일치합니다.")

            if res['player'].damage_log:
                log_df = pd.DataFrame(res['player'].damage_log)
                c1, c2 = st.columns([2, 1])
                with c1:
                    st.markdown("**📈 누적 데미지**")
                    st.line_chart(log_df.set_index('Time')['Cumulative'])
                with c2:
                    st.markdown("**🥧 스킬 비중**")
                    skill_sum = log_df.groupby('Name')['Damage'].sum().reset_index()
                    fig_pie = px.pie(skill_sum, values='Damage', names='Name')
                    st.plotly_chart(fig_pie, use_container_width=True, config=PLOT_CONFIG)
                
                with st.expander("🔎 상세 로그 보기"):
                    st.dataframe(log_df)

        # 결과 2: 몬테카를로
        if st.session_state.monte_res:
            data_list = st.session_state.monte_res['data']
            avg = np.mean(data_list)
            std = np.std(data_list)
            min_v = np.min(data_list)
            max_v = np.max(data_list)
            
            st.divider()
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("평균 DPS", f"{int(avg):,}")
            c2.metric("최소", f"{int(min_v):,}")
            c3.metric("최대", f"{int(max_v):,}")
            c4.metric("표준편차", f"{int(std):,}")
            
            fig = px.histogram(data_list, nbins=10, title="DPS 분포도")
            fig.add_vline(x=avg, line_dash="dash", line_color="red")
            st.plotly_chart(fig, use_container_width=True, config=PLOT_CONFIG)

    # =========================================================================
    # TAB 2: 레이드 난이도 검증 (변수명 수정 완료)
    # =========================================================================
    with tab2:
        st.subheader("2. Raid & Dungeon TTK Analysis")
        st.markdown("**검증 목표:** 파티 규모와 유저 스펙을 고려할 때, 제한 시간 내 클리어가 가능한가?")

        with st.form("raid_form"):
            party_spec_ratio = st.slider("파티원 평균 스펙 비율", 50, 150, 100, format="%d%%")
            st.caption("💡 100%=정상 스펙, 80%=컨트롤 미숙, 120%=고스펙")
            
            if st.form_submit_button("🛡️ 레이드 검증 실행"):
                if 'Dungeon_Config' not in data: st.error("데이터 누락"); st.stop()
                
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
                        "TTK (Sec)": int(ttk),
                        "Limit (Sec)": limit,
                        "판정": status
                    })
                st.session_state.raid_res = pd.DataFrame(dungeon_res)

        if st.session_state.raid_res is not None:
            df = st.session_state.raid_res
            st.markdown("##### 📊 검증 결과 리포트")
            st.caption(f"👉 **현재 조건:** 파티원들이 기획 의도 대비 **{party_spec_ratio}%** 효율을 낼 때를 가정합니다.")
            st.dataframe(df, use_container_width=True)
            
            # [수정] y축 이름을 데이터프레임 컬럼명과 일치시킴
            fig = px.bar(df, x='던전명', y=['TTK (Sec)', 'Limit (Sec)'], barmode='group', 
                         title=f"클리어 타임 비교")
            st.plotly_chart(fig, use_container_width=True, config=PLOT_CONFIG)

    # =========================================================================
    # TAB 3: 과금 밸런스 검증 (변수명 수정 완료)
    # =========================================================================
    with tab3:
        st.subheader("3. Payment & Lanchester Analysis")
        st.markdown("**검증 목표:** 과금 등급간 스탯 격차와 다대일 전투 효율 진단")

        if 'Payment_Grade' not in data:
            st.error("❌ 'Payment_Grade' 시트가 없습니다.")
        else:
            with st.form("balance_form"):
                t_lv = st.slider("비교할 레벨 구간", 1, 60, 60)
                check_bal = st.form_submit_button("💰 밸런스 분석 실행")
                
                if check_bal:
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
                    # [수정] y축 이름을 데이터프레임 컬럼명 'Combat Power'로 일치시킴
                    fig = px.bar(df_b, x='Grade', y='Combat Power', color='Grade', title="전투력(CP) 격차")
                    st.plotly_chart(fig, use_container_width=True, config=PLOT_CONFIG)
                
                try:
                    h_cp = df_b[df_b['Grade'].str.contains("Heavy", case=False)]['Combat Power'].values[0]
                    f_cp = df_b[df_b['Grade'].str.contains("Free", case=False)]['Combat Power'].values[0]
                    ratio = np.sqrt(h_cp / f_cp)
                    
                    st.info(f"""
                    **⚔️ 란체스터 분석 결과:**
                    * 헤비과금 유저는 무과금 유저보다 단순 스펙이 **{h_cp/f_cp:.1f}배** 높습니다.
                    * 하지만 다대일 전투(일점사) 환경에서는 이론상 **1 vs {ratio:.2f}명**까지가 한계입니다.
                    """)
                except: pass

    # =========================================================================
    # TAB 4: 데이터 열람
    # =========================================================================
    with tab4:
        st.subheader("4. Loaded Balance Data")
        
        with st.form("data_view_form"):
            sheet_names = list(data.keys())
            selected_sheet = st.selectbox("시트 선택 (Select Sheet)", sheet_names)
            view_btn = st.form_submit_button("📂 데이터 조회")
            
            if view_btn:
                st.session_state.view_df = data[selected_sheet]

        if st.session_state.view_df is not None:
            st.dataframe(st.session_state.view_df, use_container_width=True)
        elif sheet_names:
            st.info("위에서 시트를 선택하고 '데이터 조회' 버튼을 눌러주세요.")

else:
    st.info("👈 Please upload 'BalanceSheets.xlsx'")
