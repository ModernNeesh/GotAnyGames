import pandas as pd
import sqlalchemy as sa
from src.sql_loading_helpers import *
from dotenv import load_dotenv
import os

load_dotenv()
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")

# Create the engine
engine = sa.create_engine(f'postgresql://postgres:{POSTGRES_PASSWORD}@localhost:5432/GamesDatabase')

#Start logging
logging.basicConfig(filename='logging/app.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

base_df = pd.DataFrame({'foreign_key_1': [1, 2, 3], 'foreign_key_2' : [9, 8, 7]})

def initialize_test_case(tablename):
    with engine.begin() as conn:
        base_df.to_sql(tablename, conn, if_exists='replace', index=False)



#Test case 1: Try to add data with completely new foreign keys
initialize_test_case('no_pkey_test_1')
new_df = pd.DataFrame({'foreign_key_1': [4, 5, 6], 'foreign_key_2' : [10, 11, 12]})
update_data_without_pkey(new_df, 'no_pkey_test_1') #Should have 6 rows with all the data



#Test case 2: Try to add new data with some new, some old foreign keys, but no duplicates
initialize_test_case('no_pkey_test_2')
new_df = pd.DataFrame({'foreign_key_1': [1, 5, 6], 'foreign_key_2' : [10, 7, 12]})
update_data_without_pkey(new_df, 'no_pkey_test_2') #Should have 6 rows with all the data



#Test case 3: Try to add new data that has duplicate entries
initialize_test_case('no_pkey_test_3')
new_df = pd.DataFrame({'foreign_key_1': [1, 2, 3], 'foreign_key_2' : [9, 10, 8]})
update_data_without_pkey(new_df, 'no_pkey_test_3') #Should have 5 rows 



#Test case 4: Try to add no new data
initialize_test_case('no_pkey_test_4')
blank_df = pd.DataFrame(columns = ['foreign_key_1', 'foreign_key_2'])
update_data_without_pkey(blank_df, 'no_pkey_test_4') #Should have 3 rows


#Test case 5: Insert the exact same data
initialize_test_case('no_pkey_test_5')
new_df = base_df.copy()
update_data_without_pkey(new_df, 'no_pkey_test_5') #Should have 3 rows



#Test case 6: Insert data where id numbers are swapped
initialize_test_case('no_pkey_test_6')
new_df = pd.DataFrame({'foreign_key_1': [9, 8, 7], 'foreign_key_2' : [1, 2, 3]})
update_data_without_pkey(new_df, 'no_pkey_test_6') #Should have 6 rows 

logging.info("Done running test cases without primary keys!")