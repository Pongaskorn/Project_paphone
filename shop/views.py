from django.shortcuts import render

from .models import Product


def product_list(request):
    current = request.GET.get("cat", "all")
    products = Product.objects.filter(is_active=True)
    if current in Product.Category.values:
        products = products.filter(category=current)
    else:
        current = "all"
    categories = [("all", "ทั้งหมด")] + list(Product.Category.choices)
    return render(
        request,
        "shop/product_list.html",
        {"products": products, "categories": categories, "current": current},
    )
