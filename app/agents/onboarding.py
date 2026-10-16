import re


def generate_product_content(name: str, category: str) -> dict:
    clean_name = name.strip()
    slug = re.sub(r"[^a-z0-9]+", "-", clean_name.casefold()).strip("-")
    description = f"{clean_name} is a versatile {category.lower()} piece selected for everyday comfort, considered design, and dependable quality."
    seo_tags = [term for term in re.findall(r"[a-z0-9]+", f"{clean_name} {category}".casefold()) if len(term) > 2]
    return {"slug": slug, "description": description, "seo_tags": sorted(set(seo_tags))}
