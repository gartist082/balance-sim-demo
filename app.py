# app.py (BattleSim + dashboard 완전 통합 버전)
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(page_title="Game Balance Simulator", layout="wide")

@st.cache_data
def load_params():
    try:
        df = pd.read_csv('balance_params.csv')
        df.columns = df.columns.str.strip().str.lower()  # 핵심 수정!
        st.success(f"✅ CSV 로드 성공! 열: {list(df.columns)}")
        return df
    except Exception as e:
        st.error(f"❌ CSV 오류: {e}")
        return None

# BattleSim 함수들 (BattleSim.py에서 가져옴)
def calculate_damage(attacker, defender):
    base_dmg = attacker['atk']
    if np.random.random() < attacker['crit_rate']:
        base_dmg *= attacker['crit_mult']
    final_dmg = max(1, base_dmg - defender['armor_pen'])
    if np.random.random() < defender['dodge_rate']:
        final_dmg = 0
    return final_dmg

def run_single_battle(player_stats, enemy_stats):
    p_hp, e_hp = player_stats['hp'], enemy_stats['hp']
    turns = 0
    while p_hp > 0 and e_hp > 0 and turns < 200:
        turns += 1
        # Player attack
        e_hp -= calculate_damage(player_stats, enemy_stats)
        if e_hp <= 0:
            return 'player', turns
        # Enemy attack  
        p_hp -= calculate_damage(enemy_stats, player_stats)
    return 'enemy' if p_hp <= 0 else 'player', turns

# Streamlit UI
st.title("⚔️ 전투 밸런스 시뮬레이터")
st.markdown("엑셀 CSV로 만든 스탯을 불러와 승률 분석")

df = load_params()
if df is not None and len(df) >= 2:
    player = df[df['role'] == 'player'].iloc[0]
    enemy = df[df['role'] == 'enemy'].iloc[0]
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Player")
        st.json(player.to_dict())
    with col2:
        st.subheader("Enemy") 
        st.json(enemy.to_dict())
    
    iterations = st.slider("시뮬레이션 횟수", 100, 10000, 2000)
    
    if st.button("시뮬레이션 실행", type="primary"):
        results = {'player_wins': 0, 'turns': []}
        progress = st.progress(0)
        
        for i in range(iterations):
            winner, turns = run_single_battle(player, enemy)
            if winner == 'player':
                results['player_wins'] += 1
            results['turns'].append(turns)
            progress.progress((i+1) / iterations)
        
        win_rate = results['player_wins'] / iterations
        col1, col2 = st.columns(2)
        col1.metric("승률", f"{win_rate:.1%}")
        col2.metric("평균 턴", f"{np.mean(results['turns']):.1f}")
        
        fig = px.histogram(results['turns'], nbins=30, title="턴 분포")
        st.plotly_chart(fig, use_container_width=True)
        
        st.success(f"✅ {iterations:,}회 시뮬레이션 완료!")
else:
    st.warning("balance_params.csv 파일을 업로드하고 'role' 열에 'player', 'enemy' 구분하세요.")

st.markdown("---")
st.caption("Game Designer 김지훈 | 전투 밸런스 자동 검증 데모")
