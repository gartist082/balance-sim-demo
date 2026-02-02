import streamlit as st
import pandas as pd
import plotly.express as px
from data_manager import load_excel_data, get_growth_stat
from sim_engine import Character
import numpy as np

st.set_page_config(page_title="MMORPG Balance Verification Pro", layout="wide")

# 그래프 고정 설정 (줌인/아웃 방지)
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
    # 탭 4개 구성 (데이터 열람 복구)
    tab1, tab2, tab3, tab4 = st.tabs(["1. 클래스 성장 검증", "2. 레이드 난이도 검증", "3. 과금 밸런스 검증", "4. 데이터 열람"])

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
            
            target_dps = get_growth_stat(sel_level, data['Growth_Table'], 'Standard_DPS')
            st.markdown(f"👉 **Target DPS (기획 의도):** {int(target_dps):,}")
            
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
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                for i in range(10): # 10회
                    p = Character(sel_level, class_row, data['Growth_Table'], data['Skill_Data'])
                    for _ in range(int(sel_time / 0.1)): p.update(0.1)
                    results.append(p.total_damage / sel_time)
                    progress_bar.progress((i + 1) / 10)
                    status_text.text(f"Simulating... {i+1}/10")
                
                status_text.empty()
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

            # [복구] 상세 로그 및 차트 (그래프 고정 적용)
            if res['player'].damage_log:
                log_df = pd.DataFrame(res['player'].damage_log)
                
                c1, c2 = st.columns([2, 1])
                with c1:
                    st.markdown("**📈 시간대별 누적 데미지**")
                    st.line_chart(log_df.set_index('Time')['Cumulative'])
                with c2:
                    st.markdown("**🥧 스킬별 데미지 비중**")
                    skill_sum = log_df.groupby('Name')['Damage'].sum().reset_index()
                    fig_pie = px.pie(skill_sum, values='Damage', names='Name')
                    st.plotly_chart(fig_pie, use_container_width=True, config=PLOT_CONFIG)
                
                with st.expander("🔎 초 단위 상세 로그 보기"):
                    st.dataframe(log_df)

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
        st.markdown("**검증 목표:** 파티 규모와 유저 스펙을 고려할 때, 보스를 제한 시간 내에 잡을 수 있는가?")

        # [수정] 슬라이더 설명 명확화
        with st.expander("⚙️ 시뮬레이션 조건 설정 (Setting)", expanded=True):
            party_spec_ratio = st.slider("파티원 평균 스펙 비율", 50, 150, 100, format="%d%%")
            st.info("""
            **💡 설정 가이드:**
            * **100%:** 파티원 전원이 기획된 'Standard DPS'를 정확히 낼 때.
            * **80%:** 유저들의 장비가 부족하거나 컨트롤 미숙으로 딜 효율이 떨어질 때.
            * **120%:** 유저들이 '고강 장비'나 '시너지 조합'으로 기획 의도보다 더 강할 때.
            """)

        with st.form("raid_form"):
            if st.form_submit_button("🛡️ 레이드 검증 실행"):
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
            st.dataframe(df, use_container_width=True)
            
            # [수정] 그래프 고정
            fig = px.bar(df, x='던전명', y=['예상소요', '제한시간'], barmode='group', 
                         title=f"클리어 타임 비교 (스펙 {party_spec_ratio}% 기준)")
            st.plotly_chart(fig, use_container_width=True, config=PLOT_CONFIG)
            
            st.info("**해석:** '예상소요(파란색)'가 '제한시간(빨간색)'보다 높으면 클리어 불가능(Fail)입니다.")

    # =========================================================================
    # TAB 3: 과금 밸런스 검증
    # =========================================================================
    with tab3:
        st.subheader("3. Payment & Lanchester Analysis")
        st.markdown("**검증 목표:** 과금 등급(Grade)간 스탯 격차가 실제 PVP 환경(다대일 전투)에서 어떤 효율을 보이는지 진단합니다.")

        if 'Payment_Grade' not in data:
            st.error("❌ 'Payment_Grade' 시트가 없습니다.")
        else:
            with st.form("balance_form"):
                t_lv = st.slider("비교할 레벨 구간", 1, 60, 60)
                
                if st.form_submit_button("💰 밸런스 분석 실행"):
                    base_atk = get_growth_stat(t_lv, data['Growth_Table'], 'Base_Primary_Stat')
                    bal_res = []
                    for idx, row in data['Payment_Grade'].iterrows():
                        mult = row['Stat_Multiplier']
                        # 공식 원복: 전투력 = 배율 (선형)
                        cp = base_atk * mult * 100 
                        bal_res.append({"Grade": row['Grade'], "Multiplier": mult, "Combat Power": int(cp)})
                    
                    st.session_state.bal_df = pd.DataFrame(bal_res)

            if 'bal_df' in st.session_state:
                df_b = st.session_state.bal_df
                
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
                    
                    # [수정] 란체스터 설명 (중립적이고 분석적인 톤)
                    st.info(f"""
                    **📊 밸런스 분석 결과:**
                    * **1:1 전투:** 헤비과금은 무과금보다 스펙이 **{cp_ratio:.1f}배** 높으므로 압도적으로 승리합니다.
                    * **다대일 전투:** 하지만 란체스터 제2법칙에 따르면, 무과금 유저 **{lanchester_n:.1f}명**이 협공하면 대등한 전투가 성립됩니다.
                    
                    **💡 기획적 제언:**
                    이 결과는 **"고과금 유저라도 다수의 협공 앞에서는 무적일 수 없다"**는 MMORPG의 생태계 균형을 보여줍니다. 
                    만약 기획 의도가 '일당백의 무쌍'이라면, 단순 스탯 상향보다는 **광역 스킬(AoE) 효율**이나 **생존기(무적/피감)** 설계를 통해 다대일 전투 능력을 보강해야 함을 시사합니다.
                    """)
                except: pass

    # =========================================================================
    # TAB 4: 데이터 열람 (복구 완료)
    # =========================================================================
    with tab4:
        st.subheader("4. Loaded Balance Data")
        st.markdown("**📂 현재 로드된 엑셀 데이터 확인**")
        
        sheet_names = list(data.keys())
        if sheet_names:
            selected_sheet = st.selectbox("시트 선택 (Select Sheet)", sheet_names)
            st.dataframe(data[selected_sheet], use_container_width=True)
        else:
            st.warning("로드된 데이터가 없습니다.")

else:
    st.info("👈 Please upload 'BalanceSheets.xlsx'")
