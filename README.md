# Mini E-commerce REST API

Django REST Framework assignment for Batch 10, Module 23. Built by Fahad Ahammed.

## Features
- Category and product CRUD with serializers and ModelViewSets.
- Products contain name, description, decimal price, stock, category, and created date.
- Name search, category filter, exact/range price filtering, price ordering, pagination.
- Token login, logout/revocation, and authenticated write/order endpoints.
- Orders contain the current user, product, quantity, total price, and order date.
- Users can create, list, and retrieve only their own orders.
- Bonus: stock validation and atomic stock deduction; price snapshots preserve historical totals.
- Automated Django API tests and an importable Postman collection with assertions.

## Quick start
Use Python 3.12 or newer. SQLite is included with Python; no separate database service is needed.

```sh
python -m venv .venv
# macOS / Linux
source .venv/bin/activate
# Windows PowerShell instead: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Create your own username and password when prompted. No credentials, tokens, or database are committed. Open http://127.0.0.1:8000/ for the browsable API and http://127.0.0.1:8000/admin/ for administration. You can create additional ordinary users through the admin Users page. Admin login uses Django sessions; API calls use tokens.

## Authentication and permissions

```http
POST /auth/login/
Content-Type: application/json

{"username":"your-username","password":"your-password"}
```

A successful response contains `{"token":"..."}`. Send `Authorization: Token YOUR_TOKEN` on protected requests. `POST /auth/logout/` revokes that token. Login is throttled to 20 attempts/minute per client scope; use HTTPS when hosting an API with tokens.

| Resource | Anonymous | Authenticated |
| --- | --- | --- |
| Categories / products | List and retrieve | Create, read, update, delete |
| Orders | No access (401) | Create, list own, retrieve own |
| Login | Obtain token with valid credentials | Obtain token |
| Logout | No access | Revoke current token |

All authenticated users may manage the catalog in this educational API. Order ownership comes from the authenticated user, never the request body. Order totals and unit prices are calculated server-side. Other users receive 404 for an order they do not own. Orders cannot be updated or deleted through the API.

## Endpoints

| Method | URL | Purpose |
| --- | --- | --- |
| GET, POST | `/categories/` | List / create categories |
| GET, PUT, PATCH, DELETE | `/categories/{id}/` | Category CRUD |
| GET, POST | `/products/` | List / create products |
| GET, PUT, PATCH, DELETE | `/products/{id}/` | Product CRUD |
| POST | `/auth/login/` | Receive token |
| POST | `/auth/logout/` | Revoke token |
| GET, POST | `/orders/` | List own orders / create order |
| GET | `/orders/{id}/` | Retrieve own order |

Use trailing slashes. Successful creation returns 201; deletion/logout returns 204. Invalid input or insufficient stock returns 400. Missing/invalid tokens return 401. Missing/inaccessible objects return 404. Unsupported order mutations return 405. Deleting a referenced category/product returns 409 to preserve relationships.

### Example JSON
Create a category:
```json
{"name":"Electronics","description":"Devices and accessories"}
```
Create a product using the returned category ID:
```json
{"name":"Phone","description":"Smartphone","price":"120.50","stock":5,"category":1}
```
Create an order using the returned product ID:
```json
{"product":1,"quantity":2}
```
The total is `241.00`; stock becomes 3. Quantity must be an integer between 1 and 10000 and cannot exceed available stock. Product price must be positive and stock nonnegative. Monetary values are decimal strings. The example assumes the created IDs are 1; use the actual IDs returned by your database.

### Search, filtering, ordering, pagination
```text
/products/?search=phone
/products/?category=1
/products/?price=120.50
/products/?min_price=10&max_price=200
/products/?ordering=price
/products/?ordering=-price
/products/?search=phone&category=1&min_price=10&ordering=price&page=1&page_size=5
```
Price bounds are inclusive. Filters combine. Default page size is 10; `page_size` is capped at 100. Lists return `count`, `next`, `previous`, and `results`. Price ordering uses ID as a deterministic tie-breaker.

## Testing
```sh
python manage.py check
python manage.py test shop
python manage.py makemigrations --check --dry-run
```
Tests cover CRUD, validation, token lifecycle, filtering, ordering, pagination, order isolation, total-price tampering, price snapshots, stock exhaustion, transaction rollback, and protected deletes.

### Postman
1. Start the local server and create a user.
2. Import `postman/Mini-Ecommerce.postman_collection.json` into Postman.
3. Set collection variables `base_url`, `username`, and `password` locally.
4. Run the collection in order using Collection Runner. Login captures the token and creation requests capture IDs automatically.
5. Review the test results. The final requests log out and confirm token revocation.

The collection deliberately creates an order and leaves its category/product in the local database because referenced records are protected. Disposable CRUD test records are deleted. Run against a test database, not important real data. Do not export or commit populated password/token variables.

You can also execute the same Postman collection with Newman:
```sh
newman run postman/Mini-Ecommerce.postman_collection.json -e /path/to/private-local-environment.json
```

## Project structure
```text
manage.py
requirements.txt
config/       settings, root URLs, WSGI
shop/         models, serializers, viewsets, filters, pagination, admin, tests
shop/migrations/  committed database schema
postman/      collection and request assertions
```

## Design decisions
Category-to-product and product-to-order are protected foreign keys, so existing records are not silently destroyed. Stock deduction and order insertion share a transaction. Conditional stock updates prevent successful orders from driving stock negative; row locking is also used on databases that support it. SQLite is suitable for this local assignment, but concurrent writers may encounter lock contention; use PostgreSQL and load/concurrency testing before a production deployment. Historical unit/total prices are saved on each order. Product name remains a live reference.

## Configuration
Defaults are for local development only: `DJANGO_DEBUG=1`, localhost hosts, SQLite, and a development-only secret. Environment variables are read directly (no automatic `.env` loading). Set `DJANGO_DEBUG=0`, a random `DJANGO_SECRET_KEY`, and `DJANGO_ALLOWED_HOSTS` before hosting; a missing production secret fails startup. Production additionally needs an appropriate server, HTTPS, static-file handling, database configuration, and deployment checks. Hosting is not required by this assignment.

## Submission
Submit the GitHub repository URL. This repository includes complete source, pinned requirements, committed migrations, README, tests, and Postman collection. Optional reviews, ratings, and image uploads are not implemented; stock validation is included.
