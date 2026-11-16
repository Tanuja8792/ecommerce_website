from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from ecommerce_website.models import Category, Product


SAMPLE_PRODUCTS = [
    # Electronics (12)
    ("Wireless Earbuds", "Electronics", "boAt", 1299, 10, 40, "Compact wireless earbuds with clear sound and a charging case."),
    ("Bluetooth Speaker", "Electronics", "JBL", 2499, 12, 25, "Portable Bluetooth speaker for music at home and outdoors."),
    ("Smartphone", "Electronics", "Samsung", 15999, 8, 20, "Everyday smartphone with a bright display and capable camera."),
    ("Smart Watch", "Electronics", "Noise", 2999, 15, 30, "Smart watch with activity tracking and notification support."),
    ("Laptop Backpack", "Electronics", "HP", 1499, 5, 35, "Padded backpack designed to carry a laptop and daily essentials."),
    ("USB-C Fast Charger", "Electronics", "Anker", 899, 5, 50, "Compact fast charger for compatible USB-C devices."),
    ("Wireless Mouse", "Electronics", "Logitech", 699, 10, 45, "Comfortable wireless mouse for work and study."),
    ("Mechanical Keyboard", "Electronics", "Redragon", 2799, 10, 18, "Responsive mechanical keyboard for typing and gaming."),
    ("HD Webcam", "Electronics", "Logitech", 1999, 8, 22, "Full HD webcam for online meetings and classes."),
    ("Power Bank 20000mAh", "Electronics", "Ambrane", 1799, 12, 28, "High-capacity power bank for charging devices on the go."),
    ("Over-Ear Headphones", "Electronics", "boAt", 1899, 10, 32, "Comfort-fit over-ear headphones for music and calls."),
    ("LED Desk Lamp", "Electronics", "Philips", 999, 5, 24, "Adjustable LED desk lamp for reading and working."),
    # Fashion (12)
    ("Classic Cotton T-Shirt", "Fashion", "Roadster", 599, 10, 60, "Soft everyday cotton T-shirt with a comfortable fit."),
    ("Slim Fit Jeans", "Fashion", "Levis", 1799, 15, 30, "Versatile slim-fit denim jeans for casual outfits."),
    ("Casual Shirt", "Fashion", "Peter England", 1199, 10, 35, "Smart casual shirt suitable for everyday wear."),
    ("Women's Floral Dress", "Fashion", "DressBerry", 1499, 20, 24, "Lightweight floral dress for casual outings."),
    ("Hooded Sweatshirt", "Fashion", "H&M", 1299, 10, 28, "Soft hooded sweatshirt for cool days."),
    ("Cotton Kurti", "Fashion", "Biba", 999, 15, 32, "Comfortable printed cotton kurti for daily wear."),
    ("Running Shoes", "Fashion", "Puma", 2499, 12, 20, "Lightweight running shoes with cushioned support."),
    ("Casual Sneakers", "Fashion", "Campus", 1599, 10, 26, "Everyday sneakers with a clean casual design."),
    ("Leather Wallet", "Fashion", "WildHorn", 799, 5, 40, "Compact wallet with slots for cards and cash."),
    ("Classic Sunglasses", "Fashion", "Fastrack", 999, 10, 30, "Classic sunglasses for daily outdoor use."),
    ("Canvas Belt", "Fashion", "U.S. Polo Assn.", 499, 5, 45, "Adjustable canvas belt for casual outfits."),
    ("Travel Duffel Bag", "Fashion", "Skybags", 1399, 10, 18, "Spacious duffel bag for short trips and gym use."),
    # Beauty (12)
    ("Aloe Vera Face Wash", "Beauty", "Mamaearth", 249, 5, 50, "Gentle daily face wash with an aloe vera-based formula."),
    ("Hydrating Face Moisturizer", "Beauty", "Nivea", 299, 10, 45, "Daily moisturizer for soft and hydrated-feeling skin."),
    ("Vitamin C Face Serum", "Beauty", "Minimalist", 599, 10, 25, "Lightweight face serum for a simple skincare routine."),
    ("SPF 50 Sunscreen", "Beauty", "Neutrogena", 499, 5, 35, "Broad-spectrum sunscreen for everyday sun protection."),
    ("Rose Water Toner", "Beauty", "Good Vibes", 199, 5, 40, "Refreshing rose water toner for skincare routines."),
    ("Matte Lipstick", "Beauty", "Maybelline", 399, 15, 30, "Smooth matte lipstick for everyday makeup."),
    (" kajal Eyeliner", "Beauty", "Lakme", 249, 5, 32, "Easy-to-apply kajal for defined eyes."),
    ("Shampoo 340ml", "Beauty", "Dove", 349, 10, 38, "Daily-use shampoo for clean and manageable hair."),
    ("Conditioner 180ml", "Beauty", "L'Oreal", 299, 5, 28, "Hair conditioner for a smooth-feeling finish."),
    ("Body Lotion", "Beauty", "Vaseline", 275, 5, 42, "Moisturizing body lotion for everyday use."),
    ("Perfume 50ml", "Beauty", "Engage", 599, 10, 20, "Fresh everyday fragrance in a convenient bottle."),
    ("Makeup Brush Set", "Beauty", "Swiss Beauty", 449, 10, 22, "Multi-piece brush set for basic makeup application."),
    # Home Accessories (12)
    ("Ceramic Coffee Mug", "Home Accessories", "Home Centre", 299, 5, 50, "Reusable ceramic mug for coffee, tea and other drinks."),
    ("Stainless Steel Water Bottle", "Home Accessories", "Milton", 499, 10, 45, "Durable reusable water bottle for everyday hydration."),
    ("Decorative Cushion Cover", "Home Accessories", "Dreamscape", 349, 5, 36, "Decorative cushion cover to refresh your living space."),
    ("Table Clock", "Home Accessories", "Ajanta", 599, 10, 20, "Simple table clock for your desk or bedside."),
    ("LED String Lights", "Home Accessories", "Homesake", 399, 5, 30, "Decorative LED string lights for a warm ambience."),
    ("Non-Stick Frying Pan", "Home Accessories", "Prestige", 899, 10, 18, "Everyday frying pan with a non-stick cooking surface."),
    ("Cotton Bedsheet", "Home Accessories", "Spaces", 1199, 15, 22, "Soft cotton bedsheet for a comfortable bedroom."),
    ("Storage Organizer", "Home Accessories", "HomeStrap", 449, 5, 28, "Multipurpose organizer for keeping household items tidy."),
    ("Wall Photo Frame", "Home Accessories", "Art Street", 299, 5, 40, "Minimal photo frame for home or office decor."),
    ("Kitchen Knife Set", "Home Accessories", "Wonderchef", 799, 10, 16, "Kitchen knife set for everyday food preparation."),
    ("Laundry Basket", "Home Accessories", "Cello", 649, 5, 20, "Lightweight laundry basket for home use."),
    ("Door Mat", "Home Accessories", "Status", 249, 5, 34, "Practical door mat for an entryway."),
    # Men's Fashion (12)
    ("Men's Formal Trousers", "Men's Fashion", "Van Heusen", 1499, 10, 24, "Smart formal trousers for office and occasions."),
    ("Men's Polo T-Shirt", "Men's Fashion", "U.S. Polo Assn.", 899, 10, 35, "Classic polo T-shirt for a neat casual look."),
    ("Men's Track Pants", "Men's Fashion", "HRX", 799, 5, 30, "Comfortable track pants for workouts and daily wear."),
    ("Men's Casual Shorts", "Men's Fashion", "Decathlon", 599, 5, 28, "Lightweight casual shorts for relaxed days."),
    ("Men's Leather Sandals", "Men's Fashion", "Bata", 999, 10, 20, "Everyday sandals with a comfortable footbed."),
    ("Men's Formal Shoes", "Men's Fashion", "Red Tape", 2299, 15, 18, "Classic formal shoes for work and events."),
    ("Men's Sports Cap", "Men's Fashion", "Nike", 699, 5, 26, "Adjustable sports cap for outdoor activities."),
    ("Men's Wrist Watch", "Men's Fashion", "Fastrack", 1799, 10, 16, "Everyday wrist watch with a clean dial design."),
    ("Men's Gym Vest", "Men's Fashion", "Puma", 499, 5, 32, "Breathable gym vest for workout sessions."),
    ("Men's Checked Shirt", "Men's Fashion", "Allen Solly", 1299, 10, 22, "Casual checked shirt for everyday styling."),
    ("Men's Winter Jacket", "Men's Fashion", "Woodland", 2499, 15, 12, "Warm casual jacket for cooler weather."),
    ("Men's Backpack", "Men's Fashion", "American Tourister", 1599, 10, 20, "Everyday backpack with space for daily essentials."),
]


class Command(BaseCommand):
    help = "Create or update 60 demo products and their categories."

    @transaction.atomic
    def handle(self, *args, **options):
        created = 0
        updated = 0

        for name, category_name, brand, price, discount, stock, description in SAMPLE_PRODUCTS:
            category_slug = slugify(category_name)
            category, _ = Category.objects.get_or_create(
                name=category_name,
                defaults={
                    "slug": category_slug,
                    "description": f"{category_name} products",
                },
            )
            product_slug = slugify(name)
            _, was_created = Product.objects.update_or_create(
                slug=product_slug,
                defaults={
                    "name": name,
                    "description": description,
                    "price": Decimal(str(price)),
                    "category": category,
                    "brand": brand,
                    "stock": stock,
                    "discount": discount,
                    "is_available": True,
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(self.style.SUCCESS(
            f"Done! {created} products created, {updated} existing demo products updated."
        ))
        self.stdout.write("Product images are optional; upload images later from Django Admin.")
