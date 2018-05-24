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
        for placeholder in title.page.placeholders.all():
            to_serialize.append(placeholder)
            for plugin in placeholder.cmsplugin_set.all():
                to_serialize.append(plugin)
                if plugin.plugin_type == 'TextPlugin':
                    to_serialize.append(plugin.djangocms_text_ckeditor_text)
        return serialize('json', to_serialize)

    def revert(self, revision):
        # TODO: Investigate the m2m attribute on the deserialized object
        # TODO: What if title removed? What if page removed?
        placeholders = []

        for obj in deserialize("json", revision.serialized_data):
            if obj.object.__class__.__name__ == 'Title':
                title = obj.object
                title.page.placeholders.all().delete()
            elif obj.object.__class__.__name__ == 'Placeholder':
                placeholders.append(obj.object)
            elif obj.object.__class__.__name__ in ['CMSPlugin', 'Text']:
                obj.object.pk = None
            obj.object.save()
        title.page.placeholders.add(*placeholders)
