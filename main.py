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


#Separate features that need their own lookup/junction tables
features_columns =  [column for column in games_df 
                    if games_df[column].dtype == 'object' and games_df[column].apply(lambda x: isinstance(x, list)).any()]

features_df = games_df[['id'] + features_columns]
games_df = games_df.drop(columns = features_columns)


#Get lookup and junction tables from features
get_lookup_and_junction(features_df, ACCESS_TOKEN)

#Process games data
games_df = clean_games_data(games_df)




#Save cleaned games data
if len(games_df) > 0:
    clean_games_fp = Path(config['games_folder'] + config['games_clean_fp'])
    logging.info("Saving cleaned games dataframe to: %s", clean_games_fp)
    games_df.to_json(clean_games_fp, orient='records', date_format='iso')
    logging.info("Saved cleaned games dataframe with %s records", len(games_df))

#Get multiplayer modes data
multiplayer_modes_df = get_multiplayer_modes(ACCESS_TOKEN)


coop_games_data = get_coop_games_data()
#Process multiplayer modes data
multiplayer_modes_df = clean_multiplayer_modes_data(multiplayer_modes_df, coop_games_data)


#Save cleaned multiplayer modes data
if len(multiplayer_modes_df) > 0:
    clean_multiplayer_modes_fp = Path(config['multiplayer_modes_folder'] + config['multiplayer_modes_clean_fp'])
    logging.info("Saving cleaned multiplayer modes dataframe to: %s", clean_multiplayer_modes_fp)
    multiplayer_modes_df.to_json(clean_multiplayer_modes_fp, orient='records', date_format='iso')
    logging.info("Saved cleaned multiplayer modes dataframe with %s records", len(multiplayer_modes_df))


logging.info("Done!")