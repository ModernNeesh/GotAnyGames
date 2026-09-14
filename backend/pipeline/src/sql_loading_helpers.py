import pandas as pd
import sqlalchemy as sa
import logging
from dotenv import load_dotenv
import os
from pathlib import Path
import sys

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.models.db import init_db

# Create the engine
load_dotenv()

engine, _, _ = init_db()
inspector = sa.inspect(engine)


def update_data_without_pkey(new_df, tablename):
    """
    Function to add new rows to dataframe without a primary key.
    Simply appends any new rows that aren't exact copies of existing rows.

    Inputs:
    new_df (pd.DataFrame): New data to add (may contain redundant data)
    tablename (str): Name of table to add to
    """
    try:
        current_df = pd.read_sql_table(tablename, engine)
    except ValueError:
        current_df = pd.DataFrame(columns = new_df.columns)

    # 2. Perform a left join on all columns to find rows.
    # The 'indicator=True' creates a '_merge' column detailing the source of the row.
    merged = new_df.merge(
        current_df, 
        on=list(new_df.columns), 
        how='left', 
        indicator=True
    )

    # 3. Filter down to the rows that did NOT find a match in current_df 
    # ('left_only') and drop the temporary '_merge' indicator column.
    new_rows = merged[merged['_merge'] == 'left_only'].drop(columns=['_merge'])

    if new_rows.empty:
        logging.info(f"No new or updated rows to insert into {tablename}.")
        return

    with engine.begin() as conn:
        new_rows.to_sql(tablename, conn, if_exists='append', index=False)
        logging.info(f"Appended {len(new_rows)} new rows to {tablename} table")





def update_data_with_pkey(new_df, tablename, has_updated_at=True):
    try:
        current_df = pd.read_sql_table(tablename, engine)
    except ValueError:
        current_df = pd.DataFrame(columns=new_df.columns)

    # 1. Isolate ALL rows that need to go into the database (both updates and brand new rows)
    rows_to_replace_mask = get_replacement_mask(new_df, current_df, use_updated_at=has_updated_at)
    new_rows_mask = ~new_df['id'].isin(current_df['id'])
    
    # Combine them into a single dataframe of data to push
    rows_to_upsert = new_df[rows_to_replace_mask | new_rows_mask].copy()

    if rows_to_upsert.empty:
        logging.info(f"No new or updated rows to insert into {tablename}.")
        return

    with engine.begin() as conn:
        
        #Simply create a new table with the given data if it doesn't exist yet
        if not inspector.has_table(tablename):
            rows_to_upsert.to_sql(tablename, conn, index=False)

        else:
            # 2. Write the incoming data to a temporary staging table
            rows_to_upsert.to_sql('my_tmp', conn, if_exists='replace', index=False)

            # 3. Dynamically build the SET clause for the SQL query
            all_columns = ', '.join(rows_to_upsert.columns)
            columns_to_update = [col for col in rows_to_upsert.columns if col != 'id']
            set_clause = ", ".join([f"{col} = EXCLUDED.{col}" for col in columns_to_update])
            
            # 4. Create command to upsert rows
            upsert_sql = f"""
                    INSERT INTO {tablename} ({all_columns})
                    SELECT {all_columns} FROM my_tmp
                    ON CONFLICT (id) 
                    DO UPDATE SET {set_clause};
                """
                
            # Execute the raw SQL using SQLAlchemy's text wrapper
            conn.execute(sa.text(upsert_sql))


        logging.info(f"Upserted {len(rows_to_upsert)} new rows to {tablename} table")



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
    assert (set(new_df.columns) == set(current_df.columns)), "Columns should be the same for both dataframes"

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
