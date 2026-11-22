from django.db.models.deletion import ProtectedError
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, mixins, status, viewsets
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from .filters import ProductFilter
from .models import Category, Product, Order
from .serializers import CategorySerializer, ProductSerializer, OrderSerializer

class ProtectedDeleteMixin:
    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response({"detail": "This record is used by existing products or orders and cannot be deleted."}, status=status.HTTP_409_CONFLICT)

class CategoryViewSet(ProtectedDeleteMixin, viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

class ProductViewSet(ProtectedDeleteMixin, viewsets.ModelViewSet):
    queryset = Product.objects.select_related("category").all()
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ProductFilter
    search_fields = ["name"]
    ordering_fields = ["price"]
    ordering = ["id"]

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        # A unique tie-breaker makes pagination stable for equal prices.
        if self.request.query_params.get("ordering") in ("price", "-price"):
            queryset = queryset.order_by(self.request.query_params["ordering"], "id")
        return queryset

class OrderViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).select_related("product", "user")

class LoginView(ObtainAuthToken):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        request.auth.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
  
