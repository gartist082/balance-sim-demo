import streamlit as st
import pandas as pd
import plotly.express as px
from data_manager import load_excel_data, get_growth_stat
from sim_engine import Character
import numpy as np

st.set_page_config(page_title="MMORPG Balance Verification Pro", layout="wide")

# 세션 초기화
if 'growth_res' not in st.session_state: st.session_state.growth_res = None
if 'monte_res' not in st.session_state: st.session_state.monte_res = None
if 'raid_res' not in st.session_state: st.session_state.raid_res = None

# 그래프 고정 (줌인 방지)
PLOT_CONFIG = {'displayModeBar': False, 'staticPlot': True}

st.title("⚖️ MMORPG Balance Verification System")

uploaded_file = st.sidebar.file_uploader("Upload Data (BalanceSheets.xlsx)", type=['xlsx'])
default_file = "BalanceSheets.xlsx"

data = None
if uploaded_file: data = load_excel_data(uploaded_file)
else: 
    try: data = load_excel_data(default_file)
    except: pass

if data:
    tab1, tab2, tab3 = st.tabs(["1. 클래스 성장 검증", "2. 레이드 난이도 검증", "3. 과금 밸런스 검증"])

    # =========================================================================
    # TAB 1: 클래스 성장 & 전투
    # =========================================================================
    with tab1:
        st.subheader("1. Class Growth & Combat Simulation")
        
        st.markdown("""
        > **🛠️ 검증 목표:**
        > 기획된 **성장 테이블(Growth Table)**과 **스킬 메커니즘(Skill Data)**이 실제 인게임 환경에서 의도한 DPS를 출력하는지 확인합니다.
        > * **단일 실행:** 스킬 쿨타임, 자원 소모, 데미지 공식의 정상 작동 여부 확인.
        > * **몬테카를로:** 치명타(Crit) 등 확률 변수에 따른 **DPS 편차(Stability)** 검증.
        """)

        with st.form("combat_form"):
            c1, c2, c3 = st.columns(3)
            with c1:
                if 'Class_Job' in data:
                    sel_class = st.selectbox("직업 선택", data['Class_Job']['Class_Name'].unique())
                else: st.stop()
            with c2: sel_level = st.slider("테스트 레벨", 1, 60, 60)
            with c3: sel_time = st.slider("전투 시간 (초)", 10, 300, 60)
            
            target_dps = get_growth_stat(sel_level, data['Growth_Table'], 'Standard_DPS')
            st.info(f"🎯 **기획 의도(Target):** 레벨 {sel_level}의 표준 DPS는 **{int(target_dps):,}** 입니다.")
            
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                btn_single = st.form_submit_button("▶️ 단일 전투 실행 (로그 확인)")
            with col_b2:
                btn_monte = st.form_submit_button("🎲 몬테카를로 실행 (편차 확인)")

            # 로직 수행
            class_row = data['Class_Job'][data['Class_Job']['Class_Name'] == sel_class].iloc[0]
            
            if btn_single:
                player = Character(sel_level, class_row, data['Growth_Table'], data['Skill_Data'])
                steps = int(sel_time / 0.1)
                for _ in range(steps): player.update(0.1)
                
                st.session_state.growth_res = {
                    "type": "single", "player": player, "time": sel_time, "target": target_dps
                }
                st.session_state.monte_res = None

            if btn_monte:
                results = []
                # [수정] 10회로 단축
                progress_bar = st.progress(0)
                
                for i in range(10):
                    p = Character(sel_level, class_row, data['Growth_Table'], data['Skill_Data'])
                    for _ in range(int(sel_time / 0.1)): p.update(0.1)
                    results.append(p.total_damage / sel_time)
                    progress_bar.progress((i + 1) / 10)
                
                progress_bar.empty()
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
            
            if ratio > 1.1: st.warning("⚠️ **OP 경고:** 기획 의도보다 데미지가 높습니다. 스킬 계수 하향이나 쿨타임 조정이 필요합니다.")
            elif ratio < 0.9: st.error("⚠️ **UP 경고:** 딜이 부족합니다. 버프가 필요합니다.")
            else: st.success("✅ **Pass:** 기획 의도와 일치합니다.")

            if res['player'].damage_log:
                log_df = pd.DataFrame(res['player'].damage_log)
                st.markdown("##### 📈 시간대별 누적 데미지")
                st.line_chart(log_df.set_index('Time')['Cumulative'])

        # 결과 2: 몬테카를로
        if st.session_state.monte_res:
            data_list = st.session_state.monte_res['data']
            avg = np.mean(data_list)
            std = np.std(data_list)
            min_v = np.min(data_list)
            max_v = np.max(data_list)
            
            st.divider()
            st.markdown("### 🎲 안정성 분석 결과 (N=10)")
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("평균 DPS", f"{int(avg):,}")
            c2.metric("최소 DPS", f"{int(min_v):,}")
            c3.metric("최대 DPS", f"{int(max_v):,}")
            c4.metric("표준편차", f"{int(std):,}")
            
            fig = px.histogram(data_list, nbins=10, title="DPS 분포도")
            fig.add_vline(x=avg, line_dash="dash", line_color="red")
            st.plotly_chart(fig, use_container_width=True, config=PLOT_CONFIG)
            
            st.info("""
            **💡 결과 해석:**
            * **Min-Max 격차:** 이 격차가 클수록 치명타 의존도가 높은 '로또형 딜러'입니다.
            * **표준편차:** 0에 가까울수록 매번 일정한 딜을 넣는 안정적인 직업입니다.
            """)

    # =========================================================================
    # TAB 2: 레이드 난이도 검증
    # =========================================================================
    with tab2:
        st.subheader("2. Raid & Dungeon TTK Analysis")
        st.markdown("""
        > **🛠️ 검증 목표:** 
        > 보스의 체력(HP)이 파티원들의 평균 스펙 대비 적절하게 설정되었는지 검증합니다.
        > * **TTK (Time To Kill):** 파티가 전멸하지 않고 딜을 넣었을 때 클리어까지 걸리는 시간.
        > * **조건 설정:** 유저들의 장비 수준이나 컨트롤 능력을 조절하여 난이도 변화를 예측합니다.
        """)

        # [수정] 슬라이더 명칭 변경 (객관화)
        with st.expander("⚙️ 시뮬레이션 조건 설정 (Simulation Settings)", expanded=True):
            party_spec_ratio = st.slider("파티 전투력 비율 (Party CP Ratio)", 50, 150, 100, format="%d%%")
            st.caption(f"💡 **설정:** 파티원들이 기획된 표준 스펙(Standard DPS)의 **{party_spec_ratio}%** 효율을 낸다고 가정합니다.")

        if st.button("🛡️ 레이드 검증 실행"):
            if 'Dungeon_Config' not in data: st.error("데이터 누락"); st.stop()
            
            dungeon_res = []
            for idx, row in data['Dungeon_Config'].iterrows():
                mob = data['Monster_Book'][data['Monster_Book']['Mob_ID'] == row['Boss_Mob_ID']].iloc[0]
                std_dps = get_growth_stat(row['Min_Level'], data['Growth_Table'], 'Standard_DPS')
                
                # 파티 DPS 계산
                final_party_dps = std_dps * row['Rec_Party_Size'] * (party_spec_ratio / 100.0)
                ttk = mob['HP'] / final_party_dps if final_party_dps > 0 else 999999
                limit = row['Time_Limit_Sec']
                
                status = "🟢 Clear" if ttk <= limit else "🔴 Fail"
                dungeon_res.append({
                    "던전명": row['Dungeon_Name'],
                    "권장Lv": int(row['Min_Level']),
                    "파티규모": f"{row['Rec_Party_Size']}인",
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
            
            fig = px.bar(df, x='던전명', y=['예상소요', '제한시간'], barmode='group', 
                         title=f"클리어 타임 비교 (전투력 {party_spec_ratio}% 기준)")
            st.plotly_chart(fig, use_container_width=True, config=PLOT_CONFIG)
            
            st.info("""
            **💡 그래프 해석:**
            * **예상소요(파랑) < 제한시간(빨강):** 클리어 가능. 파란 막대가 너무 낮으면 콘텐츠가 너무 쉬운 것입니다.
            * **예상소요(파랑) > 제한시간(빨강):** 클리어 불가(Time Over). 보스 체력을 하향하거나 유저 스펙을 상향해야 합니다.
            """)

    # =========================================================================
    # TAB 3: 과금 밸런스 검증
    # =========================================================================
    with tab3:
        st.subheader("3. Payment & Lanchester Analysis")
        st.markdown("""
        > **🛠️ 검증 목표:** 
        > 과금 등급(Grade)간 스탯 격차가 실제 PVP 환경(다대일 전투)에서 어떤 효율을 보이는지 **'란체스터 제2법칙'**으로 진단합니다.
        """)

        if 'Payment_Grade' not in data:
            st.error("❌ 'Payment_Grade' 시트가 없습니다.")
        else:
            t_lv = st.slider("비교할 레벨 구간", 1, 60, 60)
            
            if st.button("💰 밸런스 분석 실행"):
                base_atk = get_growth_stat(t_lv, data['Growth_Table'], 'Base_Primary_Stat')
                
                bal_res = []
                for idx, row in data['Payment_Grade'].iterrows():
                    mult = row['Stat_Multiplier']
                    # [수정] 공식 원상 복구: 선형 비례 (Multiplier = Combat Power)
                    cp = base_atk * mult * 100 
                    bal_res.append({"Grade": row['Grade'], "Multiplier": mult, "Combat Power": int(cp)})
                
                df_b = pd.DataFrame(bal_res)
                
                c1, c2 = st.columns(2)
                with c1: st.dataframe(df_b, use_container_width=True)
                with c2:
                    fig = px.bar(df_b, x='Grade', y='Combat Power', color='Grade', title="전투력(CP) 격차")
                    st.plotly_chart(fig, use_container_width=True, config=PLOT_CONFIG)
                
                try:
                    h_cp = df_b[df_b['Grade'].str.contains("Heavy", case=False)]['Combat Power'].values[0]
                    f_cp = df_b[df_b['Grade'].str.contains("Free", case=False)]['Combat Power'].values[0]
                    
                    cp_ratio = h_cp / f_cp
                    lanchester_n = np.sqrt(cp_ratio)
                    
                    st.success(f"""
                    **⚔️ 란체스터 법칙 시뮬레이션 결과**
                    
                    * **전투력 격차:** 헤비과금 유저는 무과금 유저보다 단순 스펙이 **{cp_ratio:.1f}배** 높습니다.
                    * **실질 교환비(N):** 하지만 다대일 전투(일점사 환경)를 가정할 때, 이론상 **1 vs {lanchester_n:.2f}명**이 한계입니다.
                    
                    **💡 기획적 통찰 (Insight):**
                    단순히 스탯만 15배 높다고 해서 15명을 이길 수 있는 것은 아닙니다. 
                    고과금 유저에게 압도적인 경험을 제공하려면 **'광역 피해(AoE)'** 또는 **'피해 감소'** 등 다대일 전투 보정 시스템이 필요함을 시사합니다.
                    """)
                except: pass

else:
    st.info("👈 Please upload 'BalanceSheets.xlsx'")
