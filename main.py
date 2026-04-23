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
print(ACCESS_TOKEN)
df = get_games(ACCESS_TOKEN)

#Process data
df = split_list_columns(df, ACCESS_TOKEN)
df = deduplicate(df)


#Save cleaned data
if len(df) > 0:
    clean_games_fp = Path(config['games_folder'] + config['games_clean_fp'])
    logging.info("Saving cleaned games dataframe to: %s", clean_games_fp)
    df.to_json(clean_games_fp, orient='records', date_format='iso')
    logging.info("Saved cleaned games dataframe with %s records", len(df))
