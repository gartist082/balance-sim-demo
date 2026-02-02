        if run_monte:
            results = []
            progress = st.progress(0)
            status_text = st.empty()
            
            # [수정] 불필요한 멘트 제거 ("Simulating..."만 깔끔하게)
            with st.spinner("Analyzing Combat Stability..."):
                for i in range(10):
                    c = Character(tuned_stat, skills_df, back_prob)
                    steps = int(sim_time / 0.1)
                    for _ in range(steps): c.update(0.1)
                    results.append(c.total_damage/sim_time)
                    progress.progress((i + 1) / 10)
            
            status_text.empty()
            
            avg_dps = np.mean(results)
            min_dps = np.min(results)
            max_dps = np.max(results)
            std_dev = np.std(results)
            
            st.markdown("#### 📊 Simulation Report")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Average DPS", f"{int(avg_dps):,}")
            m2.metric("Min DPS", f"{int(min_dps):,}")
            m3.metric("Max DPS", f"{int(max_dps):,}")
            m4.metric("Stability (Std Dev)", f"{int(std_dev):,}")
            
            fig = px.histogram(results, nbins=10, title="DPS Probability Distribution")
            fig.add_vline(x=avg_dps, line_dash="dash", line_color="red", annotation_text="Avg")
            st.plotly_chart(fig, use_container_width=True)
            
            # [수정] 10회 멘트 삭제 -> 전문적인 분석 가이드로 교체
            st.info("""
            **📈 결과 해석 가이드:**
            1. **Stability (표준편차):** 값이 낮을수록 **'컨트롤/운'**에 덜 의존하는 안정적인 클래스입니다.
            2. **Min-Max Gap:** 격차가 크다면 **'치명타/백어택'** 의존도가 높다는 뜻이며, 밸런스 조정(보정)이 필요할 수 있습니다.
            3. **Distribution:** 그래프가 오른쪽으로 쏠려 있다면(Skewed Right), **'고점(High Potential)'**이 높은 성장형 캐릭터입니다.
            """)
