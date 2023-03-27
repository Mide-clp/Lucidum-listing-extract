import pandas as pd
import json
import ast


def get_normalize_data(file_dir: str) -> pd.DataFrame:
    file_data = []
    with open(file_dir, "r") as file:
        for data in file:
            parsed_data = json.loads(data)
            parsed_data["amenities"] = ast.literal_eval(parsed_data["amenities"])

            file_data.append(parsed_data)

    extracted_data = pd.json_normalize(file_data)

    return extracted_data


def save_data(df_object: pd.DataFrame, filename: str) -> None:
    file_dir = "./data/aggregated_data/" + filename
    df_object.to_csv(file_dir, index=False, float_format='%g')


if __name__ == "__main__":
    file_name = "./data/raw_data/airbnb-data.json"

    pd.options.display.float_format = '{:,.2f}'.format
    df = get_normalize_data(file_name)

    # format data type
    df["review_rating"] = df["review_rating"].astype(float)
    df["review_number"] = df["review_number"].astype(int)
    df["price"] = df["price"].astype(float)
    df["year_joined"] = df["year_joined"].astype(int)
    df["bedrooms"] = df["bedrooms"].apply(lambda x: x.split(".")[0])
    df["beds"] = df["beds"].apply(lambda x: x.split(".")[0]).astype(int)
    df["baths"] = df["baths"].astype(float)
    save_data(df, 'parsed_data')

    df_group_bedrooms = df[["bedrooms", "price"]].groupby("bedrooms").mean().reset_index()
    save_data(df_group_bedrooms, "avg_price_bedrooms")
    df_group_bed = df[["beds", "price"]].groupby("beds").mean().reset_index()
    save_data(df_group_bed, "avg_price_beds")
    df_group_bath = df[["baths", "price"]].groupby("baths").mean().reset_index()
    save_data(df_group_bath, "avg_price_baths")
    df_group_bedrooms_bed = df[["beds", "bedrooms", "price"]].groupby(["beds", "bedrooms"]).mean().reset_index()
    save_data(df_group_bedrooms_bed, "avg_price_bedrooms_beds")
    df_group_bedrooms_bed_bath = df[["beds", "bedrooms", "baths", "price"]].groupby(
        ["beds", "baths", "bedrooms"]).mean().reset_index()
    save_data(df_group_bedrooms_bed_bath, "avg_price_bedrooms_beds_bath")
    df_group_state = df[["state", "price"]].groupby("state").mean().reset_index()
    save_data(df_group_state, "avg_price_state")
    df_group_state_city = df[["city", "state", "price"]].groupby(["city", "state"]).mean().reset_index()
    save_data(df_group_state_city, "avg_price_city_state")
    df_group_state_city_beds = df[["beds", "city", "state", "price"]].groupby(
        ["beds", "city", "state"]).mean().reset_index()
    save_data(df_group_state_city_beds, "avg_price_beds_city_state")
    df_group_state_city_bedroom = df[["bedrooms", "city", "state", "price"]].groupby(
        ["bedrooms", "city", "state"]).mean().reset_index()
    save_data(df_group_state_city_bedroom, "avg_price_bedrooms_city_state")
    df_group_state_city_beds_bedroom = df[["beds", "bedrooms", "city", "state", "price"]].groupby(
        ["beds", "bedrooms", "city", "state"]).mean().reset_index()
    save_data(df_group_state_city_beds_bedroom, "avg_price_beds_bedrooms_city_state")
    df_group_state_city_beds_bedroom_baths = df[["beds", "bedrooms", "baths", "city", "state", "price"]].groupby(
        ["beds", "bedrooms", "baths", "city", "state"]).mean().reset_index()
    save_data(df_group_state_city_beds_bedroom_baths, "avg_price_beds_bedrooms_bath_city_state")
