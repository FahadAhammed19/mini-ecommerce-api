from decimal import Decimal
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase
from .models import Category, Product, Order

class CommerceAPITests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='buyer', password='Test-password-123')
        self.other = get_user_model().objects.create_user(username='other', password='Other-password-123')
        self.token = Token.objects.create(user=self.user)
        self.category = Category.objects.create(name='Electronics')
        self.product = Product.objects.create(name='Phone', description='Test phone', price='120.50', stock=5, category=self.category)

    def authenticate(self, user=None):
        token, _ = Token.objects.get_or_create(user=user or self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    def test_login_logout_and_revocation(self):
        response = self.client.post(reverse('login'), {'username': 'buyer', 'password': 'Test-password-123'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['token'], self.token.key)
        self.authenticate()
        self.assertEqual(self.client.post(reverse('logout')).status_code, 204)
        self.assertEqual(self.client.get(reverse('order-list')).status_code, 401)

    def test_invalid_login_and_missing_token(self):
        self.assertEqual(self.client.post(reverse('login'), {'username': 'buyer', 'password': 'wrong'}).status_code, 400)
        self.assertEqual(self.client.get(reverse('order-list')).status_code, 401)
        self.assertEqual(self.client.post(reverse('product-list'), {}).status_code, 401)
        self.assertEqual(self.client.post(reverse('category-list'), {'name': 'No'}).status_code, 401)
        self.client.credentials(HTTP_AUTHORIZATION='Token invalid')
        self.assertEqual(self.client.get(reverse('order-list')).status_code, 401)

    def test_category_crud(self):
        self.authenticate()
        response = self.client.post(reverse('category-list'), {'name': 'Books', 'description': 'Reading'})
        self.assertEqual(response.status_code, 201)
        url = reverse('category-detail', args=[response.data['id']])
        self.assertEqual(self.client.get(url).data['name'], 'Books')
        self.assertEqual(self.client.patch(url, {'name': 'New books'}).status_code, 200)
        self.assertEqual(self.client.get(reverse('category-list')).data['count'], 2)
        self.assertEqual(self.client.delete(url).status_code, 204)

    def test_product_crud_and_validation(self):
        self.authenticate()
        payload = {'name': 'Cable', 'description': 'USB cable', 'price': '12.00', 'stock': 4, 'category': self.category.pk}
        response = self.client.post(reverse('product-list'), payload)
        self.assertEqual(response.status_code, 201)
        url = reverse('product-detail', args=[response.data['id']])
        self.assertEqual(self.client.get(url).data['price'], '12.00')
        self.assertEqual(self.client.patch(url, {'stock': 8}).status_code, 200)
        self.assertEqual(self.client.put(url, {**payload, 'name': 'New cable'}).status_code, 200)
        for update in ({'stock': -1}, {'price': '-1.00'}, {'price': '0.00'}, {'category': 99999}, {'name': ''}):
            self.assertEqual(self.client.patch(url, update).status_code, 400)
        self.assertEqual(self.client.delete(url).status_code, 204)
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_search_category_price_order_and_pagination(self):
        books = Category.objects.create(name='Books')
        Product.objects.create(name='Book', description='Reading', price='10.00', stock=10, category=books)
        Product.objects.create(name='Phone case', description='Case', price='20.00', stock=10, category=self.category)
        url = reverse('product-list')
        self.assertEqual(self.client.get(url, {'search': 'PHONE'}).data['count'], 2)
        self.assertEqual(self.client.get(url, {'category': books.pk}).data['count'], 1)
        self.assertEqual(self.client.get(url, {'price': '20.00'}).data['count'], 1)
        data = self.client.get(url, {'search': 'phone', 'category': self.category.pk, 'min_price': 15, 'max_price': 130, 'ordering': '-price', 'page_size': 1}).data
        self.assertEqual(data['count'], 2)
        self.assertEqual(data['results'][0]['name'], 'Phone')
        self.assertIsNotNone(data['next'])
        data = self.client.get(url, {'ordering': 'price', 'page_size': 1, 'page': 2}).data
        self.assertEqual(data['results'][0]['name'], 'Phone case')
        self.assertEqual(self.client.get(url, {'min_price': 'invalid'}).status_code, 400)
        self.assertEqual(self.client.get(url, {'page': 999}).status_code, 404)

    def test_order_calculates_total_and_deducts_stock(self):
        self.authenticate()
        response = self.client.post(reverse('order-list'), {'product': self.product.pk, 'quantity': 2, 'user': self.other.pk, 'total_price': '0.01'}, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['user'], self.user.pk)
        self.assertEqual(response.data['total_price'], '241.00')
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 3)
        self.assertEqual(self.client.get(reverse('order-detail', args=[response.data['id']])).status_code, 200)

    def test_orders_are_private_and_immutable(self):
        self.authenticate()
        order = self.client.post(reverse('order-list'), {'product': self.product.pk, 'quantity': 1}).data
        url = reverse('order-detail', args=[order['id']])
        self.assertEqual(self.client.patch(url, {'quantity': 2}).status_code, 405)
        self.assertEqual(self.client.delete(url).status_code, 405)
        self.authenticate(self.other)
        self.assertEqual(self.client.get(reverse('order-list')).data['count'], 0)
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_invalid_order_quantities_leave_stock_unchanged(self):
        self.authenticate()
        for quantity in (0, -1, 6, 10001, 'not-a-number', 1.5):
            response = self.client.post(reverse('order-list'), {'product': self.product.pk, 'quantity': quantity})
            self.assertEqual(response.status_code, 400, response.data)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 5)
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(self.client.post(reverse('order-list'), {'product': 99999, 'quantity': 1}).status_code, 400)

    def test_last_stock_cannot_be_ordered_twice(self):
        self.authenticate()
        self.assertEqual(self.client.post(reverse('order-list'), {'product': self.product.pk, 'quantity': 5}).status_code, 201)
        self.assertEqual(self.client.post(reverse('order-list'), {'product': self.product.pk, 'quantity': 1}).status_code, 400)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 0)

    def test_order_keeps_price_snapshot(self):
        self.authenticate()
        response = self.client.post(reverse('order-list'), {'product': self.product.pk, 'quantity': 2})
        self.product.price = Decimal('200.00')
        self.product.save()
        order = self.client.get(reverse('order-detail', args=[response.data['id']])).data
        self.assertEqual(order['unit_price'], '120.50')
        self.assertEqual(order['total_price'], '241.00')

    def test_failed_order_creation_rolls_back_stock(self):
        self.authenticate()
        with patch('shop.serializers.Order.objects.create', side_effect=RuntimeError('test failure')):
            with self.assertRaises(RuntimeError):
                self.client.post(reverse('order-list'), {'product': self.product.pk, 'quantity': 2})
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 5)
        self.assertEqual(Order.objects.count(), 0)

    def test_referenced_records_cannot_be_deleted(self):
        self.authenticate()
        self.assertEqual(self.client.delete(reverse('category-detail', args=[self.category.pk])).status_code, 409)
        self.client.post(reverse('order-list'), {'product': self.product.pk, 'quantity': 1})
        self.assertEqual(self.client.delete(reverse('product-detail', args=[self.product.pk])).status_code, 409)
  
