import pandas as pd

from api import load_or_scrap, scrap_log_time
from get_values import search

def print_informations(df):

    with pd.option_context("display.max_rows", None,
                           "display.max_columns", None,
                           "display.max_colwidth", None,
                           "display.width", None):

        print(df)

def main():

    try:
        df = load_or_scrap("all_users_campus_2026_september.csv", "campus/31/users?filter[pool_year]=2026")
        pool_september_2026 = search(df, field=["login", "pool_year", "pool_month"],
                                        filters={"pool_year": 2026,
                                                 "pool_month": "september"})
        print_informations(pool_september_2026)
    except Exception as e:
        print(e)
        return

    try:
        ids = pool_september_2026.index.get_level_values("user_id").unique()
        september_pool_logtime = scrap_log_time(ids, csv_name="log_time.csv")
        print_informations(september_pool_logtime)
    except Exception as e:
        print(e)
        return



if __name__ == "__main__":  
    main()