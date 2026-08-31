from app.api import fields
from app.api.serializers import Serializer
from core.models.model_page_visit import PageVisit
from core.models.model_user import User


class PageVisitSerializer(Serializer):
    id = fields.IntegerField(dump_only=True)
    user = fields.PrimaryKeyRelatedField(User, required=False,
                                         allow_none=True)
    path = fields.CharField(required=True, max_length=255)
    timestamp = fields.DateTimeField(dump_only=True)
    ip_address = fields.CharField(required=False, allow_none=True)
    user_agent = fields.CharField(required=False, allow_none=True,
                                  allow_blank=True)
    referrer = fields.CharField(required=False, allow_none=True,
                                max_length=500)
    method = fields.CharField(required=True, max_length=10)
    device_type = fields.CharField(required=False, max_length=50)
    language = fields.CharField(required=False, max_length=10)
    session_id = fields.UnknownModelField(PageVisit)
    extra_data = fields.UnknownModelField(PageVisit)

    model = PageVisit
