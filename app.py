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
    tab1, tab2, tab3 = st.tabs(["1. 클래스 성장 검증", "2. 레이드 난이도 검증", "3. 과금 밸런스 검증"])

    # =========================================================================
    # TAB 1: 클래스 성장 검증
    # =========================================================================
    with tab1:
        st.subheader("1. Class Growth & DPS Simulation")
        st.info("📝 **테스트 조건:** 특정 레벨의 캐릭터가 '샌드백(방어력 0)'을 공격했을 때의 이론상 최대 DPS를 측정합니다.")

        with st.form("growth_form"):
            c1, c2, c3 = st.columns(3)
            with c1:
                if 'Class_Job' in data:
                    sel_class = st.selectbox("직업 선택 (Class)", data['Class_Job']['Class_Name'].unique())
                else: st.stop()
            with c2: sel_level = st.slider("테스트 레벨 (Level)", 1, 60, 60)
            with c3: sel_time = st.slider("전투 시간 (Time)", 10, 300, 60)
            
            # 실시간 목표값 표시
            target_dps = get_growth_stat(sel_level, data['Growth_Table'], 'Standard_DPS')
            st.markdown(f"👉 **검증 목표:** 레벨 {sel_level}의 기획 의도 표준 DPS는 **{int(target_dps):,}** 입니다.")
            
            submitted = st.form_submit_button("▶️ 시뮬레이션 실행 (Run)")
            
            if submitted:
                class_row = data['Class_Job'][data['Class_Job']['Class_Name'] == sel_class].iloc[0]
                player = Character(sel_level, class_row, data['Growth_Table'], data['Skill_Data'])
                
                steps = int(sel_time / 0.1)
                for _ in range(steps): player.update(0.1)
                
                actual_dps = player.total_damage / sel_time
                
                st.session_state.growth_result = {
                    "player": player, "actual": actual_dps, "target": target_dps, "log": player.damage_log,
                    "time": sel_time
                }

        if st.session_state.growth_result:
            res = st.session_state.growth_result
            ratio = res['actual'] / res['target'] if res['target'] > 0 else 0
            
            c1, c2, c3 = st.columns(3)
            c1.metric("실제 DPS (Actual)", f"{int(res['actual']):,}")
            c2.metric("목표 DPS (Target)", f"{int(res['target']):,}")
            c3.metric("달성률 (Ratio)", f"{ratio*100:.1f}%", delta="높을수록 강함")

            if 0.9 <= ratio <= 1.1:
                st.success(f"✅ **적정 (Pass):** 스킬 계수와 스탯 구조가 기획 의도({int(res['target']):,})에 부합합니다.")
            elif ratio > 1.1:
                st.warning(f"⚠️ **OP (Over Powered):** 기획 의도보다 **{ratio:.2f}배** 강합니다. 스킬 데미지(%)를 낮추거나, 성장 테이블의 목표치를 상향해야 합니다.")
            else:
                st.error(f"⚠️ **UP (Under Powered):** 딜이 부족합니다. 스킬 쿨타임을 줄이거나 계수를 상향하세요.")

            if res['log']:
                log_df = pd.DataFrame(res['log'])
                st.markdown("##### 📊 상세 전투 로그 (Damage Log)")
                st.line_chart(log_df.set_index('Time')['Cumulative'])

    # =========================================================================
    # TAB 2: 레이드 난이도 검증
    # =========================================================================
    with tab2:
        st.subheader("2. Raid & Dungeon TTK Analysis")
        st.markdown("**검증 목표:** 파티 규모와 유저 스펙을 고려할 때, 보스를 제한 시간 내에 잡을 수 있는가?")

        if 'Dungeon_Config' in data:
            st.markdown("##### 📋 검증 대상 던전 목록 (Input Data)")
            st.dataframe(data['Dungeon_Config'][['Dungeon_Name', 'Min_Level', 'Rec_Party_Size', 'Time_Limit_Sec']], use_container_width=True)
        
        with st.form("raid_form"):
            run_raid = st.form_submit_button("🛡️ 위 던전 리스트 일괄 검증 시작")
            
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
                    
                    status = "🟢 Clear" if ttk <= row['Time_Limit_Sec'] else "🔴 Fail"
                    dungeon_res.append({
                        "던전명": row['Dungeon_Name'],
                        "권장 레벨": row['Min_Level'],
                        "파티원": f"{row['Rec_Party_Size']}인",
                        "보스 체력": f"{boss_hp:,}",
                        "예상 소요시간": f"{int(ttk)}초",
                        "제한 시간": f"{row['Time_Limit_Sec']}초",
                        "판정": status
                    })
                st.session_state.raid_result = pd.DataFrame(dungeon_res)

        if st.session_state.raid_result is not None:
            st.markdown("##### 📊 검증 결과 리포트")
            df = st.session_state.raid_result
            st.dataframe(df, use_container_width=True)
            
            fig = px.bar(df, x='던전명', y=['예상 소요시간', '제한 시간'], barmode='group', title="클리어 타임 비교 (TTK Analysis)")
            st.plotly_chart(fig, use_container_width=True)
            
            st.info("**해석:** '예상 소요시간'이 '제한 시간'보다 길면 막대기가 더 높게 표시되며, 이는 **스펙 부족 또는 보스 체력 과다**를 의미합니다.")

    # =========================================================================
    # TAB 3: 과금 밸런스 검증 (기획적 해석 추가)
    # =========================================================================
    with tab3:
        st.subheader("3. Payment & Lanchester Analysis")
        st.markdown("**목적:** 과금 등급(Grade)에 따른 전투력 격차가 생태계를 파괴하지 않는지 '란체스터 법칙'으로 진단합니다.")

        if 'Payment_Grade' not in data:
            st.error("❌ 'Payment_Grade' 시트가 없습니다. 엑셀에 시트를 추가하고 다시 업로드해주세요.")
        else:
            with st.form("balance_form"):
                t_lv = st.slider("비교할 레벨 구간 (Target Level)", 1, 60, 60)
                st.markdown(f"👉 레벨 {t_lv} 기준, 등급별 전투력을 계산합니다.")
                
                check_bal = st.form_submit_button("💰 밸런스 격차 분석 실행")
                
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
                with c1:
                    st.markdown("##### 📋 등급별 전투력 데이터")
                    st.dataframe(df_b, use_container_width=True)
                with c2:
                    fig = px.bar(df_b, x='Grade', y='Combat Power', color='Grade', title="전투력(CP) 격차 시각화")
                    st.plotly_chart(fig, use_container_width=True)
                
                # 란체스터 해석
                try:
                    h_cp = df_b[df_b['Grade'].str.contains("Heavy", case=False)]['Combat Power'].values[0]
                    f_cp = df_b[df_b['Grade'].str.contains("Free", case=False)]['Combat Power'].values[0]
                    
                    # 전투력 비율
                    cp_ratio = h_cp / f_cp 
                    # 란체스터 교환비 (제곱근)
                    lanchester_n = np.sqrt(cp_ratio)
                    
                    st.markdown("---")
                    st.subheader("⚔️ 최종 진단 (Lanchester's Law)")
                    st.info(f"""
                    **[시뮬레이션 결과]**
                    * **전투력 격차:** 헤비과금 유저는 무과금 유저보다 스펙이 **{cp_ratio:.1f}배** 높습니다.
                    * **실질 교환비(N):** 하지만 다대일 전투(일점사 환경)를 고려한 란체스터 제2법칙에 따르면, **헤비과금 1명은 무과금 약 {lanchester_n:.1f}명과 대등**하게 싸울 수 있습니다.
                    
                    **💡 기획적 시사점 (Insight):**
                    단순 스탯 차이가 15배나 나더라도, 다수의 협공 앞에서는 4명을 당해내기 어렵습니다.
                    고과금 유저에게 확실한 '무쌍(일당백)' 경험을 제공하려면, 단순 스탯 상향 외에 **광역 피해량(AoE) 증가**나 **받는 피해 감소(Damage Reduction)** 옵션이 필수적임을 시사합니다.
                    """)
                except:
                    st.warning("⚠️ 정확한 진단을 위해 'Grade' 컬럼에 'Free'와 'Heavy'가 포함되어야 합니다.")

else:
    st.info("👈 왼쪽 사이드바에서 **BalanceSheets.xlsx** 파일을 업로드해주세요.")
