import requests
import csv
import time

BASE = "https://www.jbhifi.co.nz"
PRODUCTS_JSON = BASE + "/products.json"
LIMIT = 250
OUTPUT_FILE = "jbhifi_products_with_category.csv"

PAGE_DELAY = 0.1
MAX_ERRORS = 5


def is_gift_card(title: str) -> bool:
    if not title:
        return False
    t = title.lower()
    return "gift card" in t or "giftcard" in t or "gift-card" in t


def fetch_products(page: int):
    url = f"{PRODUCTS_JSON}?limit={LIMIT}&page={page}"
    print(f"Fetching URL: {url}")

    try:
        r = requests.get(url, timeout=20)
        if r.status_code != 200:
            print(f"  HTTP {r.status_code} on page {page}")
            return None
        return r.json().get("products", [])
    except Exception as e:
        print(f"  Request error: {e}")
        return None


def get_category(product):
    """Get category from product type. If blank fallback to tags."""
    cat = product.get("product_type", "").strip()
    if cat:
        return cat
    tags = product.get("tags", "")
    return tags if tags else "Uncategorized"


def scrape():
    seen_variants = set()
    rows = []

    page = 1
    consecutive_errors = 0

    while True:

        products = fetch_products(page)

        if products is None:
            consecutive_errors += 1
            if consecutive_errors >= MAX_ERRORS:
                print("Too many errors — stopping.")
                break
            page += 1
            continue
        else:
            consecutive_errors = 0

        # TRUE stop condition – empty feed = end
        if len(products) == 0:
            print("Reached end of Shopify feed — stopping.")
            break

        for p in products:
            pid = p.get("id")
            title = p.get("title", "").strip()
            handle = p.get("handle", "")  # Get the handle

            category = get_category(p)

            for v in p.get("variants", []):
                vid = v.get("id")

                if vid in seen_variants:
                    continue
                seen_variants.add(vid)

                if not is_gift_card(title):
                    price = float(v.get("price") or 0)
                    comp_raw = v.get("compare_at_price")
                    original = float(comp_raw) if comp_raw else price
                    disc = round((original - price) / original * 100, 2) if original > price else 0

                    rows.append([
                        pid,
                        vid,
                        handle,  # Added handle to row
                        title,
                        original,
                        price,
                        disc,
                        category
                    ])

        if page >= 100:
            print("Reached Shopify 25,000 item limit (page 100). Stopping.")
            break

        page += 1
        time.sleep(PAGE_DELAY)

    print(f"\nDONE — unique variants scraped: {len(seen_variants)}")
    print(f"Total rows: {len(rows)}")

    # Save CSV
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Product ID",
            "Variant ID",
            "Handle",  # Added Header
            "Title",
            "Original Price",
            "Discounted Price",
            "Discount %",
            "Category"
        ])
        writer.writerows(rows)

    print(f"Saved → {OUTPUT_FILE}")


if __name__ == "__main__":
    scrape()