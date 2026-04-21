import pandas as pd
from api_functions import get_feature_names


def download_feature_id_maps(df, access_token):
    for col in df.columns:
        if df[col].dtype == 'object' and df[col].apply(lambda x: isinstance(x, list)).any():
            needed_ids = df[col].explode().unique()
            get_feature_names(col, access_token)



def ids_to_names(df, column):
    names_df = pd.read_csv(fr"feature_id_maps/{column}_names.csv")
    id_to_name = dict(zip(names_df['id'], names_df['name']))
    new_col = df[column].apply(lambda ids: [id_to_name.get(i, "Unknown") for i in ids] if isinstance(ids, list) else [])
    return new_col


def split_list_column(df, column):
    new_df = df.copy()
    for col in new_df.columns:
        if new_df[col].dtype == 'object' and new_df[col].apply(lambda x: isinstance(x, list)).any():
            subbed_col = ids_to_names(new_df, col)
            expanded_cols = expanded_cols = pd.get_dummies(subbed_col.explode()).groupby(level=0).sum().astype(int)
            new_df = pd.concat([new_df.drop(col, axis=1), expanded_cols], axis=1)
    
    return new_df