import pandas as pd
import streamlit as st

@st.cache_data(ttl=0)
def load_excel_data(uploaded_file):
    try:
        xls = pd.ExcelFile(uploaded_file)
        data_dict = {}
        required = ['Class_Job', 'Growth_Table', 'Skill_Data', 'Monster_Book', 'Dungeon_Config']
        normalized = {name.strip(): name for name in xls.sheet_names}
        
        for req in required:
            if req in normalized:
                df = pd.read_excel(xls, normalized[req])
                df.columns = df.columns.str.strip()
                data_dict[req] = df
            else:
                st.error(f"❌ 필수 시트 누락: {req}")
                return None
        return data_dict
    except Exception as e:
        st.error(f"데이터 로드 오류: {e}")
        return None

def get_growth_stat(level, growth_df, target_col):
    if level in growth_df['Level'].values:
        return growth_df.loc[growth_df['Level'] == level, target_col].values[0]
    
    lower = growth_df[growth_df['Level'] < level]
    upper = growth_df[growth_df['Level'] > level]
    
    if lower.empty: return upper.iloc[0][target_col]
    if upper.empty: return lower.iloc[-1][target_col]
    
    x1, y1 = lower.iloc[-1]['Level'], lower.iloc[-1][target_col]
    x2, y2 = upper.iloc[0]['Level'], upper.iloc[0][target_col]
    
    return y1 + (y2 - y1) * (level - x1) / (x2 - x1)
