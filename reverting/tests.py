import json
import string

from django.test import TestCase
from django.contrib.sites.models import Site
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
import factory
import factory.fuzzy
from freezegun import freeze_time
from cms.models import Title, Page, TreeNode, Placeholder

from . import TitleVersioning
from .models import Revision


class UserFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = User


class TreeNodeFactory(factory.django.DjangoModelFactory):
    site = factory.fuzzy.FuzzyChoice(Site.objects.all())
    depth = 0

    class Meta:
        model = TreeNode


class PageFactory(factory.django.DjangoModelFactory):
    node = factory.SubFactory(TreeNodeFactory)

    class Meta:
        model = Page


class PlaceholderFactory(factory.django.DjangoModelFactory):
    default_width = factory.fuzzy.FuzzyInteger(0, 25)
    slot = factory.fuzzy.FuzzyText(length=2, chars=string.digits)

    class Meta:
        model = Placeholder


def _expected_title_json(title):
    return {
        "pk": title.id,
        "model": "cms.title",
        "fields": {
            "slug": title.slug,
            "language": title.language,
            "meta_description": None,
            "path": "",
            "publisher_is_draft": True,
            "menu_title": None,
            "page": title.page.id,
            "publisher_public": None,
            "creation_date": "2018-05-01T15:15:51.640Z",
            "publisher_state": title.publisher_state,
            "published": False,
            "title": title.title,
            "has_url_overwrite": False,
            "page_title": None,
            "redirect": None
        }
    }


def _expected_placeholder_json(placeholder):
    return {
        "pk": placeholder.id,
        "model": "cms.placeholder",
        "fields": {
            "default_width": placeholder.default_width,
            "slot": placeholder.slot,
        }
    }


class TitleFactory(factory.django.DjangoModelFactory):
    language = factory.fuzzy.FuzzyChoice(['en', 'fr', 'it'])
    title = factory.fuzzy.FuzzyText(length=12)
    slug = factory.LazyAttribute(lambda o: o.title.lower()[:8])
    page = factory.SubFactory(PageFactory)

    class Meta:
        model = Title

    @factory.post_generation
    def placeholders(self, create, placeholders, **kwargs):
        if not create:
            # Simple build, do nothing.
            return

        if placeholders:
            self.page.placeholders.add(*placeholders)


class TitleRevisionFactory(factory.django.DjangoModelFactory):
    obj_id = factory.SelfAttribute('obj.id')
    content_type = factory.LazyAttribute(
        lambda o: ContentType.objects.get_for_model(Title()))
    user = factory.SubFactory(UserFactory)
    serialized_data = factory.LazyAttribute(
        lambda o: _expected_title_json(o.title))

    class Meta:
        model = Revision


class TestTitleSerialize(TestCase):

    @freeze_time("2018-05-01T15:15:51.640Z")
    def test_serialize(self):
        placeholders = PlaceholderFactory.create_batch(2)
        title = TitleFactory(placeholders=placeholders)

        serialized = json.loads(TitleVersioning().serialize(title))

        self.assertEqual(len(serialized), 3)
        self.assertDictEqual(serialized[0], _expected_title_json(title))
        self.assertDictEqual(
            serialized[1], _expected_placeholder_json(placeholders[0]))
        self.assertDictEqual(
            serialized[2], _expected_placeholder_json(placeholders[1]))


class TestTitleDeserialize(TestCase):

    def test_deserialize(self):
        title_current = TitleFactory(
            language='en', placeholders=PlaceholderFactory.create_batch(3))
        # Prep serialized data which is different to current title
        title_revision_data = _expected_title_json(TitleFactory.build(language='en'))
        title_revision_data['pk'] = title_current.pk
        title_revision_data['fields']['page'] = title_current.page.pk
        placeholder_revision_data = [
            _expected_placeholder_json(placeholder)
            for placeholder in PlaceholderFactory.build_batch(2)]
        placeholder_revision_data[0]['pk'] = 88
        placeholder_revision_data[1]['pk'] = 89
        serialized_data = [title_revision_data] + placeholder_revision_data
        # Create revision
        revision = TitleRevisionFactory(
            obj_id=title_current.pk,
            serialized_data=json.dumps(serialized_data))

        TitleVersioning().revert(revision)

        # Get the title from the db to make sure it's been saved
        title = Title.objects.get()
        self.assertEqual(title.title, title_revision_data['fields']['title'])
        self.assertEqual(title.slug, title_revision_data['fields']['slug'])
        # Check placeholders
        placeholders = title.page.placeholders.all()
        self.assertEqual(placeholders.count(), 2)
        self.assertEqual(
            placeholders[0].default_width,
            placeholder_revision_data[0]['fields']['default_width'])
        self.assertEqual(placeholders[0].slot,
            placeholder_revision_data[0]['fields']['slot'])
        self.assertEqual(
            placeholders[1].default_width,
            placeholder_revision_data[1]['fields']['default_width'])
        self.assertEqual(
            placeholders[1].slot,
            placeholder_revision_data[1]['fields']['slot'])
