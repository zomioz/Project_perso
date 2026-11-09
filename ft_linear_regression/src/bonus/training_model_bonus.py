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

def linear_regression(df, number_of_iteration) -> tuple[float, float]:

    '''
    Function that execute an linear regression on a dataframe
    argument: Dirst: Dataframe. Second: number of iteration for the linear regression
    return: The two θ for the prediction
    '''

    learningRate = 0.1
    m = len(df)
    T0 = 0.0
    T1 = 0.0
    estimate_price = 0

    for x in range(number_of_iteration):

        TmpT0 = 0
        TmpT1 = 0

        for i in range(m):
            mileage = df.iloc[i, 0]
            price = df.iloc[i, 1]
            estimate_price = T0 + (T1 * mileage)
            TmpT0 += estimate_price - price
            TmpT1 += (estimate_price - price) * mileage

        T0 = T0 - learningRate * (1 / m) * TmpT0
        T1 = T1 - learningRate * (1 / m) * TmpT1

    return T0, T1

def fit_linear_regression(df) -> tuple[float, float]:

    '''
    Fit a linear regression on the first two numeric columns and return real-scale parameters.
    '''

    df_normalized = df.astype(float).copy()

    x_min = df_normalized.iloc[:, 0].min()
    x_max = df_normalized.iloc[:, 0].max()
    x_range = x_max - x_min
    if x_range == 0:
        raise ValueError("At least two different dates are required.")
    df_normalized.iloc[:, 0] = (df_normalized.iloc[:, 0] - x_min) / x_range

    y_min = df_normalized.iloc[:, 1].min()
    y_max = df_normalized.iloc[:, 1].max()
    y_range = y_max - y_min
    if y_range == 0:
        return y_min, 0.0
    df_normalized.iloc[:, 1] = (df_normalized.iloc[:, 1] - y_min) / y_range

    T0, T1 = linear_regression(df_normalized, 1000)
    T1_real = T1 * (y_range / x_range)
    T0_real = y_min + (y_range * T0) - (T1_real * x_min)
    return T0_real, T1_real

def training_model():

    '''
    Main function it load the data file and execute an linear regression on it
    argument : None
    return : None
    '''

    df = load("data.csv")
    if df is None:
        return False

    T0_real, T1_real = fit_linear_regression(df)

    with open("output_bonus.txt", "w") as f:
        print(str(T0_real), file=f)
        print(str(T1_real), file=f)
    
    return True