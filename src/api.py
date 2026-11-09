import os
import time
import requests
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / '.env', override=True)

def load_or_scrap(csv_name, endpoint_argument):

    '''
    Return the long DataFrame from CSV_PATH if it exists (no API call),
    otherwise scrap the API, build the DataFrame and save it to CSV_PATH.
    Argument: TMP
    Return: Dataframe
    '''

    csv_path = Path(__file__).resolve().parent.parent / csv_name
    if csv_path.exists():
        return pd.read_csv(csv_path, index_col=["user_id", "section", "row", "field"])

    access_token = create_token()
    data = scrap_from_api(access_token, endpoint_argument)
    df = to_long_dataframe(data)
    df.to_csv(csv_path)
    return df

def create_token():

    '''
    Function that create a personnal token to acces the API 42
    Argument: None
    Return: a valid acces token on succes, raise an Excpetion on fail
    '''

    uid = os.getenv("UID")
    usecret = os.getenv("SECRET")
    scope = os.getenv("SCOPE")
    endpoint = os.getenv("ENDPOINT")
    token_url = os.getenv("TOKEN_URL")
    
    payload = {
        'grant_type': 'client_credentials',
        'client_id': uid,
        'client_secret': usecret,
        'scope': scope
    }

    response = requests.post(token_url, data=payload, timeout=(10, 30))
    if response.status_code == 200:
        return response.json()['access_token']
    raise Exception(f"Failed to create token: {response.status_code} {response.text}")

last_request_at = 0.0


def scrap_from_api(
    access_token,
    endpoint_argument,
    per_page=100,
    requests_per_second=2,
    timeout=(10, 30),
    max_retries=5,
):

    global last_request_at
    api_url = f"{os.getenv('ENDPOINT').rstrip('/')}/{endpoint_argument.lstrip('/')}"
    print(api_url)
    headers = {
        'Authorization': f'Bearer {access_token}'
    }

    page = 1
    all_data = []
    request_interval = 1 / requests_per_second
    retries = 0

    while True:
        wait_time = request_interval - (time.monotonic() - last_request_at)
        if wait_time > 0:
            time.sleep(wait_time)

        response = requests.get(
            api_url,
            headers=headers,
            params={'page': page, 'per_page': per_page},
            timeout=timeout,
        )
        last_request_at = time.monotonic()

        if response.status_code == 429:
            retry_after = response.headers.get('Retry-After')
            try:
                retry_delay = max(float(retry_after), request_interval) if retry_after else request_interval
            except ValueError:
                retry_delay = request_interval
            retries += 1
            if retries > max_retries:
                raise RuntimeError(
                    f"API rate limit exceeded after {max_retries} retries: {api_url}"
                )
            if retry_delay > 60:
                raise RuntimeError(
                    f"API requested a {retry_delay:g}s retry delay for {api_url}; "
                    "stopping instead of waiting indefinitely."
                )
            time.sleep(retry_delay)
            continue
        retries = 0
        
        if response.status_code != 200:
            raise Exception(f"Failed to get data from API: {response.status_code} - {response.text}")

        data = response.json()
        if not isinstance(data, list):
            return data

        all_data.extend(data)
        if len(data) < per_page:
            return all_data

        page +=1


def to_long_dataframe(data):

    '''
    Convert one user (dict) or several users (list of dicts) into ONE DataFrame
    indexed by (user_id, section, row, field) with a single column "value".
    - section: the API key ("campus", "projects_users", ...), "user" for simple fields
    - row: position inside the section (0 for a dict, 0..n for a list)
    - field: the flattened field name ("id", "project.name", ...)
    Return: a sorted DataFrame, ex: df.loc[(166888, "campus", 0, "id"), "value"]
    '''

    users = data if isinstance(data, list) else [data]
    records = []

    for user in users:
        user_id = user["id"]
        for section, content in user.items():
            if isinstance(content, dict):
                content = [content]
            if not isinstance(content, list):
                records.append((user_id, "user", 0, section, content))
                continue
            for row, item in enumerate(content):
                if not isinstance(item, dict):
                    records.append((user_id, section, row, "value", item))
                    continue
                for field, value in pd.json_normalize(item).iloc[0].items():
                    records.append((user_id, section, row, field, value))

    df = pd.DataFrame(records, columns=["user_id", "section", "row", "field", "value"])
    return df.set_index(["user_id", "section", "row", "field"]).sort_index()

def scrap_log_time(ids, csv_name="log_time.csv", begin_at="2026-09-01", per_page=100, requests_per_second=2):

    '''
    Daily log time of every user in ids from begin_at (YYYY-MM-DD) on, stored in ONE csv:
    user_id | date | log_time. The filter is sent to the API (begin_at parameter).
    Read from the csv if it exists (no API call), otherwise scrap and save it.
    Return: DataFrame indexed by (user_id, date) with a log_time (timedelta) column
    '''

    csv_path = Path(__file__).resolve().parent.parent / csv_name
    if not csv_path.exists():
        access_token = create_token()
        rows = []
        for user_id in ids:
            try:
                data = scrap_from_api(access_token,
                                      f"users/{user_id}/locations_stats?begin_at={begin_at}",
                                      per_page, requests_per_second)
            except Exception as e:
                print(f"{user_id}: {e}")
                continue
            rows += [(user_id, date, log_time) for date, log_time in data.items()]
        pd.DataFrame(rows, columns=["user_id", "date", "log_time"]).to_csv(csv_path, index=False)

    df = pd.read_csv(csv_path, parse_dates=["date"])
    df["log_time"] = pd.to_timedelta(df["log_time"])
    return df.set_index(["user_id", "date"]).sort_index()



