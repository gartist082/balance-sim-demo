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
        
        # 직업 보정
        self.max_hp = base_hp * class_row['Base_HP_Mod']
        self.current_hp = self.max_hp
        self.max_mp = base_mp
        self.current_mp = self.max_mp
        
        # 공격력
        str_atk = base_stat * class_row['Stat_Weight_Str']
        int_atk = base_stat * class_row['Stat_Weight_Int']
        self.atk = max(str_atk, int_atk)
        
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
        dmg = self.atk * (skill['Dmg_Percent'] / 100.0)
        
        self.total_damage += dmg
        self.damage_log.append({
            'Time': round(self.current_time, 2),
            'Type': 'Skill',
            'Name': skill['Skill_Name'],
            'Damage': int(dmg),
            'Cumulative': int(self.total_damage)
        })
        
        self.is_casting = True
        self.cast_end_time = self.current_time + skill['Cast_Time']
        self.skills.at[skill.name, 'next_available'] = self.current_time + skill['Cooldown']
        return dmg

    def basic_attack(self):
        if int(self.current_time * 10) % 10 == 0:
            dmg = self.atk
            self.total_damage += dmg
            self.damage_log.append({
                'Time': round(self.current_time, 2),
                'Type': 'Attack',
                'Name': 'Basic Attack',
                'Damage': int(dmg),
                'Cumulative': int(self.total_damage)
            })
            return dmg
        return 0
