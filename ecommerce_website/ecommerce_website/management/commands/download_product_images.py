import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from ecommerce_website.models import Product


CATEGORY_TERMS = {
    "electronics": "electronics smartphone headphones computer gadget",
    "fashion": "clothing shirt shoes fashion",
    "beauty": "cosmetics skincare bottle",
    "home accessories": "home decor kitchen household",
    "men's fashion": "men clothing shoes",
}

USER_AGENT = "ShopSphereDemo/1.0 (Django product image downloader)"


def commons_request(params):
    params.update({"action": "query", "format": "json"})
    url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=35) as response:
        return json.loads(response.read().decode("utf-8"))


def commons_search(query):
    """Find a usable image file in Wikimedia Commons for the search phrase."""
    search_data = commons_request({
        "list": "search",
        "srsearch": query,
        "srnamespace": 6,
        "srlimit": 15,
    })
    titles = [
        item.get("title")
        for item in search_data.get("query", {}).get("search", [])
        if item.get("title")
    ]
    if not titles:
        return None, None

    image_data = commons_request({
        "titles": "|".join(titles),
        "prop": "imageinfo",
        "iiprop": "url|mime|extmetadata",
        "iiurlwidth": 900,
    })
    pages = image_data.get("query", {}).get("pages", {})
    for page in pages.values():
        info = (page.get("imageinfo") or [{}])[0]
        mime = info.get("mime", "")
        image_url = info.get("thumburl") or info.get("url")
        if mime in ("image/jpeg", "image/png", "image/webp") and image_url:
            return page.get("title", ""), info
    return None, None


class Command(BaseCommand):
    help = "Download product photos from Wikimedia Commons for products without local images."

    def add_arguments(self, parser):
        parser.add_argument(
            "--all",
            action="store_true",
            help="Replace existing product photos too (normally only missing photos are downloaded).",
        )

    def handle(self, *args, **options):
        product_dir = Path(settings.MEDIA_ROOT) / "products"
        product_dir.mkdir(parents=True, exist_ok=True)
        attribution_file = product_dir / "IMAGE_ATTRIBUTION.txt"

        products = Product.objects.select_related("category").order_by("id")
        if not options["all"]:
            products = products.filter(image="")
        total = products.count()

        if not total:
            self.stdout.write(self.style.SUCCESS("No products need photos."))
            return

        downloaded = 0
        skipped = 0
        attribution_lines = []

        for index, product in enumerate(products, start=1):
            category = product.category.name.lower()
            category_terms = next(
                (term for key, term in CATEGORY_TERMS.items() if key in category),
                "consumer product",
            )
            # Try exact product name first, then broaden to product + category,
            # and finally use category-specific terms.
            queries = [
                product.name,
                f"{product.name} {category}",
                category_terms,
            ]
            found_title, info = None, None
            for query in queries:
                try:
                    found_title, info = commons_search(query)
                except Exception as exc:
                    self.stdout.write(self.style.WARNING(
                        f"Search attempt failed for {product.name} ({query}): {exc}"
                    ))
                if info:
                    break
                time.sleep(0.5)

            if not info:
                skipped += 1
                self.stdout.write(self.style.WARNING(
                    f"[{index}/{total}] No Commons photo found after all searches: {product.name}"
                ))
                continue

            image_url = info.get("thumburl") or info.get("url")
            mime = info.get("mime", "")
            extension = {
                "image/jpeg": ".jpg",
                "image/png": ".png",
                "image/webp": ".webp",
            }.get(mime)
            if not extension:
                skipped += 1
                continue

            filename = f"{slugify(product.slug) or product.pk}{extension}"
            destination = product_dir / filename
            try:
                request = urllib.request.Request(image_url, headers={"User-Agent": USER_AGENT})
                with urllib.request.urlopen(request, timeout=45) as response:
                    image_bytes = response.read()
                if len(image_bytes) < 3000:
                    raise ValueError("Image download was too small or invalid")

                destination.write_bytes(image_bytes)
                product.image.name = f"products/{filename}"
                product.save(update_fields=["image"])
                downloaded += 1

                metadata = info.get("extmetadata", {})
                artist = metadata.get("Artist", {}).get("value", "Creator not listed")
                license_name = metadata.get("LicenseShortName", {}).get("value", "License not listed")
                source_page = info.get("descriptionurl", "")
                attribution_lines.append(
                    f"Product: {product.name}\nFile: {found_title}\nCreator: {artist}\n"
                    f"License: {license_name}\nSource: {source_page}\n"
                )
                self.stdout.write(self.style.SUCCESS(
                    f"[{index}/{total}] Photo saved: {product.name}"
                ))
            except Exception as exc:
                if destination.exists():
                    destination.unlink()
                skipped += 1
                self.stdout.write(self.style.WARNING(
                    f"[{index}/{total}] Download failed for {product.name}: {exc}"
                ))

            time.sleep(0.8)

        if attribution_lines:
            with attribution_file.open("a", encoding="utf-8") as file:
                file.write("\n\n".join(attribution_lines) + "\n")

        self.stdout.write(self.style.SUCCESS(
            f"Finished: {downloaded} photos downloaded; {skipped} products still need photos."
        ))
        self.stdout.write(f"Photo folder: {product_dir}")
        self.stdout.write(f"Image credits: {attribution_file}")
