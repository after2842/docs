from django.db import models
from pgvector.django import VectorField

class Document(models.Model):
    title = models.CharField(max_length=255)
    content = models.TextField()
    embedding = VectorField(dimensions=1536)  # Adjust dimensions based on your embedding model
    metadata = models.JSONField(null=True, blank=True)
