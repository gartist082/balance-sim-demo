import pandas as pd
import streamlit as st

# [수정] ttl=0 제거 (화면 깜빡임 및 탭 튕김 방지)
@st.cache_data
def load_excel_data(uploaded_file):
    try:
        xls = pd.ExcelFile(uploaded_file)
        data_dict = {}
        
        # 필수 시트 목록
        required = ['Class_Job', 'Growth_Table', 'Skill_Data', 'Monster_Book', 'Dungeon_Config']
        
        # 시트 이름 매핑 (공백 제거 등 유연하게 처리)
        sheet_names = xls.sheet_names
        normalized = {name.strip(): name for name in sheet_names}
        
        for req in required:
            if req in normalized:
                real_name = normalized[req]
                df = pd.read_excel(xls, real_name)
                df.columns = df.columns.str.strip()
                data_dict[req] = df
            else:
                # Payment_Grade는 선택사항이므로 에러 처리에서 제외 가능하나, 여기선 필수 체크
                if req != 'Payment_Grade': 
                    pass 
        
        # 선택 사항: Payment_Grade
        if 'Payment_Grade' in normalized:
             data_dict['Payment_Grade'] = pd.read_excel(xls, normalized['Payment_Grade'])
             
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
