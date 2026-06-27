import pandas as pd

from src import clean_data


def test_clean_data_removes_nulls():
    df = pd.DataFrame({"A": [1, None], "B": [2, 3]})
    cleaned = clean_data(df)
    assert cleaned.isnull().sum().sum() == 0


def test_clean_data_lowercase_columns():
    df = pd.DataFrame({"ColA": [1], "ColB": [2]})
    cleaned = clean_data(df)
    assert all(c.islower() for c in cleaned.columns)


def test_clean_data_shape_reduced():
    df = pd.DataFrame({"A": [1, None], "B": [2, 3]})
    cleaned = clean_data(df)
    assert len(cleaned) == 1
