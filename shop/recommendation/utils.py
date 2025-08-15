import pandas as pd

from shop.models import OrderItem


def export_purchase_data():
    data = OrderItem.objects.values("order__customer_id", "product_id", "quantity")
    df = pd.DataFrame(data)
    df = (
        df.groupby(["order__customer_id", "product_id"])
        .agg({"quantity": "sum"})
        .reset_index()
    )
    df.columns = ["user_id", "product_id", "quantity"]
    return df
