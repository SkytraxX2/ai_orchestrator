import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
def quick_model(df, target):
    X = df.drop(target, axis=1)
    y = df[target]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)
    model = LinearRegression().fit(X_train, y_train)
    return model, X_test, y_test
