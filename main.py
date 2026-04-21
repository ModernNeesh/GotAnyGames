import pandas as pd
from api_functions import *
from data_cleaning_functions import *


access_token = get_access_token()
df = get_multiplayer_games(access_token)
download_feature_id_maps(df, access_token)



df = split_list_column(df, 'genres')
if len(df) > 0:
    df.to_csv('multiplayer_games.csv', index=False)











