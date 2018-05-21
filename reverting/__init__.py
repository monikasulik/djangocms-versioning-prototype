from django.core.serializers import serialize, deserialize


# NOTE: Default implementation will be defined here. This class and classes
# inheriting from it will be used like:
# versioning.register(Versioning, ModelClass)
# to register models for versioning
class Versioning(object):

    def serialize(self, obj):
        pass

    def revert(self, revision):
        pass


class TitleVersioning(Versioning):

    def serialize(self, title):
        to_serialize = [title]
        to_serialize.extend(title.page.placeholders.all())
        return serialize('json', to_serialize)

    def revert(self, revision):
        # TODO: Investigate the m2m attribute on the deserialized object
        placeholders = []

        for obj in deserialize("json", revision.serialized_data):
            obj.object.save()
            if obj.object.__class__.__name__ == 'Title':
                title = obj.object
            elif obj.object.__class__.__name__ == 'Placeholder':
                placeholders.append(obj.object)
        title.page.placeholders.clear()
        title.page.placeholders.add(*placeholders)
