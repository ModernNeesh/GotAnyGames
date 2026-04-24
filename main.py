import pandas as pd
from api_functions import *
from data_cleaning_functions import *
from pathlib import Path
import yaml
import logging

#Load configs
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

#Start logging
logging.basicConfig(filename='logging/app.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


#Get access token and games data
ACCESS_TOKEN = get_access_token()
games_df = get_games(ACCESS_TOKEN)

#Process data
games_df = split_list_columns(games_df, ACCESS_TOKEN)
games_df = deduplicate(games_df)


#Save cleaned data
if len(games_df) > 0:
    clean_games_fp = Path(config['games_folder'] + config['games_clean_fp'])
    logging.info("Saving cleaned games dataframe to: %s", clean_games_fp)
    games_df.to_json(clean_games_fp, orient='records', date_format='iso')
    logging.info("Saved cleaned games dataframe with %s records", len(games_df))


multiplayer_modes_df = get_multiplayer_modes(ACCESS_TOKEN)
if len(multiplayer_modes_df) > 0:
    clean_multiplayer_modes_fp = Path(config['multiplayer_modes_folder'] + config['multiplayer_modes_clean_fp'])
    logging.info("Saving cleaned multiplayer modes dataframe to: %s", clean_multiplayer_modes_fp)
    multiplayer_modes_df.to_json(clean_multiplayer_modes_fp, orient='records', date_format='iso')
    logging.info("Saved cleaned multiplayer modes dataframe with %s records", len(multiplayer_modes_df))
