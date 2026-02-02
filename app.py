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

st.title("⚖️ MMORPG Balance Verification System")

uploaded_file = st.sidebar.file_uploader("Upload Data (BalanceSheets.xlsx)", type=['xlsx'])
default_file = "BalanceSheets.xlsx"

data = None
if uploaded_file: data = load_excel_data(uploaded_file)
else: 
    try: data = load_excel_data(default_file)
    except: pass

if data:
    tab1, tab2, tab3 = st.tabs(["1. 클래스 성장/전투 검증", "2. 레이드 난이도 검증", "3. 과금 밸런스 검증"])

    # =========================================================================
    # TAB 1: 클래스 성장 & 전투 (몬테카를로 복구 + 상세 분석)
    # =========================================================================
    with tab1:
        st.subheader("1. Class Growth & Combat Simulation")
        st.info("📝 **검증 목적:** 특정 레벨 캐릭터의 스킬 사이클을 시뮬레이션하여, 기획된 '목표 DPS'를 달성하는지, 그리고 확률적 변수(치명타 등)에 따른 편차는 안정한지 확인합니다.")

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
            
            # 버튼 분리
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                btn_single = st.form_submit_button("▶️ 단일 전투 실행 (로그 분석)")
            with col_b2:
                btn_monte = st.form_submit_button("🎲 몬테카를로 실행 (안정성 검증)")

            # 로직 수행
            class_row = data['Class_Job'][data['Class_Job']['Class_Name'] == sel_class].iloc[0]
            
            if btn_single:
                player = Character(sel_level, class_row, data['Growth_Table'], data['Skill_Data'])
                steps = int(sel_time / 0.1)
                for _ in range(steps): player.update(0.1)
                
                st.session_state.growth_res = {
                    "type": "single", "player": player, "time": sel_time, "target": target_dps
                }
                st.session_state.monte_res = None # 초기화

            if btn_monte:
                results = []
                # 시연용 20회 반복
                for _ in range(20):
                    p = Character(sel_level, class_row, data['Growth_Table'], data['Skill_Data'])
                    for _ in range(int(sel_time / 0.1)): p.update(0.1)
                    results.append(p.total_damage / sel_time)
                
                st.session_state.monte_res = {"data": results, "target": target_dps}
                st.session_state.growth_res = None # 초기화

        # [결과 화면 1] 단일 전투 (Single Run)
        if st.session_state.growth_res:
            res = st.session_state.growth_res
            actual_dps = res['player'].total_damage / res['time']
            ratio = actual_dps / res['target'] if res['target'] > 0 else 0
            
            st.divider()
            st.markdown("### 📊 단일 전투 분석 결과")
            
            m1, m2, m3 = st.columns(3)
            m1.metric("실제 DPS", f"{int(actual_dps):,}")
            m2.metric("목표 DPS", f"{int(res['target']):,}")
            m3.metric("달성률", f"{ratio*100:.1f}%", delta="적정: 90~110%")
            
            if ratio > 1.1: st.warning("⚠️ **OP 경고:** 기획 의도보다 데미지가 높습니다. 스킬 계수 하향을 고려하세요.")
            elif ratio < 0.9: st.error("⚠️ **UP 경고:** 딜이 부족합니다. 쿨타임 감소나 계수 상향이 필요합니다.")
            else: st.success("✅ **Pass:** 기획 의도와 일치합니다.")

            # 상세 로그 및 차트
            if res['player'].damage_log:
                log_df = pd.DataFrame(res['player'].damage_log)
                
                c1, c2 = st.columns([2, 1])
                with c1:
                    st.markdown("**📈 시간대별 누적 데미지**")
                    st.line_chart(log_df.set_index('Time')['Cumulative'])
                with c2:
                    st.markdown("**🥧 스킬별 데미지 비중**")
                    # 스킬 이름별 데미지 합산
                    skill_sum = log_df.groupby('Name')['Damage'].sum().reset_index()
                    fig = px.pie(skill_sum, values='Damage', names='Name')
                    st.plotly_chart(fig, use_container_width=True)
                
                with st.expander("🔎 초 단위 상세 로그 보기"):
                    st.dataframe(log_df)

        # [결과 화면 2] 몬테카를로 (Monte Carlo)
        if st.session_state.monte_res:
            data_list = st.session_state.monte_res['data']
            avg = np.mean(data_list)
            std = np.std(data_list)
            min_v = np.min(data_list)
            max_v = np.max(data_list)
            
            st.divider()
            st.markdown("### 🎲 몬테카를로 안정성 분석 (N=20)")
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("평균 DPS", f"{int(avg):,}")
            c2.metric("최소 DPS (Unlucky)", f"{int(min_v):,}")
            c3.metric("최대 DPS (Lucky)", f"{int(max_v):,}")
            c4.metric("표준편차 (Stability)", f"{int(std):,}", help="낮을수록 운에 덜 의존하는 안정적인 직업입니다.")
            
            fig = px.histogram(data_list, nbins=10, title="DPS 분포도 (Probability Distribution)")
            fig.add_vline(x=avg, line_dash="dash", line_color="red", annotation_text="AVG")
            st.plotly_chart(fig, use_container_width=True)

    # =========================================================================
    # TAB 2: 레이드 난이도 검증 (설정 기능 추가)
    # =========================================================================
    with tab2:
        st.subheader("2. Raid & Dungeon TTK Analysis")
        st.markdown("**검증 목표:** 기획된 보스 체력이 유저 스펙(Standard DPS) 대비 적절한지, 제한 시간 내 클리어가 가능한지 검증합니다.")

        # [기능 추가] 시뮬레이션 조건 설정
        with st.expander("⚙️ 시뮬레이션 조건 설정 (Simulation Settings)", expanded=True):
            party_spec_ratio = st.slider("파티원 스펙 수준 (기획 의도 대비)", 50, 200, 100, format="%d%%")
            st.caption(f"💡 설정: 유저들이 기획 의도(Standard DPS)의 **{party_spec_ratio}%** 효율을 낸다고 가정합니다.")

        if st.button("🛡️ 레이드 검증 실행", key='btn_raid'):
            if 'Dungeon_Config' not in data: st.error("데이터 누락"); st.stop()
            
            dungeon_res = []
            for idx, row in data['Dungeon_Config'].iterrows():
                mob = data['Monster_Book'][data['Monster_Book']['Mob_ID'] == row['Boss_Mob_ID']].iloc[0]
                boss_hp = mob['HP']
                
                # 유저 1인 스펙 (성장 테이블 기준)
                std_dps = get_growth_stat(row['Min_Level'], data['Growth_Table'], 'Standard_DPS')
                
                # 파티 전체 DPS (파티원 수 * 표준DPS * 사용자가 설정한 스펙 비율)
                spec_multiplier = party_spec_ratio / 100.0
                party_dps = std_dps * row['Rec_Party_Size'] * spec_multiplier
                
                # TTK 계산
                ttk = boss_hp / party_dps if party_dps > 0 else 999999
                limit = row['Time_Limit_Sec']
                
                status = "🟢 Clear" if ttk <= limit else "🔴 Fail"
                
                dungeon_res.append({
                    "던전명": row['Dungeon_Name'],
                    "권장Lv": int(row['Min_Level']),
                    "파티규모": f"{row['Rec_Party_Size']}인",
                    "보스체력": f"{boss_hp:,}",
                    "파티DPS(예상)": f"{int(party_dps):,}",
                    "예상소요(초)": int(ttk),
                    "제한시간(초)": limit,
                    "판정": status
                })
            
            st.session_state.raid_res = pd.DataFrame(dungeon_res)

        if st.session_state.raid_res is not None:
            df = st.session_state.raid_res
            st.markdown("##### 📊 검증 결과 리포트")
            st.dataframe(df, use_container_width=True)
            
            fig = px.bar(df, x='던전명', y=['예상소요(초)', '제한시간(초)'], barmode='group', 
                         title=f"클리어 타임 비교 (스펙 {party_spec_ratio}% 기준)")
            st.plotly_chart(fig, use_container_width=True)
            
            st.info("""
            **💡 그래프 해석:**
            * 파란색 막대(예상소요)가 하늘색 막대(제한시간)보다 낮아야 클리어 가능합니다.
            * 만약 모든 던전이 Fail이라면, 보스 체력을 낮추거나 유저 표준 DPS를 상향해야 합니다.
            """)

    # =========================================================================
    # TAB 3: 과금 밸런스 검증 (Disclaimer 추가)
    # =========================================================================
    with tab3:
        st.subheader("3. Payment & Lanchester Analysis")
        
        # [추가] 임의 데이터임을 명시
        st.warning("⚠️ **Disclaimer:** 본 시뮬레이션에 사용된 `Payment_Grade` 데이터는 검증 로직 시연을 위한 **임의의 더미 데이터**입니다. 실제 라이브 서비스 데이터가 아님을 밝힙니다.")

        if 'Payment_Grade' not in data:
            st.error("❌ 'Payment_Grade' 시트가 없습니다.")
        else:
            t_lv = st.slider("비교할 레벨 구간", 1, 60, 60)
            
            if st.button("💰 밸런스 분석 실행"):
                base_atk = get_growth_stat(t_lv, data['Growth_Table'], 'Base_Primary_Stat')
                
                bal_res = []
                for idx, row in data['Payment_Grade'].iterrows():
                    mult = row['Stat_Multiplier']
                    # 수정된 CP 공식: (공격력 * 배율) * (체력 * 배율) -> 배율의 제곱 효과
                    cp = (base_atk * mult) * (base_atk * mult) 
                    bal_res.append({"Grade": row['Grade'], "Multiplier": mult, "Combat Power": int(cp)})
                
                df_b = pd.DataFrame(bal_res)
                
                c1, c2 = st.columns(2)
                with c1:
                    st.dataframe(df_b, use_container_width=True)
                with c2:
                    fig = px.bar(df_b, x='Grade', y='Combat Power', color='Grade', title="전투력(CP) 격차")
                    st.plotly_chart(fig, use_container_width=True)
                
                try:
                    h_cp = df_b[df_b['Grade'].str.contains("Heavy")]['Combat Power'].values[0]
                    f_cp = df_b[df_b['Grade'].str.contains("Free")]['Combat Power'].values[0]
                    ratio = np.sqrt(h_cp / f_cp)
                    
                    st.success(f"""
                    **⚔️ 란체스터 법칙 적용 결과**
                    * 헤비과금 유저는 무과금 유저 대비 전투력이 높습니다.
                    * 다대일 전투(일점사) 환경을 가정할 때, 이론상 **1 vs {ratio:.2f}명**까지 대등한 전투가 가능합니다.
                    """)
                except: pass
