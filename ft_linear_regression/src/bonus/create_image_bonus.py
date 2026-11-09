import matplotlib.pyplot as plt
import pandas as pd
from get_value_bonus import get_value
from load_bonus import load
from training_model_bonus import fit_linear_regression

def create_image():

    '''
    Function that create graphics in .png from a .csv and an output linear regresion file
    Argument: None
    return: None
    '''

    df = load("data.csv")
    T0, T1 = get_value("output_bonus.txt")

    mileage = df['km'].values
    price = df['price'].values

    plt.scatter(mileage, price)
    plt.xlabel('mileage')
    plt.ylabel('price')
    plt.title('Car prices based on mileage data from a CSV file')
    plt.savefig("bonus_regression_scatter.png", dpi=100, bbox_inches="tight", pad_inches=0.3)

    regression_function = T0 + T1 * mileage

    plt.clf()
    plt.plot(mileage, regression_function, color='red')
    plt.xlabel('mileage')
    plt.ylabel('price')
    plt.title('Car prices based on mileage from linear regression function')
    plt.savefig("bonus_regression_linearfunction.png", dpi=100, bbox_inches="tight", pad_inches=0.3)

    plt.scatter(mileage, price)
    plt.xlabel('mileage')
    plt.ylabel('price')
    plt.title('Price of a car based on his mileage')
    plt.savefig("bonus_regression_all.png", dpi=100, bbox_inches="tight", pad_inches=0.3)
    plt.close("all")


def filter_through_week(df, week_number, start_date):

    '''
    Keep the rows from the first week through the selected week.
    '''

    dates = pd.to_datetime(df["date"])
    days_since_start = (dates.dt.normalize() - pd.Timestamp(start_date).normalize()).dt.days
    return df.loc[(days_since_start // 7 + 1) <= week_number].copy()


def create_student_image(df, login, week_number=None, start_date=None, end_date=None):

    '''
    Create a logtime scatter plot and its linear regression for one student.
    '''

    df = df.sort_values("date").copy()
    df["date"] = pd.to_datetime(df["date"])
    df["log_time_minutes"] = pd.to_numeric(df["log_time_minutes"])

    period_start = pd.Timestamp(start_date or df["date"].min()).normalize()
    period_end = pd.Timestamp(end_date or df["date"].max()).normalize()
    daily_logtime = (
        df.groupby(df["date"].dt.normalize())["log_time_minutes"]
        .sum()
        .reindex(pd.date_range(period_start, period_end, freq="D"), fill_value=0)
    )
    plot_df = daily_logtime.rename_axis("date").reset_index(name="log_time_minutes")
    plot_df["x_days"] = (plot_df["date"] - period_start).dt.days

    model_data = plot_df[["x_days", "log_time_minutes"]]
    T0, T1 = fit_linear_regression(model_data)
    regression_function = T0 + T1 * plot_df["x_days"]

    plt.figure()
    plt.scatter(plot_df["date"], plot_df["log_time_minutes"], label="Temps de présence quotidien")
    plt.plot(plot_df["date"], regression_function, color="red", label="Régression linéaire")
    plt.xlabel("Date")
    plt.ylabel("Temps de présence (minutes / jour)")
    title = f"Temps de présence par jour — {login}"
    if week_number is not None:
        title += f" (jusqu'à la semaine {week_number})"
    plt.title(title)
    plt.legend()
    plt.gcf().autofmt_xdate()
    output_path = "student_logtime_regression.png"
    plt.savefig(output_path, dpi=100, bbox_inches="tight", pad_inches=0.3)
    plt.close()
    return output_path


def calculate_attendance_scores(df, week_number, start_date, end_date):

    '''
    Calculate cumulative attendance percentages through the selected week.
    Missing daily rows count as zero minutes; the theoretical time uses covered days.
    '''

    period_end = min(
        pd.Timestamp(start_date).normalize() + pd.Timedelta(days=week_number * 7 - 1),
        pd.Timestamp(end_date).normalize()
    )
    period_start = pd.Timestamp(start_date).normalize()
    covered_days = (period_end - period_start).days + 1
    if covered_days <= 0:
        raise ValueError("La période sélectionnée ne contient aucun jour.")

    period_df = df.loc[
        (df["date"] >= period_start) & (df["date"] <= period_end)
    ].copy()
    period_df["log_time_minutes"] = pd.to_numeric(period_df["log_time_minutes"])
    all_logins = df["login"].dropna().unique()
    total_minutes = (
        period_df.groupby("login")["log_time_minutes"].sum()
        .reindex(all_logins, fill_value=0)
    )
    scores = (total_minutes / (2520 * covered_days / 7) * 100).rename("score_presence")
    return scores.sort_values()


def create_attendance_scores_image(scores, week_number):

    '''
    Create a horizontal ranking of attendance scores from lowest to highest.
    '''

    figure_height = max(6, len(scores) * 0.28)
    fig, ax = plt.subplots(figsize=(10, figure_height))
    ax.barh(scores.index.astype(str), scores.values, color="#0078D4")
    ax.invert_yaxis()
    ax.set_xlabel("Score de présence (%)")
    ax.set_ylabel("Étudiant")
    ax.set_title(f"Classement des scores de présence — jusqu'à la semaine {week_number}")
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    output_path = "attendance_scores.png"
    fig.savefig(output_path, dpi=100, bbox_inches="tight", pad_inches=0.3)
    plt.close(fig)
    return output_path


def create_project_scores_image(scores, week_number, score_column, title, output_path):

    '''
    Create a scrollable-friendly student ranking for one project score.
    '''

    scores = scores.sort_values(score_column, ascending=True)
    figure_height = max(6, len(scores) * 0.28)
    fig, ax = plt.subplots(figsize=(10, figure_height))
    ax.barh(scores["login"].astype(str), scores[score_column], color="#0078D4")
    ax.invert_yaxis()
    ax.set_xlabel("Score (%)")
    ax.set_ylabel("Étudiant")
    ax.set_title(f"{title} — jusqu'à la semaine {week_number}")
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_path, dpi=100, bbox_inches="tight", pad_inches=0.3)
    plt.close(fig)
    return output_path
