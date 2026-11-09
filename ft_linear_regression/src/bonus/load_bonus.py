import pandas as pd
from pandas import DataFrame as DataFrame


def load(path: str) -> DataFrame | None:

    '''
    Function to load a .csv file
    Argument: The path of .csv file
    Return: None on fail, a DataFrame on succes
    '''

    try:
        df = pd.read_csv(path)
    except (FileNotFoundError, PermissionError, IsADirectoryError):
        print("Error: unable to load csv file")
        return None

    return df