from decimal import Decimal
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.name

class Product(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    stock = models.PositiveIntegerField(validators=[MaxValueValidator(2147483647)])
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    created_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]
        constraints = [models.CheckConstraint(condition=models.Q(price__gt=0), name="positive_product_price")]

    def __str__(self):
        return self.name

class Order(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="orders")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="orders")
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(10000)])
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=14, decimal_places=2)
    order_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-order_date", "-id"]
        constraints = [
            models.CheckConstraint(condition=models.Q(quantity__gt=0), name="positive_order_quantity"),
            models.CheckConstraint(condition=models.Q(total_price__gt=0), name="positive_order_total"),
        ]

    def __str__(self):
        return f"Order {self.pk} - {self.user}"
