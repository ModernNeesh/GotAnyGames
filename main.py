import pandas as pd
from api_functions import *
from data_cleaning_functions import *
from pathlib import Path
import yaml
import logging


with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

logging.basicConfig(filename='logging/app.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

ACCESS_TOKEN = get_access_token()
df = get_multiplayer_games(ACCESS_TOKEN)
download_feature_id_maps(df, ACCESS_TOKEN)



df = split_list_columns(df)
if len(df) > 0:
    clean_multiplayer_games_fp = Path(config['multiplayer_games_folder'] + config['multiplayer_games_clean_fp'])
    logging.info("Saving cleaned multiplayer games dataframe to: %s", clean_multiplayer_games_fp)
    df.to_csv(clean_multiplayer_games_fp, index=False)
    logging.info("Saved cleaned multiplayer games dataframe with %s records", len(df))











