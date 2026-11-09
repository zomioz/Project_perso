import pandas as pd

from api import (
    load_or_scrap,
    scrap_log_time,
    replace_id_by_login,
    scrap_project_pushes,
)
from algo import calculate_project_scores
from get_values import search

PROJECT_PUSH_BEFORE = pd.Timestamp("2026-10-02")


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
        september_pool_logtime = september_pool_logtime.loc[
            september_pool_logtime.index.get_level_values("date") <= pd.Timestamp("2026-10-01")
        ]
        september_pool_logtime = replace_id_by_login(september_pool_logtime, df)
        september_pool_logtime["log_time_minutes"] = (
            september_pool_logtime["log_time"].dt.total_seconds() / 60
        ).round(2)
        print_informations(september_pool_logtime)
        september_pool_logtime.to_csv("september_pool_logtime.csv")

        login_by_id = (
            df.xs("login", level="field")["value"]
            .reset_index()
            .drop_duplicates("user_id")
            .set_index("user_id")["value"]
            .astype(str)
            .to_dict()
        )
        project_pushes = scrap_project_pushes(ids, login_by_id)
        project_pushes.to_csv("september_pool_project_pushes.csv", index=False)

        project_scores = calculate_project_scores(
            project_pushes,
            [login_by_id.get(user_id, str(user_id)) for user_id in ids],
            september_pool_logtime.index.get_level_values("date").min(),
            min(
                september_pool_logtime.index.get_level_values("date").max(),
                PROJECT_PUSH_BEFORE - pd.Timedelta(days=1),
            ),
        )
        project_scores.to_csv("september_pool_project_scores.csv", index=False)
        print_informations(project_scores)
    except Exception as e:
        print(e)
        return



if __name__ == "__main__":  
    main()