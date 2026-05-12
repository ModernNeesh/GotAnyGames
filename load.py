import pandas as pd
from src.sql_loading_helpers import *
from dotenv import load_dotenv
import os
import yaml

load_dotenv()
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")

# Load config
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

#Start logging
logging.basicConfig(filename='logging/app.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

logging.info("Beginning load step...")

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
            logging.info(f"Loading table {tablename_formatted}...")

            df = pd.read_json(filepath_formatted, orient='records')
            update_data_with_pkey(df, tablename_formatted, has_updated_at = True)
    else:        
        logging.info(f"Loading table {tablename}...")
        df = pd.read_json(filepath, orient='records')

        if 'first_release_date' in df.columns:
            df['first_release_date'] = pd.to_datetime(df['first_release_date'], unit='s')
        has_updated_at = not ('multiplayer_modes' in filepath)
        update_data_with_pkey(df, tablename, has_updated_at = has_updated_at)


for filepath_config, (parent_folder, tablename) in tables_without_pkeys:
    filepath = config[parent_folder] + config[filepath_config]
    if r'{field}' in filepath:
        fields = config['feature_fields']
        for field in fields:
            filepath_formatted = filepath.format(field=field)
            tablename_formatted = tablename.format(field=field)
            logging.info(f"Loading table {tablename_formatted}...")

            df = pd.read_json(filepath_formatted, orient='records')
            update_data_without_pkey(df, tablename_formatted)
    else:        
        df = pd.read_json(filepath, orient='records')
        update_data_without_pkey(df, tablename)

logging.info("Load step complete!")