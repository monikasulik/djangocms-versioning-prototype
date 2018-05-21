from django.core.serializers import serialize, deserialize


class Versioning(object):

    def serialize(self, obj):
        pass

    def revert(self, revision):
        pass


class TitleVersioning(Versioning):

    def serialize(self, title):
        return serialize('json', [title])

    def revert(self, revision):
        for obj in deserialize("json", revision.serialized_data):
            obj.object.save()
            return obj.object
