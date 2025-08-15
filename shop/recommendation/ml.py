from surprise import Dataset, Reader, SVD
from .utils import export_purchase_data


def train_recommender():
    df = export_purchase_data()

    reader = Reader(rating_scale=(0, df["quantity"].max()))
    data = Dataset.load_from_df(df[["user_id", "product_id", "quantity"]], reader)

    trainset = data.build_full_trainset()

    model = SVD()
    model.fit(trainset)

    return model


def get_top_n_recommendations(user_id, model, n=5):
    df = export_purchase_data()
    all_product_ids = df["product_id"].unique()

    # Filter out already purchased
    purchased = df[df["user_id"] == user_id]["product_id"].tolist()
    candidates = [pid for pid in all_product_ids if pid not in purchased]

    predictions = [model.predict(user_id, pid) for pid in candidates]
    top_n = sorted(predictions, key=lambda x: x.est, reverse=True)[:n]

    return [int(pred.iid) for pred in top_n]  # product_ids
