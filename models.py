from django.db import models
class Category(models.Model):
    name = models.CharField(max_length=100)
    def __str__(self):
        return self.name
class Product(models.Model):       
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock_quantity = models.PositiveIntegerField()
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    image = models.ImageField(upload_to='product_images/', blank=True, null=True)
    def __str__(self):
        return self.name