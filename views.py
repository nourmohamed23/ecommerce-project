from django.shortcuts import get_object_or_404, render
from .models import Category, Product
from django.db.models import Sum
from orders.models import OrderItem
def product_list(request):
    query=request.GET.get('q', '')
    category_id= request.GET.get("category", "")
    products = Product.objects.all()
    categories= Category.objects.all()
    if query:
        products = products.filter(name__icontains=query)|products.filter(description__icontains=query)
    if category_id:
        try:
            category_id = int(category_id)
        except (TypeError, ValueError):
            products = products.none()
        else:
            products = products.filter(category_id=category_id)
    return render(request, 'products/product_list.html', {'products': products, 'categories': categories, 'query': query, 'selected_category': category_id,})
def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    similar_products = Product.objects.filter(
        category=product.category,
        stock_quantity__gt=0 ).exclude(id=product.id)[:4]
    return render(request, "products/product_detail.html", {"product": product, "similar_products": similar_products,})