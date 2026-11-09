from load_bonus import load
from get_value_bonus import get_value

def calculate_precision():

    '''
    Function that calculate the precision of an linear regression model using RMSE, MSE and R2
    Argument: None
    Return: 3 values : MSE, RMSE, R2
    '''

    df = load("data.csv")
    T0, T1 = get_value("output_bonus.txt")

    true_price = df["price"]
    predicted_price = T0 + T1 * df["km"]

    mse = calculate_mse(true_price, predicted_price)
    rmse = mse ** 0.5
    r2 = calculate_r2(true_price, predicted_price)
    return mse, rmse, r2


def calculate_mse(true_price, predicted_price):

    '''
    Function that calculate MSE value : Mean squared error
    Argument: True Prices from .csv and Predicted_price from linear regression function
    Return: MSE value
    '''

    total = 0
    n = len(true_price)

    for i in range(n):
        error = true_price[i] - predicted_price[i]
        total += error * error

    return total / n


def calculate_r2(true_price, predicted_price):

    '''
    Function that calculate R2 value : 
    Argument : True Prices from .csv and Predicted_price from linear regression function
    Return: R2 Value
    '''

    n = len(true_price)

    total = 0
    for i in range(n):
        total += true_price[i]
    mean_true = total / n

    ss_res = 0
    ss_tot = 0
    for i in range(n):
        error = true_price[i] - predicted_price[i]
        ss_res += error * error

        diff = true_price[i] - mean_true
        ss_tot += diff * diff

    if ss_tot == 0:
        return 0

    return 1 - (ss_res / ss_tot)