def add_log_time_minutes(csv_name="log_time.csv"):

    '''
    Add a log_time_minutes column to the csv: 02:00:00 -> 120.0 (rounded to 0.01).
    The original log_time column is kept, so scrap_log_time still reads the file.
    Safe to run several times.
    '''

    csv_path = Path(__file__).resolve().parent.parent / csv_name
    df = pd.read_csv(csv_path)
    df["log_time_minutes"] = (pd.to_timedelta(df["log_time"]).dt.total_seconds() / 60).round(2)
    df.to_csv(csv_path, index=False)
    return df

def replace_id_by_login(df_log, df_users):

    '''
    Replace the user_id of df_log (index level "user_id") by the user login.
    Argument: df_log indexed by user_id (ex: from scrap_log_time),
              df_users in the long format USER_ID | SECTION | ROW | FIELD | VALUE
              containing the "login" field (ex: promo_2026)
    Return: a copy of df_log where user_id is the login (unknown ids are kept as is)
    '''

    logins = df_users.xs("login", level="field")["value"].droplevel(["section", "row"])
    return df_log.rename(index=logins.to_dict(), level="user_id").rename_axis(index={"user_id": "login"})


def scrap_project_pushes(
    user_ids,
    login_by_id,
    csv_name="september_pool_project_pushes.csv",
    before_date="2026-10-02",
):

    '''
    Load or scrap every projects_users attempt for the given students.
    Each projects_users record is kept as a separate push, including retries.
    The nested user endpoint supplies the attempt details, avoiding per-attempt API calls.
    '''

    csv_path = Path(__file__).resolve().parent.parent / csv_name
    if csv_path.exists():
        pushes = pd.read_csv(csv_path)
        push_dates = pd.to_datetime(pushes["push_date"], utc=True, errors="coerce")
        if push_dates.isna().any():
            raise ValueError(f"Invalid push date found in {csv_path}.")
        pushes = pushes.loc[push_dates < pd.Timestamp(before_date, tz="UTC")].copy()
        pushes.to_csv(csv_path, index=False)
        return pushes

    access_token = create_token()
    rows = []
    seen_project_user_ids = set()
    cutoff = pd.Timestamp(before_date, tz="UTC")

    user_ids = list(user_ids)
    for position, user_id in enumerate(user_ids, start=1):
        print(f"Collecting project pushes for student {position}/{len(user_ids)} (id={user_id})")
        references = scrap_from_api(access_token, f"users/{user_id}/projects_users")
        if isinstance(references, dict):
            references = [references]
        if not isinstance(references, list):
            raise ValueError(f"Unexpected projects_users response for user {user_id}.")

        for reference in references:
            if not isinstance(reference, dict) or "id" not in reference:
                raise ValueError(f"Missing projects_users id for user {user_id}.")

            project_user_id = reference["id"]
            if project_user_id in seen_project_user_ids:
                continue
            seen_project_user_ids.add(project_user_id)

            reference_date = reference.get("created_at")
            if reference_date:
                parsed_reference_date = pd.to_datetime(reference_date, utc=True, errors="coerce")
                if pd.isna(parsed_reference_date):
                    raise ValueError(
                        f"Invalid push date for projects_users/{project_user_id}."
                    )
                if parsed_reference_date >= cutoff:
                    continue

            project_user = reference
            project = project_user.get("project") or {}
            if not isinstance(project, dict):
                project = {}
            if "final_mark" not in project_user:
                raise ValueError(
                    f"Missing final_mark in projects_users list for id {project_user_id}."
                )
            push_date = project_user.get("created_at")
            if not push_date:
                raise ValueError(
                    f"Missing push date for projects_users/{project_user_id}."
                )
            parsed_push_date = pd.to_datetime(push_date, utc=True, errors="coerce")
            if pd.isna(parsed_push_date):
                raise ValueError(
                    f"Invalid push date for projects_users/{project_user_id}."
                )
            if parsed_push_date >= cutoff:
                continue
            rows.append({
                "login": login_by_id.get(user_id, str(user_id)),
                "user_id": user_id,
                "projects_user_id": project_user_id,
                "project_id": project_user.get("project_id", project.get("id")),
                "project_name": project.get("name", project_user.get("project_name")),
                "push_date": push_date,
                "final_mark": project_user.get("final_mark"),
                "marked_at": project_user.get("marked_at"),
                "status": project_user.get("status"),
                "occurrence": project_user.get("occurrence"),
            })

    columns = [
        "login", "user_id", "projects_user_id", "project_id", "project_name",
        "push_date", "final_mark", "marked_at", "status", "occurrence"
    ]
    pushes = pd.DataFrame(rows, columns=columns)
    pushes.to_csv(csv_path, index=False)
    return pushes