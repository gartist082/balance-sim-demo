# ⚖️ MMORPG Balance Verification System (Pro)

> **"Data-Driven Design: 감(Feel)이 아닌 데이터(Data)로 밸런스를 증명합니다."**
> 
> * **Project Type:** MMORPG 전투 밸런스 검증 자동화 도구
> * **Role:** Lead Balance Designer (Candidate)
> * **Co-Work:** AI Assistant (Python Implementation & Refactoring)
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
├── app.py              # [UI/View] 사용자 인터페이스 및 결과 시각화
├── sim_engine.py       # [Model] 캐릭터, 스킬 로직, 데미지 산출 엔진
├── data_manager.py     # [Controller] 엑셀 데이터 로드, 전처리, 스탯 보간
└── BalanceSheets.xlsx  # [DB] 기획 데이터 (직업, 성장, 몬스터, 던전 등)

## 🛠️ 핵심 기능 (Key Features)

### 1. 클래스 성장 및 전투 검증 (Class Growth & Combat Sim)
*   **Time-based Engine:** 0.1초 단위 시뮬레이션을 통해 쿨타임, 시전 시간, 자원(MP) 회복 등 실제 전투 리듬을 정밀하게 구현했습니다.
*   **Monte Carlo Analysis:** 치명타(Crit) 등 확률 변수가 포함된 전투를 반복 시행하여, DPS의 **표준편차(Stability)**와
최소/최대 격차를 검증합니다.

### 2. 레이드 난이도 검증 (Raid TTK Analysis)
*   **TTK (Time To Kill) 모델링:** 보스 체력과 파티원들의 표준 스펙(Standard DPS)을 대조하여 예상 클리어 타임을 산출합니다.
*   **Variable Scenario:** 파티원 스펙 수준(50%~150%) 조절을 통해, 컨트롤 미숙이나 장비 부족 상황에서의
 클리어 가능 여부(Fail/Clear)를 진단합니다.

### 3. 과금 밸런스 및 생태계 진단 (Payment & Ecosystem)
*   **Ecosystem Balance:** 과금 등급별(무과금 vs 핵과금) 스펙 격차를 시각화합니다.
*   **Lanchester's Law:** 란체스터 제2법칙(제곱 법칙)을 적용하여, RVR(다대일 전투) 환경에서의 **'실질적 교환비(Exchange Ratio)'**를
 이론적으로 도출합니다.

---

## 🧩 데이터 프로토콜 (Excel Schema)

본 시뮬레이터는 코드 수정 없이 **엑셀 데이터 교체**만으로 다양한 게임 환경을 테스트할 수 있도록 설계되었습니다.

### 1. `Class_Job` (직업 정의)
*   **Role:** Tank, Dealer, Healer 등 직업의 역할군 정의
*   **Stat_Weight:** 레벨업 시 상승하는 기초 스탯(Primary Stat)이 공격력에 반영되는 가중치
*   **Crit_Rate:** 직업별 기본 치명타 확률 (몬테카를로 변동성의 핵심 변수)

### 2. `Growth_Table` (성장 곡선)
*   **Base_Primary_Stat:** 레벨별 기초 스탯 총량 (지수 함수적 증가)
*   **Standard_DPS:** **[검증 기준점]** 기획자가 의도한 해당 레벨의 목표 DPS (Target)

### 3. `Skill_Data` (스킬 메커니즘)
*   **Cooldown / MP_Cost:** 스킬 회전율과 자원 관리의 핵심 변수
*   **Dmg_Percent:** 공격력 대비 데미지 계수 (%)
*   **Hit_Count:** 타격 횟수 (다단 히트 시 데미지 편차 보정 효과)

### 4. `Monster_Book` & `Dungeon_Config` (환경 설정)
*   **HP / ATK:** 몬스터의 체력(TTK 검증용)과 공격력(유저 생존 검증용)
*   **Rec_Party_Size:** 던전의 권장 파티원 수 (1인, 4인, 8인 등)
*   **Time_Limit_Sec:** 보스 광폭화(Time Over) 제한 시간

### 5. `Payment_Grade` (BM 밸런스)
*   **Stat_Multiplier:** 무과금(1.0) 대비 등급별 스탯 배율 (예: Heavy = 15.0)

---

## 💡 기획적 통찰 (Design Insights)

이 도구를 통해 다음과 같은 밸런스 이슈를 사전에 방지할 수 있습니다.

*   **OP/UP 밸런스 조절:** 특정 직업의 실제 DPS가 기획 의도(Target)를 벗어나는 구간을 감지합니다.
*   **레이드 피로도 관리:** 이론상 클리어 타임(TTK)이 너무 길거나 짧은 던전을 찾아내어 보스 체력을 조절합니다.
*   **P2W 리스크 관리:** 고과금 유저의 효율이 생태계를 파괴할 수준인지, 투자 대비 효율이 낮은지를 수학적으로 진단합니다.
