# ⚔️ MMORPG Combat Balance Simulator (Pro Ver.)

> **Role:** Lead Balance Designer (Candidate)  
> **Core Concept:** Data-Driven Combat Verification & Monte Carlo Simulation  
> **Live Demo:** [![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://balance-sim-demo-fymypnl2dqsefveoluyf8l.streamlit.app/)

## 🎯 Project Objective
MMORPG 밸런싱의 핵심인 **'지속 가능한 전투 환경'**과 **'확률적 변수 제어'**를 위한 자동화 검증 도구입니다.

기존 엑셀(Static) 계산의 한계를 넘어, **Time-stream(시간 흐름)** 기반의 시뮬레이션을 통해 스킬 사이클, 자원(MP) 관리, 그리고 확률(Crit/BackAttack)에 따른 **DPS 편차(Standard Deviation)**를 정량적으로 분석하는 데 초점을 맞췄습니다.

---

## 🛠 Key Features

### 1. Hybrid Simulation Engine (Single & Monte Carlo)
단순한 1회성 검증을 넘어, 통계적 신뢰성을 확보하기 위한 두 가지 모드를 지원합니다.
*   **Single Run (Process Verification):**
    *   초(sec) 단위 로그를 통해 스킬 쿨타임 정렬, 자원 소모, 선/후딜레이 로직이 기획 의도대로 작동하는지 검증합니다.
*   **Monte Carlo Simulation (Statistical Verification):**
    *   치명타, 백어택 등 확률 변수가 포함된 전투를 **대규모(N=100~1,000) 반복 시행**합니다.
    *   이를 통해 **'운 좋은 유저(Max DPS)'**와 **'운 나쁜 유저(Min DPS)'**의 격차를 시각화하여 밸런스 리스크를 사전 감지합니다.

### 2. A/B Testing Environment (Live Tuning)
*   **실시간 비교:** 엑셀을 수정해서 다시 올릴 필요 없이, 웹 UI에서 즉시 수치(공격력, 쿨감 등)를 조절하여 **Original vs Tuned** 결과를 그래프로 비교합니다.
*   **의사결정 지원:** "공격력을 5% 올리면 실제 DPS는 얼마나 오르는가?"에 대한 답을 즉각적으로 도출합니다.

### 3. Resource & Mechanics Logic
단순 DPS 계산기가 아닌, 실제 인게임 매커니즘을 반영했습니다.
*   **MP Management:** 마나가 부족하면 스킬 사용을 중단하고 회복(Regen)을 기다리는 '딜 로스(Deal Loss)' 상황 구현.
*   **Action Logic:** 백어택(Back Attack) 성공 확률 변수 및 다단 히트(Multi-hit)별 개별 치명타 판정 적용.

---

## 🧩 Design Rationale (기획 의도)

이 시뮬레이터의 주요 설정값은 다음과 같은 기획적 근거를 바탕으로 설계되었습니다.

| 설정 항목 | 설정값 (Default) | 기획적 근거 (Rationale) |
| :--- | :--- | :--- |
| **Min Combat Time** | **30 sec** | 주요 스킬의 쿨타임(10~15초)이 최소 2회 이상 순환(Rotation)되어야 유의미한 평균 DPS 산출 가능. |
| **Max Combat Time** | **180 sec (3 min)** | 모바일/PC MMORPG 레이드 보스의 일반적인 페이즈 전환 및 광폭화(Enrage) 기준 시간. **마나(MP) 고갈에 따른 지속 딜링 능력(Sustain)**을 검증하기 위함. |
| **Monte Carlo** | **N Iterations** | 단일 실행 시 발생하는 난수(Random Seed) 편향을 제거하고, 정규분포에 근사한 **모수적 특성**을 파악하기 위함. |

---

## 📂 Data Protocol (Excel Schema)

이 시뮬레이터는 약속된 **데이터 규격(Schema)**을 준수하는 엑셀 파일을 통해 동작합니다. (`BalanceSheets.xlsx` 참조)

### Sheet 1: Stats (Character Spec)
| Column | Description | Note |
| :--- | :--- | :--- |
| `Class` | 클래스명 (Key) | Warrior, Mage 등 |
| `Base_ATK` | 기본 공격력 | |
| `Crit_Rate` | 치명타 확률 | 0.0 ~ 1.0 (0% ~ 100%) |
| `Crit_Dmg` | 치명타 배율 | 2.0 = 200% 데미지 |
| `Cooldown_Reduction` | 쿨타임 감소율 | 스킬 회전율에 영향 |
| `Back_Attack_Bonus` | 백어택 추뎀 배율 | 컨트롤 요소 반영 |
| `Max_MP` / `MP_Regen` | 자원 총량 및 회복 | **지속 전투 능력 제어 변수** |

### Sheet 2: Skills (Action Logic)
| Column | Description | Note |
| :--- | :--- | :--- |
| `Skill_Name` | 스킬명 | |
| `Cooldown` | 재사용 대기시간 | |
| `Damage_Coef` | 데미지 계수 | 공격력의 N배 |
| `Cast_Time` | 시전 시간 | **Action Delay (선후딜)** 반영 |
| `Is_BackAttack` | 백어택 가능 여부 | TRUE / FALSE |
| `MP_Cost` | 마나 소모량 | 0일 경우 평타(Basic Attack)로 간주 |
| `Hit_Count` | 타격 횟수 | 다단 히트 시 치명타 개별 판정 |

---

## 💻 Tech Stack & Usage
*   **Python 3.9** (Core Logic)
*   **Streamlit** (Web Dashboard UI)
*   **Pandas & NumPy** (Data Processing & Probability Calculation)
*   **Plotly** (Interactive Visualization)

### How to Run
1.  우측 상단의 **Live Demo** 배지를 클릭합니다.
2.  `BalanceSheets.xlsx` 파일을 업로드하거나 기본 데이터를 사용합니다.
3.  좌측 사이드바에서 수치를 조정(Tuning)합니다.
4.  **[단일 전투 실행]**으로 로직을 검증하고, **[몬테카를로 시뮬레이션]**으로 확률적 안정성을 검증합니다.
