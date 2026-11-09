import PySimpleGUI as sg
from pathlib import Path
import pandas as pd
from create_image_bonus import (
    calculate_attendance_scores,
    create_attendance_scores_image,
    create_project_scores_image,
    create_student_image,
    filter_through_week,
)
from load_bonus import load

LOGTIME_CSV = Path(__file__).resolve().parents[3] / "september_pool_logtime.csv"
PROJECT_PUSHES_CSV = LOGTIME_CSV.with_name("september_pool_project_pushes.csv")
PROJECT_SCORES_CSV = LOGTIME_CSV.with_name("september_pool_project_scores.csv")
PROJECT_PUSH_BEFORE = pd.Timestamp("2026-10-02")

def apply_modern_theme():

    '''
    Function that define a new theme for GUI
    Argument: None
    Return: None
    '''

    sg.theme('DarkBlue3')
    sg.set_options(
        font=('Segoe UI', 11),
        button_color=('#FFFFFF', '#0078D4'),
        element_padding=(5, 5),
        border_width=1,
        text_color='#FFFFFF'
    )


def display_gui():

    '''
    Function that display the GUi, and handle all button of GUI. Launch the appropriate function in each case
    Argument: None
    Return: None
    '''

    apply_modern_theme()

    logtime_df = load(str(LOGTIME_CSV))
    if logtime_df is None:
        sg.popup_error(f"Impossible de charger le fichier : {LOGTIME_CSV}")
        return
    if not {"login", "date", "log_time_minutes"}.issubset(logtime_df.columns):
        sg.popup_error("Le CSV doit contenir les colonnes login, date et log_time_minutes.")
        return

    try:
        logtime_df["date"] = pd.to_datetime(logtime_df["date"])
    except (TypeError, ValueError) as error:
        sg.popup_error(f"Les dates du CSV ne sont pas valides : {error}")
        return

    project_pushes_df = (
        load(str(PROJECT_PUSHES_CSV)) if PROJECT_PUSHES_CSV.exists() else None
    )
    project_scores_df = (
        load(str(PROJECT_SCORES_CSV)) if PROJECT_SCORES_CSV.exists() else None
    )
    project_data_available = (
        project_pushes_df is not None
        and project_scores_df is not None
        and {"login", "project_name", "push_date", "final_mark", "status", "occurrence"}
        .issubset(project_pushes_df.columns)
        and {"login", "week", "push_score", "note_score"}
        .issubset(project_scores_df.columns)
    )

    login_options = sorted(logtime_df["login"].dropna().astype(str).unique())
    start_date = logtime_df["date"].min().normalize()
    last_week = ((logtime_df["date"].max().normalize() - start_date).days // 7) + 1
    week_options = {
        f"Semaine {week}": week for week in range(1, last_week + 1)
    }
    layout = [
        [sg.Text("Régression linéaire du temps de présence quotidien (en minutes)")],
        [
            sg.Text("Choisir un étudiant :"),
            sg.Combo(login_options, key="-LOGIN-", readonly=True, size=(20, 1),
                     disabled=not login_options)
        ],
        [
            sg.Text("Afficher les données jusqu'à :"),
            sg.Combo(list(week_options), default_value=list(week_options)[-1],
                     key="-WEEK-", readonly=True, size=(16, 1)),
            sg.Button("Afficher la régression", disabled=not login_options),
            sg.Button("Afficher les scores de présence", disabled=not login_options)
        ],
        [
            sg.Button("Afficher les scores Push et note",
                      disabled=not project_data_available),
            sg.Button("Afficher les pushes de l'étudiant",
                      disabled=not project_data_available or not login_options)
        ],
        *([] if project_data_available else [[
            sg.Text("Données de projets absentes : lancez d'abord src/main.py.")
        ]]),
        [sg.Button("Quitter")]
    ]

    window = sg.Window("Temps de présence par jour", layout, margins=(500, 300))

    try:
        while True:

            event, values = window.read()

            if event in ("Quitter", sg.WIN_CLOSED):
                break

            if event == "Afficher la régression":
                login = values["-LOGIN-"]
                selected_week = values["-WEEK-"]
                if not login or not selected_week:
                    sg.popup("Choisissez un login et une semaine.")
                    continue

                student_df = logtime_df[logtime_df["login"].astype(str) == login]
                week_number = week_options[selected_week]
                student_df = filter_through_week(student_df, week_number, start_date)
                period_end = min(
                    start_date + pd.Timedelta(days=week_number * 7 - 1),
                    logtime_df["date"].max().normalize(),
                    PROJECT_PUSH_BEFORE - pd.Timedelta(days=1),
                )
                if (period_end - start_date).days < 1:
                    sg.popup(
                        "Il faut au moins deux dates différentes pour calculer la "
                        "régression sur la période choisie."
                    )
                    continue

                try:
                    image_path = create_student_image(
                        student_df, login, week_number, start_date, period_end
                    )
                except (KeyError, TypeError, ValueError) as error:
                    sg.popup(f"Impossible de créer la régression : {error}")
                    continue

                win_img = sg.Window(
                    f"Temps de présence - {login}",
                    [[sg.Image(filename=image_path)], [sg.Button("Fermer")]]
                )
                try:
                    while True:
                        event1, values1 = win_img.read()
                        if event1 in (sg.WIN_CLOSED, "Fermer"):
                            break
                finally:
                    win_img.close()

            if event == "Afficher les scores de présence":
                selected_week = values["-WEEK-"]
                if not selected_week:
                    sg.popup("Choisissez une semaine.")
                    continue

                week_number = week_options[selected_week]
                try:
                    scores = calculate_attendance_scores(
                        logtime_df, week_number, start_date, logtime_df["date"].max()
                    )
                    image_path = create_attendance_scores_image(scores, week_number)
                except (KeyError, TypeError, ValueError) as error:
                    sg.popup(f"Impossible de calculer les scores : {error}")
                    continue

                win_img = sg.Window(
                    f"Scores de présence - semaine {week_number}",
                    [
                        [sg.Column(
                            [[sg.Image(filename=image_path)]],
                            size=(1000, 650),
                            scrollable=True,
                            vertical_scroll_only=True,
                            expand_x=True,
                            expand_y=True
                        )],
                        [sg.Button("Fermer")]
                    ],
                    resizable=True,
                    finalize=True
                )
                try:
                    while True:
                        event1, values1 = win_img.read()
                        if event1 in (sg.WIN_CLOSED, "Fermer"):
                            break
                finally:
                    win_img.close()

            if event == "Afficher les scores Push et note":
                selected_week = values["-WEEK-"]
                if not selected_week:
                    sg.popup("Choisissez une semaine.")
                    continue

                week_number = week_options[selected_week]
                scores = project_scores_df.loc[
                    project_scores_df["week"] == week_number
                ].copy()
                if scores.empty:
                    sg.popup("Aucun score calculé pour cette semaine.")
                    continue

                try:
                    push_image = create_project_scores_image(
                        scores, week_number, "push_score",
                        "Score de pushes", "project_push_scores.png"
                    )
                    note_image = create_project_scores_image(
                        scores, week_number, "note_score",
                        "Score de note", "project_note_scores.png"
                    )
                except (KeyError, TypeError, ValueError) as error:
                    sg.popup(f"Impossible d'afficher les scores : {error}")
                    continue

                win_img = sg.Window(
                    f"Scores Push et note - semaine {week_number}",
                    [
                        [sg.Column(
                            [
                                [sg.Image(filename=push_image)],
                                [sg.Image(filename=note_image)]
                            ],
                            size=(1000, 650),
                            scrollable=True,
                            vertical_scroll_only=True,
                            expand_x=True,
                            expand_y=True
                        )],
                        [sg.Button("Fermer")]
                    ],
                    resizable=True,
                    finalize=True
                )
                try:
                    while True:
                        event1, values1 = win_img.read()
                        if event1 in (sg.WIN_CLOSED, "Fermer"):
                            break
                finally:
                    win_img.close()

            if event == "Afficher les pushes de l'étudiant":
                login = values["-LOGIN-"]
                selected_week = values["-WEEK-"]
                if not login or not selected_week:
                    sg.popup("Choisissez un étudiant et une semaine.")
                    continue

                week_number = week_options[selected_week]
                period_end = min(
                    start_date + pd.Timedelta(days=week_number * 7 - 1),
                    logtime_df["date"].max().normalize()
                )
                push_dates = (
                    pd.to_datetime(project_pushes_df["push_date"], utc=True, errors="coerce")
                    .dt.tz_localize(None)
                    .dt.normalize()
                )
                student_pushes = project_pushes_df.loc[
                    project_pushes_df["login"].astype(str).eq(login)
                    & push_dates.between(start_date, period_end)
                ].copy()
                student_pushes["push_date"] = pd.to_datetime(
                    student_pushes["push_date"], utc=True, errors="coerce"
                ).dt.tz_localize(None)
                student_pushes = student_pushes.sort_values("push_date")
                table_rows = [
                    [
                        str(row.projects_user_id),
                        str(row.project_name or ""),
                        row.push_date.strftime("%Y-%m-%d") if pd.notna(row.push_date) else "",
                        "" if pd.isna(row.final_mark) else str(row.final_mark),
                        str(row.status or ""),
                        "" if pd.isna(row.occurrence) else str(row.occurrence),
                    ]
                    for row in student_pushes.itertuples()
                ]
                if not table_rows:
                    sg.popup("Aucun push pour cet étudiant pendant la période choisie.")
                    continue

                win_table = sg.Window(
                    f"Pushes de {login} - semaine {week_number}",
                    [[sg.Table(
                        values=table_rows,
                        headings=["ID", "Projet", "Date du push", "Note finale", "Statut", "Tentative"],
                        auto_size_columns=False,
                        col_widths=[10, 25, 14, 12, 14, 10],
                        num_rows=min(20, len(table_rows)),
                        vertical_scroll_only=True,
                        expand_x=True,
                        expand_y=True
                    )], [sg.Button("Fermer")]],
                    resizable=True,
                    finalize=True
                )
                try:
                    while True:
                        event1, values1 = win_table.read()
                        if event1 in (sg.WIN_CLOSED, "Fermer"):
                            break
                finally:
                    win_table.close()

    except KeyboardInterrupt:
        print("Programme interrompu par l'utilisateur (Ctrl+C)")
    finally:
        window.close()