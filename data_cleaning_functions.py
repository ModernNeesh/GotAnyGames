import pandas as pd
import logging
import yaml
from api_functions import get_feature_names

# Load config
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

def ids_to_names(df, column, access_token):
    """
    Function to convert a column of lists of ids to a column of lists of names using the corresponding id-to-name map csv.

    Inputs: 
    df (pd.DataFrame): Dataframe containing the column to be converted
    column (str): Name of the column to be converted

    Returns:
    new_col (pd.Series): Series containing the converted column
    """
    names_df = get_feature_names(column, access_token)
    id_to_name = dict(zip(names_df['id'], names_df['name']))
    new_col = df[column].apply(lambda ids: [id_to_name.get(i, "Unknown") for i in ids] if isinstance(ids, list) else ids)
    return new_col


def split_list_columns(df, access_token):
    """
    Function to clean list-type columns through the following:
    1. Convert lists of ids to lists of names using the corresponding id-to-name map csv.
    2. Expand lists of names into one-hot columns for each name.

    Inputs:
    df (pd.DataFrame): Dataframe containing the columns to be cleaned

    Returns:
    new_df (pd.DataFrame): Dataframe with cleaned columns
    """
    new_df = df.copy()
    columns = new_df.columns
    for col in columns:
        if new_df[col].dtype == 'object' and new_df[col].apply(lambda x: isinstance(x, list)).any():
            logging.info("Cleaning column: %s", col)
            subbed_col = ids_to_names(new_df, col, access_token) #Convert ids to names
            expanded_cols = pd.get_dummies(subbed_col.explode(), prefix=col).groupby(level=0).sum().astype(int) #Expand into one-hot columns
            new_df = pd.concat([new_df.drop(col, axis=1), expanded_cols], axis=1) #Concatenate with original dataframe
            logging.info("Finished cleaning column: %s", col)
    return new_df


def deduplicate(df):
    """
    Deduplicate dataframe so that the id column is unique.
    Drop duplicates by keeping the most recent entry (highest value of updated_at).
    Saves output to 

    Inputs:
    df (pd.DataFrame): Dataframe to be deduplicated
    
    Returns:
    deduplicated_df (pd.DataFrame): Dataframe with unique id values, keeping most recent entries
    """
    logging.info("Deduplicating dataframe by id column")
    # Convert updated_at to datetime to handle mixed type columns
    df['updated_at'] = pd.to_datetime(df['updated_at'], unit='s', errors='coerce')
    
    # Sort by updated_at in descending order to keep the most recent entries
    df_sorted = df.sort_values('updated_at', ascending=False)

    # Drop duplicates, keeping the first occurrence (most recent due to sort)
    deduplicated_df = df_sorted.drop_duplicates(subset=['id'], keep='first')

    # Reset index to maintain clean indexing
    deduplicated_df = deduplicated_df.reset_index(drop=True)
    logging.info("Deduplication complete. Removed %d duplicate entries", len(df) - len(deduplicated_df))
    return deduplicated_df


def clean_games_data(games_df, access_token):
    """
    Function to clean games dataframe through the following:
    1. Convert lists of ids to lists of names using the corresponding id-to-name map csv.
    2. Expand lists of names into one-hot columns for each name.
    3. Deduplicate dataframe so that the id column is unique, keeping the most recent entry.

    Inputs:
    df (pd.DataFrame): Games dataframe to be cleaned

    Returns:
    cleaned_df (pd.DataFrame): Cleaned games dataframe
    """
    dtypes = config['games_dtypes']
    cleaned_df = games_df.astype(dtypes)
    cleaned_df = split_list_columns(cleaned_df, access_token)
    cleaned_df = deduplicate(cleaned_df)
    return cleaned_df



def clean_multiplayer_modes_data(modes_df, ACCESS_TOKEN):
    """
    Function to clean multiplayer modes dataframe through the following:
    1. Set appropriate data types for each column and handle missing values.
    2. Fix conflicting rows 
    3. Convert platform ids to names using the corresponding id-to-name map csv.

    Inputs:
    df (pd.DataFrame): Multiplayer modes dataframe to be cleaned

    Returns:
    cleaned_df (pd.DataFrame): Cleaned multiplayer modes dataframe
    """
    logging.info("Cleaning multiplayer modes dataframe...")

    dtypes = config['multiplayer_modes_dtypes']
    cleaned_df = modes_df.fillna(-1).astype(dtypes)
    cleaned_df = fix_conflicted_columns(cleaned_df, **config['multiplayer_modes_conflicts']['online']) 
    cleaned_df = fix_conflicted_columns(cleaned_df, **config['multiplayer_modes_conflicts']['offline'])

    platform_df_fp = config['feature_maps_folder'] + config['feature_maps_fp_template'].format(field='platforms')
    platform_id_to_name = pd.read_json(platform_df_fp, orient='records')
    platform_id_to_name_dict = dict(zip(platform_id_to_name['id'], platform_id_to_name['name']))

    cleaned_df['platform'] = cleaned_df['platform'].apply(lambda x: platform_id_to_name_dict.get(x, "Unknown"))

    return cleaned_df






def conflicting_rows(df, bool_col, max_col_1, max_col_2):
    """
    Function to check for conflicting rows based on a boolean column and a maximum value column.

    Inputs: 
    bool_col: column name of the boolean column to check for conflicts
    max_col_1: column name of the first column with maximum values
    max_col_2: column name of the second column with maximum values

    Output:
    Prints out the rows where bool_col is True but max_col is 0 or where bool_col is False but max_col is greater than 0
    """
    conflicts = (((df[bool_col] == True) & (df[max_col_1] <= 0) & (df[max_col_2] <= 0)) |
                  ((df[bool_col] == False) & (df[max_col_1] > 0) & (df[max_col_2] > 0)))
    return conflicts




def fix_conflicted_columns(df, bool_col, max_col_1, max_col_2):
    """
    Function to fix conflicting rows based on a boolean column and a maximum value column.

    Inputs: 
    bool_col: column name of the boolean column to check for conflicts
    max_col: column name of the column with maximum values

    Output:
    Returns a dataframe with the conflicting rows fixed by setting the boolean column to False and the maximum value columns to 0
    """
    new_df = df.copy()
    new_df.loc[conflicting_rows(new_df, bool_col, max_col_1, max_col_2), bool_col] = False
    new_df.loc[conflicting_rows(new_df, bool_col, max_col_1, max_col_2), max_col_1] = 0
    new_df.loc[conflicting_rows(new_df, bool_col, max_col_1, max_col_2), max_col_2] = 0
    return new_df