import pandas as pd
from src.data_transform_functions import *
from pathlib import Path
import yaml
import logging

#Load configs
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

"""
Cleans raw data.

Requires raw data from games and multiplayer modes endpoints (stored as JSON files).
Requires lookup and junction data for 'game_modes' feature.

Writes clean data from games and multiplayer modes endpoints to JSON files.
"""
#Start logging
logging.basicConfig(filename='logging/app.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

logging.info("Beginning transformation step: ")

#Read in raw games data
raw_games_fp = Path(config['games_folder'] + config['games_raw_fp'])

games_df = pd.read_json(raw_games_fp, orient='records')

#Process games data
games_df = clean_games_data(games_df)



#Read in raw multiplayer modes data
raw_modes_fp = Path(config['multiplayer_modes_folder'] + config['multiplayer_modes_raw_fp'])

modes_df = pd.read_json(raw_modes_fp, orient='records')

#Process multiplayer modes data
coop_games_data = get_coop_games_data()

excluded_ids_mask = ~modes_df['game'].isin(games_df['id'])
excluded_ids_index = modes_df[excluded_ids_mask].index

modes_df = clean_multiplayer_modes_data(modes_df, coop_games_data, missing_game_ids=excluded_ids_index)


logging.info("Transform step done.")