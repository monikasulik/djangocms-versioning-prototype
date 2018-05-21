from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.auth import get_user_model


User = get_user_model()


class Revision(models.Model):
    obj_id = models.CharField(max_length=191)
    content_type = models.ForeignKey(ContentType)
    obj = GenericForeignKey(ct_field="content_type", fk_field="obj_id")
    date_created = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User)
    serialized_data = models.TextField()
