import pandas as pd

PROJECT_PUSH_BEFORE = pd.Timestamp("2026-10-02")


def calculate_project_scores(pushes, logins, start_date, end_date):

    '''
    Return cumulative push and final-mark scores for each student and week.
    One expected push is counted every two covered calendar days.
    Missing final marks count as zero in the average against the theoretical mark of 80.
    '''

    start_date = pd.Timestamp(start_date).normalize()
    end_date = min(
        pd.Timestamp(end_date).normalize(),
        PROJECT_PUSH_BEFORE - pd.Timedelta(days=1),
    )
    if end_date < start_date:
        raise ValueError("The end date must not be before the start date.")

    pushes = pushes.copy()
    if "push_date" not in pushes.columns:
        raise ValueError("The pushes data must include a push_date column.")
    pushes["push_date"] = (
        pd.to_datetime(pushes["push_date"], utc=True, errors="coerce")
        .dt.tz_localize(None)
        .dt.normalize()
    )
    pushes = pushes.loc[pushes["push_date"] < PROJECT_PUSH_BEFORE]
    pushes["final_mark"] = pd.to_numeric(pushes["final_mark"], errors="coerce")
    logins = list(dict.fromkeys(str(login) for login in logins if pd.notna(login)))

    last_week = ((end_date - start_date).days // 7) + 1
    score_rows = []
    for week_number in range(1, last_week + 1):
        period_end = min(
            start_date + pd.Timedelta(days=week_number * 7 - 1),
            end_date
        )
        covered_days = (period_end - start_date).days + 1
        period_pushes = pushes.loc[
            pushes["push_date"].between(start_date, period_end)
        ]
        push_counts = period_pushes.groupby("login").size()
        average_marks = (
            period_pushes.assign(final_mark=period_pushes["final_mark"].fillna(0))
            .groupby("login")["final_mark"]
            .mean()
        )
        expected_pushes = covered_days / 2

        for login in logins:
            push_count = int(push_counts.get(login, 0))
            average_mark = float(average_marks.get(login, 0))
            score_rows.append({
                "login": login,
                "week": week_number,
                "covered_days": covered_days,
                "push_count": push_count,
                "theoretical_pushes": expected_pushes,
                "push_score": push_count / expected_pushes * 100,
                "average_final_mark": average_mark,
                "note_score": average_mark / 80 * 100,
            })

    return pd.DataFrame(score_rows)