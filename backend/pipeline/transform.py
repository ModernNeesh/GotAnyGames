import pandas as pd
from src.data_transform_functions import *
from pathlib import Path
import yaml
import logging

PIPELINE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = PIPELINE_DIR / "config.yaml"
LOGGING_DIR = PIPELINE_DIR / "logging"

#Load configs
with CONFIG_PATH.open("r") as f:
    config = yaml.safe_load(f)

"""
Cleans raw data.

Requires raw data from games and multiplayer modes endpoints (stored as JSON files).
Requires lookup and junction data for 'game_modes' feature.

Writes clean data from games and multiplayer modes endpoints to JSON files.
"""
#Start logging
LOGGING_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(filename=LOGGING_DIR / 'app.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

logging.info("Beginning transformation step...")

#Read in raw games data
raw_games_fp = PIPELINE_DIR / config['games_folder'] / config['games_raw_fp']

games_df = pd.read_json(raw_games_fp, orient='records')

#Read in covers data
covers_fp = PIPELINE_DIR / config['covers_folder'] / config['covers_fp']

covers_df = pd.read_json(covers_fp, orient='records')

#Process games data
games_df = clean_games_data(games_df, covers_df)



#Read in raw multiplayer modes data
raw_modes_fp = PIPELINE_DIR / config['multiplayer_modes_folder'] / config['multiplayer_modes_raw_fp']

modes_df = pd.read_json(raw_modes_fp, orient='records')

#Process multiplayer modes data
coop_games_data = get_coop_games_data()

excluded_ids_mask = ~modes_df['game'].isin(games_df['id'])
excluded_ids_index = modes_df[excluded_ids_mask].index

modes_df = clean_multiplayer_modes_data(modes_df, coop_games_data, missing_game_ids=excluded_ids_index)


logging.info("Transform step done.")