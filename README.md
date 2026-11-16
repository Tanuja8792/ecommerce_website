# ShopSphere — Django E-Commerce Website

A responsive full-stack shopping website built with Python and Django. It includes product browsing, search, categories, session-based cart, customer accounts, checkout with Cash on Delivery, order history, stock management and Django Admin.

## Features
- Responsive storefront and product catalogue
- Product categories, search and product detail pages
- Registration, login and logout using Django authentication
- Session cart with quantity changes and stock checks
- Authenticated checkout and Cash on Delivery order placement
- Order history and order status management
- Admin management for categories, products and orders
- SQLite by default; optional MySQL configuration through environment variables

## Project structure
```
ecommerce_website/
  manage.py
  ecommerce_website/
    settings.py urls.py views.py models.py admin.py
  templates/ecommerce_website/
  static/css/style.css
  media/
requirements.txt
```

## Run locally (Windows)
Open a terminal in the folder containing `manage.py`.
```powershell
py -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
python manage.py makemigrations ecommerce_website
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```
Open http://127.0.0.1:8000/ and admin at http://127.0.0.1:8000/admin/.

## Add products
In Django Admin, create categories first (enter a unique slug such as `electronics`), then add products with a unique slug, price, stock and optional image.

## Optional MySQL
Create a database named `ecommerce_db`, install a compatible MySQL client, then set environment variables:
- `DB_ENGINE=mysql`
- `DB_NAME=ecommerce_db`
- `DB_USER=your_mysql_user`
- `DB_PASSWORD=your_mysql_password`
- `DB_HOST=127.0.0.1`
- `DB_PORT=3306`

Keep credentials and `DJANGO_SECRET_KEY` in environment variables. Never commit real passwords, API keys or production secrets.

## Scope and deployment
Checkout currently supports Cash on Delivery only. No real payment gateway, shipping integration, email verification, automated test suite or production deployment configuration is included yet. Before public deployment, configure a strong secret key, DEBUG=False, allowed hosts, HTTPS, backups and static/media hosting.
