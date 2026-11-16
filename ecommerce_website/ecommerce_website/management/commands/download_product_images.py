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
    "electronics": "consumer electronics product",
    "fashion": "clothing fashion product",
    "beauty": "cosmetics skincare product",
    "home accessories": "home decor household product",
    "men's fashion": "men clothing fashion product",
}


def commons_search(query):
    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": f"filetype:bitmap {query}",
        "gsrnamespace": 6,
        "gsrlimit": 10,
        "prop": "imageinfo",
        "iiprop": "url|extmetadata",
        "iiurlwidth": 900,
        "format": "json",
    }
    url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "ShopSphereDemo/1.0 (Django product image downloader)"},
    )
    with urllib.request.urlopen(request, timeout=25) as response:
        data = json.loads(response.read().decode("utf-8"))

    pages = data.get("query", {}).get("pages", {})
    for page in pages.values():
        info = (page.get("imageinfo") or [{}])[0]
        mime = info.get("mime", "")
        image_url = info.get("thumburl") or info.get("url")
        if mime in ("image/jpeg", "image/png", "image/webp") and image_url:
            return page.get("title", ""), info
    return None, None


class Command(BaseCommand):
    help = "Download real, openly licensed product photos from Wikimedia Commons for products without images."

    def handle(self, *args, **options):
        media_root = Path(settings.MEDIA_ROOT)
        product_dir = media_root / "products"
        product_dir.mkdir(parents=True, exist_ok=True)
        attribution_file = product_dir / "IMAGE_ATTRIBUTION.txt"

        products = Product.objects.filter(image="").select_related("category")
        total = products.count()
        if not total:
            self.stdout.write(self.style.SUCCESS("All products already have images. Nothing to download."))
            return

        downloaded = 0
        skipped = 0
        attribution_lines = []

        for index, product in enumerate(products, start=1):
            category = product.category.name.lower()
            category_term = next(
                (term for key, term in CATEGORY_TERMS.items() if key in category),
                "consumer product",
            )
            # Search by product name first, then use a category-level search if needed.
            queries = [product.name, category_term]
            found_title, info = None, None

            for query in queries:
                try:
                    found_title, info = commons_search(query)
                except Exception as exc:
                    self.stdout.write(self.style.WARNING(f"Search failed for {product.name}: {exc}"))
                if info:
                    break
                time.sleep(0.4)

            if not info:
                skipped += 1
                self.stdout.write(self.style.WARNING(f"[{index}/{total}] No suitable image found: {product.name}"))
                continue

            image_url = info.get("thumburl") or info.get("url")
            mime = info.get("mime", "")
            extension = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}.get(mime)
            if not extension:
                skipped += 1
                continue

            filename = f"{slugify(product.slug) or product.pk}{extension}"
            destination = product_dir / filename
            try:
                request = urllib.request.Request(
                    image_url,
                    headers={"User-Agent": "ShopSphereDemo/1.0 (Django product image downloader)"},
                )
                with urllib.request.urlopen(request, timeout=40) as response:
                    image_bytes = response.read()
                if len(image_bytes) < 5000:
                    raise ValueError("Downloaded image is unexpectedly small")
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
                self.stdout.write(self.style.SUCCESS(f"[{index}/{total}] Image added: {product.name}"))
            except Exception as exc:
                if destination.exists():
                    destination.unlink()
                skipped += 1
                self.stdout.write(self.style.WARNING(f"Could not save image for {product.name}: {exc}"))

            time.sleep(0.6)

        if attribution_lines:
            with attribution_file.open("a", encoding="utf-8") as file:
                file.write("\n\n".join(attribution_lines) + "\n")

        self.stdout.write(self.style.SUCCESS(
            f"Finished. {downloaded} images downloaded; {skipped} products skipped."
        ))
        self.stdout.write("Check the IMAGE_ATTRIBUTION.txt file in media/products for image credits and licenses.")
