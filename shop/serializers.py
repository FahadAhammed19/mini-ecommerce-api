from django.db import transaction
from django.db.models import F
from rest_framework import serializers
from .models import Category, Product, Order

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "description"]

class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = Product
        fields = ["id", "name", "description", "price", "stock", "category", "category_name", "created_date"]
        read_only_fields = ["id", "created_date"]

class OrderSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    quantity = serializers.IntegerField(min_value=1, max_value=10000)

    class Meta:
        model = Order
        fields = ["id", "user", "product", "product_name", "quantity", "unit_price", "total_price", "order_date"]
        read_only_fields = ["id", "user", "unit_price", "total_price", "order_date"]

    @transaction.atomic
    def create(self, validated_data):
        # Lock the product on databases supporting row locks; the conditional
        # update also prevents any successful write from making stock negative.
        try:
            product = Product.objects.select_for_update().get(pk=validated_data["product"].pk)
        except Product.DoesNotExist:
            raise serializers.ValidationError({"product": "This product no longer exists."})
        quantity = validated_data["quantity"]
        changed = Product.objects.filter(pk=product.pk, stock__gte=quantity).update(stock=F("stock") - quantity)
        if not changed:
            raise serializers.ValidationError({"quantity": "Not enough stock available."})
        return Order.objects.create(
            user=self.context["request"].user, product=product, quantity=quantity,
            unit_price=product.price, total_price=product.price * quantity,
        )
  
