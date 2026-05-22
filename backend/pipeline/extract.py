import pandas as pd
from src.api_functions import *
from pathlib import Path
import yaml
import logging

#Load configs
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

"""
Extracts raw data from IGDB database

Requires no prior data.

Writes raw data from games and multiplayer modes endpoints to JSON files.
Writes lookup and junction data for various features to JSON files.
"""

#Start logging
logging.basicConfig(filename='logging/app.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


#Get access token and games data
ACCESS_TOKEN = get_access_token()
games_df = get_games(ACCESS_TOKEN)


#Separate features that need their own lookup/junction tables
features_columns =  [column for column in games_df 
                    if games_df[column].dtype == 'object' and games_df[column].apply(lambda x: isinstance(x, list)).any()]

features_df = games_df[['id'] + features_columns]



#Get lookup and junction tables from features
get_lookup_and_junction(features_df, ACCESS_TOKEN)

#Get covers data
get_covers(ACCESS_TOKEN)

#Get multiplayer modes data
get_multiplayer_modes(ACCESS_TOKEN)

logging.info("Extraction step done.")