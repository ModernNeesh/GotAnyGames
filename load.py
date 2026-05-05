import pandas as pd
import sqlalchemy as sa
from src.sql_loading_helpers import *
from dotenv import load_dotenv
import os
import yaml
from pathlib import Path

load_dotenv()
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")

# Load config
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

# Create the engine
engine = sa.create_engine(f'postgresql://postgres:{POSTGRES_PASSWORD}@localhost:5432/GamesDatabase')

#Start logging
logging.basicConfig(filename='logging/app.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')



#First: Lookup data, games data
#Second: Multiplayer modes data
#Third: Junction data

tables_with_pkeys = list(config['tablenames']['with_pkey'].items())
tables_without_pkeys = list(config['tablenames']['without_pkey'].items())

#print(tables_with_pkeys)
#print(tables_without_pkeys)

for filepath_config, (parent_folder, tablename) in tables_with_pkeys:
    filepath = config[parent_folder] + config[filepath_config]

    if r'{field}' in filepath:
        fields = config['feature_fields']
        for field in fields:
            filepath_formatted = filepath.format(field=field)
            tablename_formatted = tablename.format(field=field)
            df = pd.read_json(filepath_formatted, orient='records')
            update_data_with_pkey(df, tablename_formatted, has_updated_at = True)
    else:        
        df = pd.read_json(filepath, orient='records')
        has_updated_at = not ('multiplayer_modes' in filepath)
        update_data_with_pkey(df, tablename, has_updated_at = has_updated_at)