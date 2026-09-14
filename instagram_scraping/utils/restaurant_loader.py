import pandas as pd


def load_restaurants(csv_path: str):

    df = pd.read_csv(csv_path)

    restaurants = df[
        ["Name", "Instagram (Company)"]
    ].dropna(
        subset=[
            "Name",
            "Instagram (Company)"
        ]
    )

    return restaurants.to_dict(
        orient="records"
    )