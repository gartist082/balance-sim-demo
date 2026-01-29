import random
import pandas as pd

def load_params(csv_path="BalanceParams.csv"):
    df = pd.read_csv(csv_path)
    players = df[df['role']=='player'].to_dict(orient='records')
    enemies = df[df['role']=='enemy'].to_dict(orient='records')
    if not players or not enemies:
        raise ValueError("CSV must contain at least one player and one enemy.")
    return players[0], enemies[0]

def compute_damage(attacker, defender):
    # 방어 무시 반영
    mitigation = defender['def'] * (1 - attacker.get('armor_pen', 0))
    # 회피 체크
    if random.random() < defender.get('dodge_rate', 0):
        return 0, 'evade'
    # 기본 피해
    raw = max(1, attacker['atk'] - mitigation)
    # 크리티컬 체크
    is_crit = random.random() < attacker.get('crit_rate', 0)
    dmg = raw * (attacker['crit_mult'] if is_crit else 1)
    return dmg, ('crit' if is_crit else 'hit')

def simulate_once(player, enemy, max_turns=100):
    p_hp, e_hp = player['hp'], enemy['hp']
    turns = 0
    while p_hp > 0 and e_hp > 0 and turns < max_turns:
        turns += 1
        dmg, _ = compute_damage(player, enemy)
        e_hp -= dmg
        if e_hp <= 0:
            return {'winner':'player', 'turns':turns}
        dmg, _ = compute_damage(enemy, player)
        p_hp -= dmg
        if p_hp <= 0:
            return {'winner':'enemy', 'turns':turns}
    return {'winner':'draw', 'turns':turns}

def run_simulation(n=200, csv_path="BalanceParams.csv"):
    player, enemy = load_params(csv_path)
    results = [simulate_once(player, enemy) for _ in range(n)]
    df = pd.DataFrame(results)
    return df

if __name__ == "__main__":
    df = run_simulation()
    print(df['winner'].value_counts(normalize=True))
    print("평균 턴:", df['turns'].mean())
