# ⚔️ Action RPG Combat Mechanics Simulator (MVP)

> **Role:** Lead Game Balance Designer (Candidate)  
> **Core Concept:** Time-based Action Combat Simulation & Data Pipeline

## 📱 Live Demo
[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://balance-sim-demo-fymypnl2dqsefveoluyf8l.streamlit.app/)
*(클릭하여 시뮬레이터를 직접 실행해보실 수 있습니다)*

## 🎯 Project Objective
액션 RPG 환경에서의 **복합적인 전투 변수(Cool-time, Casting Time, Animation Delay)**를 고려한 정밀 밸런싱 도구의 프로토타입(MVP)입니다. 

단순 턴제 계산이 아닌, **Time-Stream 방식**을 도입하여 실제 인게임 환경과 유사한 DPS 효율을 검증하고, 기획자가 엑셀 데이터만으로 밸런스를 제어하는 **Data-Driven Workflow**를 구현하는 데 초점을 맞췄습니다.

## 🛠 Key Features

### 1. Time-based Simulation Engine
- **기존 문제:** 단순 턴제(Turn-based) 방식은 '선후딜'과 '재사용 대기시간'이 겹치는 실시간 액션 전투의 밀도를 반영하지 못함.
- **해결:** 0.1초 단위의 타임라인 시뮬레이션 구현.
    - **Casting Logic:** 스킬 시전 중(Casting)에는 다른 행동 불가 상태(State) 처리.
    - **Cooldown Management:** 쿨타임 감소(CDR) 수치와 실시간 쿨타임 회복 로직 적용.

### 2. Data-Driven Architecture (File Upload System)
- **설계 의도:** 코드를 수정하지 않고, **엑셀 데이터(Table) 교체만으로** 밸런스 패치를 즉각 테스트할 수 있는 **'데이터 파이프라인'** 구축.
- **확장성:** 미리 정의된 **Table Schema(규격)**만 준수한다면, 전사/마법사/암살자 등 직업군이나 프로젝트에 관계없이 시뮬레이션 가능.
- **검증:** Web UI에서 직접 엑셀 파일을 업로드하여, 다양한 기획 수치가 로직에 정상적으로 반영되는지 실시간 검증 가능.

### 3. Visual Analytics
- **DPS Graph:** 시간 경과에 따른 누적 딜량 및 순간 DPS 변화 추이 시각화.
- **Skill Breakdown:** 전체 딜량에서 각 스킬이 차지하는 비중(Contribution) 분석.
- **Combat Log:** 틱(Tick) 단위의 상세 전투 로그 제공.

## 📂 Data Protocol (Excel Schema)
이 시뮬레이터는 약속된 **데이터 규격(Protocol)**을 준수하는 엑셀 파일을 통해 동작합니다. (`BalanceSheets.xlsx` 참조)

| Sheet Name | Description | Key Columns |
| :--- | :--- | :--- |
| **Stats** | 클래스 기본 스탯 정의 | `Class`, `Base_ATK`, `Crit_Rate`, `Crit_Dmg`, `Cooldown_Reduction` |
| **Skills** | 스킬 상세 스펙 정의 | `Skill_Name`, `Cooldown`, `Damage_Coef`, `Cast_Time`, `Is_BackAttack` |

> *Note: 업로드 기능은 이 스키마(Schema)가 일치하는 모든 데이터셋에 대해 호환성을 가집니다.*

## 💻 Tech Stack
- **Language:** Python 3.9
- **Core Libraries:** 
    - `Pandas` (Data Processing)
    - `Plotly` (Interactive Visualization)
    - `Openpyxl` (Excel Integration)
- **Deployment:** Streamlit Cloud

## 📝 Limitations & Future Improvements
- 본 프로젝트는 핵심 로직 검증을 위한 MVP 모델로, 피격/회피 로직 및 상태이상(CC기) 변수는 제외되었습니다.
- 향후 몬스터 패턴 로직과 파티 시너지(Buff/Debuff) 계산 모듈을 추가하여 고도화할 수 있습니다.
