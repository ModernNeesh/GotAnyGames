import pandas as pd
import logging



def ids_to_names(df, column):
    """
    Function to convert a column of lists of ids to a column of lists of names using the corresponding id-to-name map csv.

    Inputs: 
    df (pd.DataFrame): Dataframe containing the column to be converted
    column (str): Name of the column to be converted

    Returns:
    new_col (pd.Series): Series containing the converted column
    """
    names_df = pd.read_csv(fr"feature_id_maps/{column}_names.csv")
    id_to_name = dict(zip(names_df['id'], names_df['name']))
    new_col = df[column].apply(lambda ids: [id_to_name.get(i, "Unknown") for i in ids] if isinstance(ids, list) else ids)
    return new_col


def split_list_columns(df):
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
            subbed_col = ids_to_names(new_df, col) #Convert ids to names
            expanded_cols = expanded_cols = pd.get_dummies(subbed_col.explode()).groupby(level=0).sum().astype(int) #Expand into one-hot columns
            new_df = pd.concat([new_df.drop(col, axis=1), expanded_cols], axis=1) #Concatenate with original dataframe
            logging.info("Finished cleaning column: %s", col)
    return new_df