import pandas as pd
import sqlalchemy as sa
import numpy as np

# Create the engine
engine = sa.create_engine('postgresql://postgres:Pitts!123@localhost:5432/GamesDatabase')

def update_data_with_pkey(new_df, tablename, has_updated_at = True):
    # 1. Fetch current and new data
    #new_df = pd.read_json(new_df_fp, orient='records')

    try:
        current_df = pd.read_sql_table(tablename, engine)
    except ValueError:
        current_df = pd.DataFrame(columns = new_df.columns)

    # 3. Isolate the rows that need to be updated
    # We use .copy() to avoid SettingWithCopy warnings later
    rows_to_replace = new_df[get_replacement_mask(new_df, current_df, use_updated_at=has_updated_at)].copy()
    new_rows = new_df[~new_df['id'].isin(current_df['id'])].copy()

    #print(rows_to_replace)

    # Fix: Actually apply the index change to the dataframe

    rows_to_replace.set_index('id', inplace=True)
    new_rows.set_index('id', inplace=True)

    # 4. The Transaction Block (SQLAlchemy 2.0 Standard)
    # engine.begin() automatically opens a transaction. 
    # It commits automatically at the end of the indentation, or rolls back if an error occurs.
    with engine.begin() as conn:
        
        # Write the temporary table using the connection, not the engine
        rows_to_replace.to_sql('my_tmp', conn, if_exists='replace', index=True)

        # Fix: Use conn.execute() and wrap the raw SQL in sa.text()
        if len(rows_to_replace) > 0:
            conn.execute(sa.text(f'DELETE FROM {tablename} WHERE id IN (SELECT id FROM my_tmp)'))

        # Insert the new updated rows back into the main table
        rows_to_add = pd.concat([rows_to_replace, new_rows])

        rows_to_add.to_sql(tablename, conn, if_exists='append', index=True)
    
    print("Upsert completed successfully")



def get_replacement_mask(new_df, current_df, use_updated_at=True):
    """
    Get mask of new_df that gives indices of rows that should be replaced. 

    Inputs:
    new_df (pd.DataFrame): Newly pulled API data that may or may not contain updates
    current_df (pd.DataFrame): Data currently stored in SQL database
    use_updated_at (boolean): Whether to use the 'updated_at' column to get mask

    Returns:
    replacement_mask: Boolean mask of same length as new_df.
    """
    assert (new_df.columns == current_df.columns).all(), "Columns should be the same for both dataframes"

    if new_df.empty:
        replacement_mask = pd.Series([], dtype=bool)
        assert len(replacement_mask) == len(new_df), "Mask length does not match new_df"
        assert pd.api.types.is_bool_dtype(replacement_mask), "Mask must be boolean dtype"
        return replacement_mask
    
    # Temporarily set the index to 'id' to perfectly align both dataframes for comparison
    new_indexed = new_df.set_index('id')
    curr_indexed = current_df.set_index('id')
    
    # Isolate only the IDs that exist in both dataframes (updates)
    common_ids = new_indexed.index.intersection(curr_indexed.index)
    
    if common_ids.empty:
        mask_logic = pd.Series(dtype=bool)

    elif use_updated_at:
        assert 'updated_at' in new_df.columns and 'updated_at' in current_df.columns, "Needs updated_at column to know which data to replace"

        # Compare timestamps for matching IDs
        mask_logic = new_indexed.loc[common_ids, 'updated_at'] > curr_indexed.loc[common_ids, 'updated_at']
    
    else:
        new_data = new_indexed.loc[common_ids]
        curr_data = curr_indexed.loc[common_ids]
        
        # In Pandas, NaN == NaN evaluates to False. 
        # We must check if values are strictly equal OR if both are NaN/None.
        is_unchanged = new_data.eq(curr_data) | (new_data.isna() & curr_data.isna())
        
        # If NOT ALL columns are unchanged, the row has been updated
        mask_logic = ~is_unchanged.all(axis=1)

    # Map the resulting boolean series back to the original index of new_df
    # Brand new IDs not found in current_df will map to NaN, which we fill with False 
    # (because they are new inserts, not existing rows that need replacing)
    replacement_mask = new_df['id'].map(mask_logic).fillna(False).astype(bool)

    assert len(replacement_mask) == len(new_df), f"Mask length ({len(replacement_mask)}) does not match new_df length ({len(new_df)})"
    assert pd.api.types.is_bool_dtype(replacement_mask), f"replacement_mask is of type {replacement_mask.dtype}, expected bool"

    return replacement_mask

    