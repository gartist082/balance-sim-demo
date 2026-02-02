import pandas as pd
import numpy as np
from data_manager import get_growth_stat

class Character:
    def __init__(self, level, class_row, growth_df, skills_df):
        self.level = level
        self.name = class_row['Class_Name']
        
        # 스탯 로드
        base_hp = get_growth_stat(level, growth_df, 'Base_HP')
        base_mp = get_growth_stat(level, growth_df, 'Base_MP')
        base_stat = get_growth_stat(level, growth_df, 'Base_Primary_Stat')
        base_def = get_growth_stat(level, growth_df, 'Base_DEF')
        
        self.max_hp = base_hp * class_row['Base_HP_Mod']
        self.current_hp = self.max_hp
        self.max_mp = base_mp
        self.current_mp = self.max_mp
        
        str_atk = base_stat * class_row['Stat_Weight_Str']
        int_atk = base_stat * class_row['Stat_Weight_Int']
        self.atk = max(str_atk, int_atk)
        self.defense = base_def * class_row['Base_Def_Mod']
        
        # [수정] 치명타율 로드 (값이 없으면 기본 10% 적용)
        self.crit_rate = 0.1
        for col in class_row.index:
            if 'crit' in col.lower() and 'rate' in col.lower():
                val = float(class_row[col])
                if val > 0: self.crit_rate = val
                break
        
        self.crit_dmg = 1.5
        
        # 스킬 설정
        if skills_df is not None:
            self.skills = skills_df[skills_df['Class_Name'] == self.name].copy()
            self.skills['next_available'] = 0.0
        else:
            self.skills = pd.DataFrame()

        self.current_time = 0.0
        self.is_casting = False
        self.cast_end_time = 0.0
        self.total_damage = 0
        self.damage_log = []

    def update(self, time_step):
        self.current_time += time_step
        if self.current_mp < self.max_mp:
            self.current_mp += self.max_mp * 0.05 * time_step
        
        if self.is_casting:
            if self.current_time >= self.cast_end_time:
                self.is_casting = False
            else:
                return 0

        if not self.skills.empty:
            ready = self.skills[
                (self.skills['next_available'] <= self.current_time) & 
                (self.skills['MP_Cost'] <= self.current_mp)
            ].sort_values(by='Dmg_Percent', ascending=False)
            
            if not ready.empty:
                return self.use_skill(ready.iloc[0])
        
        return self.basic_attack()

    def use_skill(self, skill):
        self.current_mp -= skill['MP_Cost']
        
        # 치명타 적용
        is_crit = np.random.random() < self.crit_rate
        dmg_mult = self.crit_dmg if is_crit else 1.0
        
        dmg = self.atk * (skill['Dmg_Percent'] / 100.0) * dmg_mult
        
        self.total_damage += dmg
        self.damage_log.append({
            'Time': round(self.current_time, 2),
            'Type': 'Skill',
            'Name': skill['Skill_Name'],
            'Damage': int(dmg),
            'Cumulative': int(self.total_damage),
            'Is_Crit': is_crit
        })
        
        self.is_casting = True
        self.cast_end_time = self.current_time + skill['Cast_Time']
        self.skills.at[skill.name, 'next_available'] = self.current_time + skill['Cooldown']
        return dmg

    def basic_attack(self):
        if int(self.current_time * 10) % 10 == 0: 
            is_crit = np.random.random() < self.crit_rate
            dmg_mult = self.crit_dmg if is_crit else 1.0
            
            dmg = self.atk * dmg_mult
            self.total_damage += dmg
            self.damage_log.append({
                'Time': round(self.current_time, 2),
                'Type': 'Attack',
                'Name': 'Basic Attack',
                'Damage': int(dmg),
                'Cumulative': int(self.total_damage),
                'Is_Crit': is_crit
            })
            return dmg
        return 0
