from django.db import models

# Create your models here.
class Article(models.Model):
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    created_date = models.DateField()
    def __str__(self):
        return self.title
