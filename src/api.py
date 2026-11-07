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

    response = requests.post(token_url, data=payload)
    if response.status_code == 200:
        return response.json()['access_token']
    raise Exception(f"Failed to create token: {response.status_code} {response.text}")

last_request_at = 0.0


def scrap_from_api(access_token, endpoint_argument, per_page=100, requests_per_second=2):

    global last_request_at
    api_url = f"{os.getenv('ENDPOINT').rstrip('/')}/{endpoint_argument.lstrip('/')}"
    print(api_url)
    headers = {
        'Authorization': f'Bearer {access_token}'
    }

    page = 1
    all_data = []
    request_interval = 1 / requests_per_second

    while True:
        wait_time = request_interval - (time.monotonic() - last_request_at)
        if wait_time > 0:
            time.sleep(wait_time)

        response = requests.get(api_url, headers=headers, params={'page': page, 'per_page': per_page})
        last_request_at = time.monotonic()

        if response.status_code == 429:
            retry_after = response.headers.get('Retry-After')
            try:
                retry_delay = max(float(retry_after), request_interval) if retry_after else request_interval
            except ValueError:
                retry_delay = request_interval
            time.sleep(retry_delay)
            continue
        
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

def scrap_log_time(ids, csv_name="log_time.csv", begin_at="2026-10-19", per_page=100, requests_per_second=2):

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