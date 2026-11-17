from decimal import Decimal
from django.utils.text import slugify
from django.conf import settings
from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    slug = models.SlugField(max_length=120, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    image = models.ImageField(upload_to="products/", blank=True)
    brand = models.CharField(max_length=100, blank=True)
    stock = models.PositiveIntegerField(default=0)
    discount = models.PositiveIntegerField(default=0)
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def sale_price(self):
        return (self.price * (Decimal("100") - Decimal(self.discount)) / Decimal("100")).quantize(Decimal("0.01"))

    @property
    def display_image_url(self):
        """
        Return the uploaded image when present; otherwise use a remotely hosted
        category/product image. No image file is stored in this project.
        """
        if self.image:
            return self.image.url

        product_tags = slugify(self.name).replace("-", ",")
        category_tags = slugify(self.category.name).replace("-", ",")
        return (
            f"https://loremflickr.com/900/900/{product_tags},{category_tags}"
            f"?lock={self.pk}"
        )

    def __str__(self):
        return self.name


class Order(models.Model):
    STATUS_CHOICES = [
        ("placed", "Placed"), ("processing", "Processing"),
        ("shipped", "Shipped"), ("delivered", "Delivered"),
        ("cancelled", "Cancelled"),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders")
    full_name = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    address = models.TextField()
    city = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=12)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="placed")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order #{self.pk} - {self.user}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    product_name = models.CharField(max_length=200)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.product_name} x {self.quantity}"
