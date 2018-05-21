import json

from django.test import TestCase
from django.contrib.sites.models import Site
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
import factory
import factory.fuzzy
from freezegun import freeze_time
from cms.models import Title, Page, TreeNode

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


class TitleFactory(factory.django.DjangoModelFactory):
    language = factory.fuzzy.FuzzyChoice(['en', 'fr', 'it'])
    title = factory.fuzzy.FuzzyText(length=12)
    slug = factory.LazyAttribute(lambda o: o.title.lower()[:8])
    page = factory.SubFactory(PageFactory)

    class Meta:
        model = Title


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
        title = TitleFactory()

        serialized = json.loads(TitleVersioning().serialize(title))

        self.assertEqual(len(serialized), 1)
        self.assertDictEqual(serialized[0], _expected_title_json(title))


class TestTitleDeserialize(TestCase):

    def test_deserialize(self):
        title_current = TitleFactory(language='en')
        title_revision_data = _expected_title_json(TitleFactory.build(language='en'))
        title_revision_data['pk'] = title_current.pk
        # NOTE: fields like language or page should not change from revision
        # to revision, should there be any safeguards?
        title_revision_data['fields']['page'] = title_current.page.pk
        revision = TitleRevisionFactory(
            obj_id=title_current.pk,
            serialized_data=json.dumps([title_revision_data]))

        TitleVersioning().revert(revision)

        # Get the object from the db to make sure it's been saved
        title = Title.objects.get()
        self.assertEqual(title.title, title_revision_data['fields']['title'])
        self.assertEqual(title.slug, title_revision_data['fields']['slug'])
