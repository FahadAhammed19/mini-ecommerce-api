from django.contrib import admin
from .models import Category, Product, Order

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["id", "name"]
    search_fields = ["name"]

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "price", "stock", "category"]
    list_filter = ["category"]
    search_fields = ["name"]

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "product", "quantity", "total_price", "order_date"]
    readonly_fields = ["user", "product", "quantity", "unit_price", "total_price", "order_date"]
    def has_add_permission(self, request):
        return False
    def has_delete_permission(self, request, obj=None):
        return False
  
