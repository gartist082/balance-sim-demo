# ⚔️ Combat Mechanics Simulator (Prototype)

> **Role:** Balance Designer (Candidate)  
> **Core Concept:** Time-based Action Combat Simulation

## 📱 Live Demo
[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://balance-sim-demo-fymypnl2dqsefveoluyf8l.streamlit.app/)
*(클릭하여 시뮬레이터를 직접 실행해보실 수 있습니다)*

## 🎯 Project Objective
MMORPG 환경에서의 **복합적인 전투 변수(Cool-time, Casting Time, Animation Delay)**를 고려한 정밀 밸런싱 도구의 프로토타입입니다. 단순 턴제 계산이 아닌, **Time-Stream 방식**을 도입하여 실제 인게임 DPS 효율을 검증하도록 설계되었습니다.

## 🛠 Key Features

### 1. Time-based Simulation Engine
- **기존 문제:** 턴제 방식(Turn-based)은 '선후딜'과 '재사용 대기시간'이 겹치는 액션 RPG의 전투 상황을 반영하지 못함.
- **해결:** 0.1초 단위의 타임라인 시뮬레이션을 구현.
    - **Casting Logic:** 스킬 시전 중(Casting)에는 다른 행동 불가 상태(State) 구현.
    - **Cooldown Management:** 쿨타임 감소(CDR) 수치와 실시간 쿨타임 회복 로직 적용.

### 2. Data-Driven Architecture
- **구조:** 로직(`app.py`)과 데이터(`Excel`)의 완벽한 분리.
- **활용:** 기획자가 코드를 건드리지 않고, 엑셀 시트(`Stats`, `Skills`)만 수정하여 즉각적인 밸런스 패치 테스트 가능.

### 3. Visual Analytics
- **DPS Graph:** 시간 경과에 따른 누적 딜량 및 순간 DPS 변화 추이 시각화.
- **Skill Breakdown:** 전체 딜량에서 각 스킬이 차지하는 비중(Contribution) 분석.
- **Combat Log:** 틱(Tick) 단위의 상세 전투 로그 제공.

## 📂 Data Structure (Excel)
이 시뮬레이터는 `BalanceSheets.xlsx`의 데이터를 기반으로 작동합니다.

1.  **Stats Sheet:** 클래스별 기초 스탯 (Base Attack, Crit Rate, Crit Dmg, CDR)
2.  **Skills Sheet:** 스킬별 상세 스펙 (Damage Coefficient, Cooldown, Casting Time)

## 💻 Tech Stack
- **Language:** Python 3.9
- **Core Libraries:** 
    - `Pandas` (Data Processing)
    - `Plotly` (Interactive Visualization)
    - `Openpyxl` (Excel Integration)
- **Deployment:** Streamlit Cloud
