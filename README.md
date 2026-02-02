# ⚖️ MMORPG Balance Verification System (Pro)

> **"Data-Driven Design: 감(Feel)이 아닌 데이터(Data)로 밸런스를 증명합니다."**
> 
> * **Project Type:** MMORPG 전투 & 경제 밸런스 검증 자동화 도구
> * **Role:** Lead Balance Designer (Candidate)
> * **Tech Stack:** Python 3.9, Streamlit, Pandas, Plotly, NumPy
> * **Live Demo:** [![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://balance-sim-demo-fymypnl2dqsefveoluyf8l.streamlit.app/)

---

## 🎯 프로젝트 개요 (Project Objective)

이 프로젝트는 MMORPG 기획 단계에서 수립한 **수치적 의도(Intention)**가 실제 인게임 환경에서 **어떤 결과(Result)**로 나타나는지를 사전에 시뮬레이션하고 검증하기 위해 개발되었습니다.

단순한 엑셀(Static) 계산의 한계를 넘어, **Time-stream(시간 흐름)** 기반의 전투 엔진과 **Monte Carlo(확률 분포)** 기법을 도입하여, 밸런스 리스크를 정량적으로 분석하고 제어하는 데 목적이 있습니다.

---

## 📂 프로젝트 구조 (File Structure)

유지보수와 확장성을 고려하여 기능별로 모듈화된 구조를 채택했습니다.

```bash
balance-sim-demo/
├── app.py              # [UI/Controller] 사용자 인터페이스 및 시각화 담당
├── sim_engine.py       # [Core Logic] 캐릭터, 스킬, 전투 공식 처리 엔진
├── data_manager.py     # [Data Pipeline] 엑셀 데이터 로드 및 전처리, 스탯 보간
└── BalanceSheets.xlsx  # [Database] 기획 데이터 (직업, 성장, 몬스터 등)
