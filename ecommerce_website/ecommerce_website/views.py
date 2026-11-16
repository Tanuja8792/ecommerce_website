from decimal import Decimal
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from .models import Category, Order, OrderItem, Product


def cart_context(request):
    cart = request.session.get("cart", {})
    count = sum(int(qty) for qty in cart.values())
    return {"cart_count": count}


def _cart_items(request):
    cart = request.session.get("cart", {})
    products = Product.objects.filter(id__in=cart.keys(), is_available=True)
    items, total = [], Decimal("0.00")
    for product in products:
        quantity = min(int(cart.get(str(product.id), 1)), product.stock)
        if quantity > 0:
            subtotal = product.sale_price * quantity
            items.append({"product": product, "quantity": quantity, "subtotal": subtotal})
            total += subtotal
    return items, total


def home(request):
    products = Product.objects.filter(is_available=True, stock__gt=0).select_related("category")[:8]
    categories = Category.objects.all()[:6]
    return render(request, "ecommerce_website/home.html", {"products": products, "categories": categories})


def product_list(request):
    products = Product.objects.filter(is_available=True, stock__gt=0).select_related("category")
    query = request.GET.get("q", "").strip()
    category = request.GET.get("category", "")
    if query:
        products = products.filter(name__icontains=query) | products.filter(brand__icontains=query)
    if category:
        products = products.filter(category__slug=category)
    return render(request, "ecommerce_website/product_list.html", {
        "products": products.distinct(), "categories": Category.objects.all(),
        "query": query, "selected_category": category,
    })


def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug, is_available=True)
    return render(request, "ecommerce_website/product_detail.html", {"product": product})


def register_view(request):
    form = UserCreationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Your account has been created.")
        return redirect("home")
    return render(request, "ecommerce_website/auth.html", {"form": form, "title": "Create account"})


def login_view(request):
    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        next_url = request.GET.get("next", "")
        if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
            return redirect(next_url)
        return redirect("home")
    return render(request, "ecommerce_website/auth.html", {"form": form, "title": "Welcome back"})


@require_POST
def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect("home")


def cart_view(request):
    items, total = _cart_items(request)
    return render(request, "ecommerce_website/cart.html", {"items": items, "total": total})


@require_POST
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_available=True)
    if product.stock < 1:
        messages.error(request, "This product is currently out of stock.")
    else:
        cart = request.session.get("cart", {})
        key = str(product.id)
        cart[key] = min(int(cart.get(key, 0)) + 1, product.stock)
        request.session["cart"] = cart
        messages.success(request, f"{product.name} added to your cart.")
    next_url = request.POST.get("next", "")
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return redirect(next_url)
    return redirect("cart")


@require_POST
def update_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    quantity = int(request.POST.get("quantity", 1))
    cart = request.session.get("cart", {})
    if quantity <= 0:
        cart.pop(str(product_id), None)
    elif quantity <= product.stock:
        cart[str(product_id)] = quantity
    else:
        messages.error(request, f"Only {product.stock} item(s) are available.")
    request.session["cart"] = cart
    return redirect("cart")


@require_POST
def remove_from_cart(request, product_id):
    cart = request.session.get("cart", {})
    cart.pop(str(product_id), None)
    request.session["cart"] = cart
    return redirect("cart")


@login_required
def checkout(request):
    items, total = _cart_items(request)
    if not items:
        messages.warning(request, "Your cart is empty.")
        return redirect("product_list")
    if request.method == "POST":
        required = ["full_name", "email", "phone", "address", "city", "postal_code"]
        data = {field: request.POST.get(field, "").strip() for field in required}
        if not all(data.values()):
            messages.error(request, "Please complete all delivery details.")
        elif any(item["quantity"] > item["product"].stock for item in items):
            messages.error(request, "Stock changed. Please review your cart.")
            return redirect("cart")
        else:
            with transaction.atomic():
                locked_products = {}
                for item in items:
                    product = Product.objects.select_for_update().get(pk=item["product"].pk)
                    if product.stock < item["quantity"] or not product.is_available:
                        messages.error(request, f"Not enough stock for {product.name}. Please review your cart.")
                        return redirect("cart")
                    locked_products[product.pk] = product
                current_total = sum(
                    (locked_products[item["product"].pk].sale_price * item["quantity"] for item in items),
                    Decimal("0.00"),
                )
                order = Order.objects.create(user=request.user, total=current_total, **data)
                for item in items:
                    product = locked_products[item["product"].pk]
                    OrderItem.objects.create(
                        order=order, product=product, product_name=product.name,
                        unit_price=product.sale_price, quantity=item["quantity"])
                    product.stock -= item["quantity"]
                    product.save(update_fields=["stock"])
                request.session["cart"] = {}
            messages.success(request, f"Order #{order.pk} placed successfully. Payment: Cash on Delivery.")
            return redirect("order_history")
    return render(request, "ecommerce_website/checkout.html", {"items": items, "total": total})


@login_required
def order_history(request):
    orders = Order.objects.filter(user=request.user).prefetch_related("items")
    return render(request, "ecommerce_website/orders.html", {"orders": orders})
