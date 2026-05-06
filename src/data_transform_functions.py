import pandas as pd
import logging
import yaml
from pathlib import Path
from src.data_cleaning_helpers import deduplicate, fix_conflicted_coop_columns, drop_all_outliers
import os

# Load config
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)



def clean_games_data(games_df):
    """
    Function to clean games dataframe through the following:
    1. Drop columns that are for list features
    2. Handle missing values.
    3. Set appropriate data types for each column 
    4. Deduplicate dataframe so that the id column is unique, keeping the most recent entry.
    

    Inputs:
    df (pd.DataFrame): Games dataframe to be cleaned

    Returns:
    cleaned_df (pd.DataFrame): Cleaned games dataframe
    """

    #1. Drop columns that are for list features
    features_columns =  [column for column in games_df 
                        if games_df[column].dtype == 'object' and 
                        games_df[column].apply(lambda x: isinstance(x, list)).any()]
    
    cleaned_df = games_df.drop(columns = features_columns)

    #2. Handle missing values (maintain column data type while adding impossible values)
    cleaned_df = cleaned_df.fillna({'rating': -1, 'first_release_date': pd.Timestamp(year=1776, month=7, day = 4)})

    #3. Set appropriate data types for each column
    dtypes = config['games_dtypes']
    cleaned_df = cleaned_df.astype(dtypes)

    #4. Deduplicate dataframe so that the id column is unique, keeping the most recent entry.
    cleaned_df = deduplicate(cleaned_df)

    #Save cleaned games data
    if len(cleaned_df) > 0:
        clean_games_fp = Path(config['games_folder'] + config['games_clean_fp'])
        logging.info("Saving cleaned games dataframe to: %s", clean_games_fp)
        cleaned_df.to_json(clean_games_fp, orient='records', date_format='iso')
        logging.info("Saved cleaned games dataframe with %s records", len(games_df))

    return cleaned_df








def clean_multiplayer_modes_data(modes_df, coop_data, missing_game_ids):
    """
    Function to clean multiplayer modes dataframe through the following:
    1. Drop rows where the game id is missing from the games data.
    2. Set appropriate data types for each column and handle missing values.
    3. Fix rows where columns give conflicting information
    4. Drop outliers in relevant columns

    Inputs:
    modes_df (pd.DataFrame): Multiplayer modes dataframe to be cleaned
    games_df (pd.DataFrame): Cleaned games dataframe; to be used when handling conflicts

    Returns:
    cleaned_df (pd.DataFrame): Cleaned multiplayer modes dataframe
    """
    logging.info("Cleaning multiplayer modes dataframe...")


    #1. Drop rows where the game id is missing from the games data. We can't get the names for these games.
    cleaned_df = modes_df.drop(index = missing_game_ids)

    #2. Set appropriate data types for each column and handle missing values. 
    dtypes = config['multiplayer_modes_dtypes']
    cleaned_df = cleaned_df.fillna(-1).astype(dtypes)

    #3. Fix rows that give conflicting information
    cleaned_df = fix_conflicted_coop_columns(cleaned_df, coop_data)

    #4. Drop outliers in relevant columns
    cleaned_df = drop_all_outliers(cleaned_df)

    #Save cleaned multiplayer modes data
    if len(cleaned_df) > 0:
        clean_multiplayer_modes_fp = Path(config['multiplayer_modes_folder'] + config['multiplayer_modes_clean_fp'])
        logging.info("Saving cleaned multiplayer modes dataframe to: %s", clean_multiplayer_modes_fp)
        cleaned_df.to_json(clean_multiplayer_modes_fp, orient='records', date_format='iso')
        logging.info("Saved cleaned multiplayer modes dataframe with %s records", len(cleaned_df))


    return cleaned_df







def get_coop_games_data():
    """
    Get data that indicates whether a game supports Co-Operative gameplay

    Requires junction and lookup tables to already exist for game modes data

    Returns:
    id_to_coop_df (pd.DataFrame): DataFrame indicating whether a game supports co-op
    """
    game_modes_junction_fp = Path(config['junctions_folder'] + config['junctions_fp_template'].format(field='game_modes'))

    game_modes_lookup_fp = Path(config['lookups_folder'] + config['lookups_fp_template'].format(field='game_modes'))

    assert os.path.exists(game_modes_junction_fp) and os.path.exists(game_modes_lookup_fp), "Game modes data must exist"

    game_modes_junction = pd.read_json(game_modes_junction_fp, orient='records')
    game_modes_lookup = pd.read_json(game_modes_lookup_fp, orient='records')

    id_to_coop_df = game_modes_junction.merge(game_modes_lookup, how = 'inner', left_on = 'game_modes_id', right_on = 'id')

    id_to_coop_df = id_to_coop_df[['game_id', 'name']]

    id_to_coop_df.columns = ['id', 'game_modes']

    id_to_coop_df = pd.get_dummies(id_to_coop_df, columns = ['game_modes']).groupby('id').sum().reset_index().astype(int)

    id_to_coop_df = id_to_coop_df[['id','game_modes_Co-operative']]

    assert len(id_to_coop_df['id'].unique()) == len(id_to_coop_df), "IDs should be unique"

    return id_to_coop_df