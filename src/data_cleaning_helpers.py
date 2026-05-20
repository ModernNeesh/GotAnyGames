import pandas as pd
import logging
import yaml
from pandas.api.types import is_datetime64_any_dtype as is_datetime

# Load config
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)


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
    assert is_datetime(df['updated_at']) or df['updated_at'].dtype == 'int64', "updated_at column must be of datetime or int type for deduplication"
    
    # Sort by updated_at in descending order to keep the most recent entries
    df_sorted = df.sort_values('updated_at', ascending=False)

    # Drop duplicates, keeping the first occurrence (most recent due to sort)
    deduplicated_df = df_sorted.drop_duplicates(subset=['id'], keep='first')

    # Reset index to maintain clean indexing
    deduplicated_df = deduplicated_df.reset_index(drop=True)
    logging.info("Deduplication complete. Removed %d duplicate entries", len(df) - len(deduplicated_df))
    return deduplicated_df


def get_replacement_function(coop_column, coop_max_column, max_column):
    """
    Function to create function that solves conflicts across certain columns in multiplayer modes data.
    i.e., the 'offlinecoop' column may have a value of True, while the 'offlinecoopmax' column has a value of 0. The data from one column contradicts the other.

    Inputs: 
    coop_column (str): The boolean column that specifies whether a multiplayer mode supports online/offline coop 
    coop_max_column (str): The integer column that specifies the maximum number of players for offline coop
    max_column (str): The integer column that specifies the maximum number of players for offline play.

    Returns:
    replace_conflict_columns (function): Function to fix the conflicts in the given set of columns.
    """
    def replace_conflict_columns(row):
        return_row = row.copy()

        #offlinecoop == True
        if row[coop_column]:
            #offlinecoopmax < 0
            if row[coop_max_column] < 0:
                #offlinemax > 0 -- Case 1 
                if row[max_column] > 0:
                    if row['game_modes_Co-operative'] == 1:
                        return_row[coop_max_column] = row[max_column]
                    else:
                        return_row[coop_column] = False
                        return_row[coop_max_column] = 0
                        return_row[max_column] = 0
                #Any potential future cases that could occur
                else:
                    return_row[coop_column] = False
                    return_row[coop_max_column] = 0
                    return_row[max_column] = 0
                    
                
            #offlinecoopmax == 0
            elif row[coop_max_column] == 0 :
                #offlinemax > 0 -- Case 2
                if row[max_column] > 0:
                    return_row[coop_max_column] = row[max_column]
                #Any potential future cases that could occur
                else:
                    return_row[coop_column] = False
                    return_row[coop_max_column] = 0
                    return_row[max_column] = 0

            
            #offlinecoopmax > 0
            else:
                if row[max_column] < 0:
                    return_row[max_column] = 0
                #Uncomment the following line if the distinction between PvP and Co-Op is not made
                #return_row[max_column] = row[coop_max_column]
                pass

        #offlinecoop == False
        else:
            #offlinecoopmax < 0
            if row[coop_max_column] < 0:
                #Nothing else to do here except fill null values
                if row[max_column] < 0:
                    return_row[max_column] = 0
                return_row[coop_max_column] = 0

            #offlinecoopmax == 0
            elif row[coop_max_column] == 0:
                #offlinemax > 0 -- Case 3
                
                #If a game doesn't have any offline play, it can't have splitscreen play
                if "offlinecoop" in coop_column:
                    return_row["splitscreen"] = False

                #We can always assume offlinemax is 0 in this case
                return_row[max_column] = 0

            #offlinecoopmax > 0
            else:
                #offlinemax < 0 -- Case 4
                #offlinemax = 0 -- Case 5

                #If a game doesn't have any offline play, it can't have splitscreen play
                if "offlinecoop" in coop_column:
                    return_row["splitscreen"] = False

                #We can always assume offlinemax is 0 in this case
                return_row[coop_max_column] = 0
                return_row[max_column] = 0

        return return_row
    return replace_conflict_columns




def fix_conflicted_coop_columns(modes_df, games_data):
    """
    Function to fix rows where data conflicts across various columns

    Inputs: 
    modes_df: DataFrame of multiplayer modes data
    games_data: Data of game ids and co-op capability from games data

    Output:
    Returns a dataframe with the conflicting rows fixed 
    """
    assert list(games_data.columns) == ['id', 'game_modes_Co-operative']
    df_with_games = modes_df.merge(games_data, left_on='game', right_on='id', how='left', suffixes=('', '_game'))
    df_with_games = df_with_games.apply(get_replacement_function(**config['multiplayer_modes_conflicts']['online']), axis = 1)
    df_with_games = df_with_games.apply(get_replacement_function(**config['multiplayer_modes_conflicts']['offline']), axis = 1)

    df_with_games.drop(columns = ['id_game', 'game_modes_Co-operative'], inplace = True)

    return df_with_games



def drop_outliers(df, column, threshold):
    """
    Helper function to get outliers for a specific column

    Inputs:
    df (pd.DataFrame): DataFrame to drop outliers from
    column (str): Column whose outliers to drop
    threshold (int): Threshold to consider points as outliers.

    Returns:
    DataFrame with outliers dropped
    """

    column = df[column].sort_values(ascending = False)
    outliers = column[column > threshold]

    return df.drop(index = outliers.index)


def drop_all_outliers(df):
    """
    Drop all outliers from DataFrame
    
    Inputs:
    df (pd.DataFrame): DataFrame to drop outliers from


    Returns:
    return_df: DataFrame with all outliers dropped
    """
    return_df = df.copy()

    columns = config['multiplayer_modes_outlier_columns']
    

    for column in columns:
        if 'online' in column:
            threshold = config['multiplayer_outlier_threshold_online']
        else:
            threshold = config['multiplayer_outlier_threshold_offline']
        return_df = drop_outliers(return_df, column, threshold)
    
    return return_df




def join_cover_data(games_df, cover_df):
    """
    Merges cover data into games dataframe

    Inputs:
    games_df (pd.DataFrame): Data from Games endpoint
    covers_df (pd.DataFrame): Data from Covers endpoint
    
    Returns:
    joined_df (pd.DataFrame): Joined data
    """
    joined_df = games_df.merge(cover_df, how = "left", left_on = "cover", right_on = "id", suffixes = ("", "_cover"))
    joined_df = joined_df.fillna({"height": -1,
                    "width": -1,
                    "url": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQ32isJCX6lH9OJwOJvk4Xrt7kF2I06nDqm4Q&s"})
    return joined_df.drop(columns = ["cover", "id_cover"])



def drop_unneccessary_columns(modes_df):
    """
    Drops columns that are redundant (offlinecoop and onlinecoop) and renames 
    some columns to better represent their purpose (offlinemax -> offlinepvpmax, onlinemax -> onlinepvpmax)

    Inputs: 
    modes_df (pd.DataFrame): Initial multiplayer modes data

    Returns:
    trimmed_df (pd.DataFrame): Data with aforementioned updates
    """
    trimmed_df = modes_df.drop(columns=['offlinecoop', 'onlinecoop'])
    trimmed_df = trimmed_df.rename(columns = {'offlinemax': 'offlinepvpmax',
                                    'onlinemax': 'onlinepvpmax'})
    return trimmed_df