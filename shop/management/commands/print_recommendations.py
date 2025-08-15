from django.core.management.base import BaseCommand

from shop.models import Product  # Adjust to your Product model
from shop.recommendation.ml import get_top_n_recommendations, train_recommender


class Command(BaseCommand):
    # single value decomposition (SVD)
    # If User A and User B like similar products, and User A likes Product X,
    # then User B might also like Product X — even if they haven’t interacted with it yet.
    help = "Recommend products for a user"

    def add_arguments(self, parser):
        parser.add_argument("user_id", type=int)

    def handle(self, *args, **kwargs):
        user_id = kwargs["user_id"]
        model = train_recommender()
        product_ids = get_top_n_recommendations(user_id, model)

        self.stdout.write(f"Top recommendations for user {user_id}:")
        for product in Product.objects.filter(id__in=product_ids):
            self.stdout.write(f"- {product.name}")
