import streamlit as st
import matplotlib.pyplot as plt
from BattleSim import run_simulation, load_params

st.title("전투 검증 시뮬레이터 데모")

n = st.slider("시뮬레이션 반복 횟수", 50, 1000, 200, 50)

st.write("현재 파라미터:")
player, enemy = load_params()
st.write("플레이어:", player)
st.write("적:", enemy)

if st.button("▶ 시뮬레이션 실행"):
    with st.spinner("시뮬레이션 중..."):
        df = run_simulation(n=n)
    st.success("완료!")

    win_rate = (df['winner']=='player').mean() * 100
    st.metric("플레이어 승률", f"{win_rate:.2f}%")
    st.metric("평균 턴 수", f"{df['turns'].mean():.2f}")

    fig, ax = plt.subplots()
    df['winner'].value_counts().plot(kind='bar', ax=ax, color=['skyblue','salmon','gray'])
    st.pyplot(fig)
