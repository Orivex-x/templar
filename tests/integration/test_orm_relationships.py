"""End-to-end ORM relationship and safe-query tests."""

import pytest

from templar.db import db
from templar.db.Models import Model
from templar.db.Relationships import ForeignKey, ManyToMany, OneToOne


@pytest.mark.integration
@pytest.mark.db
def test_foreign_keys_reverse_one_to_one_and_many_to_many_work(tmp_path):
    database = db.configure({"db_engine": "sqlite", "db_uri": f"sqlite:///{tmp_path / 'relationships.db'}"})

    try:
        class RelationshipUser(Model):
            name: str

        class RelationshipTag(Model):
            label: str

        class RelationshipPost(Model):
            title: str
            author = ForeignKey(RelationshipUser)
            tags = ManyToMany(RelationshipTag)

        class RelationshipProfile(Model):
            user = OneToOne(RelationshipUser)

        with pytest.raises(Exception):
            RelationshipPost(title="Missing author").save()

        with pytest.raises(NotImplementedError, match="Explicit through models"):
            ManyToMany(RelationshipTag, through_model=RelationshipPost)

        user = RelationshipUser(name="Ada")
        user.save()
        tag_one = RelationshipTag(label="python")
        tag_one.save()
        tag_two = RelationshipTag(label="web")
        tag_two.save()

        post = RelationshipPost(title="Safe ORM", author=user)
        post.save()
        profile = RelationshipProfile(user=user)
        profile.save()

        loaded_post = RelationshipPost.objects().filter(id=post.id).first()

        assert loaded_post.author.name == "Ada"
        assert [item.title for item in user.relationshippost_set.all()] == ["Safe ORM"]
        assert RelationshipProfile.objects().filter(id=profile.id).first().user.id == user.id

        loaded_post.tags.add(tag_one)
        loaded_post.tags.add(tag_one)  # idempotent
        loaded_post.tags.add(tag_two)

        assert {tag.label for tag in loaded_post.tags.all()} == {"python", "web"}
        assert loaded_post.tags.count() == 2

        loaded_post.tags.remove(tag_one)

        assert [tag.label for tag in loaded_post.tags.all()] == ["web"]

        loaded_post.tags.clear()

        assert loaded_post.tags.all() == []

        # The automatic join table is referentially safe even without cascade: callers must remove the relation before
        # deleting either endpoint.
        loaded_post.tags.add(tag_two)

        with pytest.raises(Exception):
            tag_two.delete()

        loaded_post.tags.remove(tag_two)
        tag_two.delete()

        class CascadingTag(Model):
            label: str

        class CascadingPost(Model):
            title: str
            tags = ManyToMany(CascadingTag, cascade_delete=True)

        cascading_post = CascadingPost(title="Cascade")
        cascading_post.save()
        cascading_tag = CascadingTag(label="cleanup")
        cascading_tag.save()
        cascading_post.tags.add(cascading_tag)
        join_table = "cascading_post_tags"

        assert database.fetchone(f"SELECT COUNT(1) AS count FROM {join_table}")["count"] == 1

        cascading_tag.delete()

        assert database.fetchone(f"SELECT COUNT(1) AS count FROM {join_table}")["count"] == 0
    finally:
        database.close()


def test_queryset_rejects_untrusted_identifiers_and_marks_raw_sql_unsafe(tmp_path):
    database = db.configure({"db_engine": "sqlite", "db_uri": f"sqlite:///{tmp_path / 'queries.db'}"})

    try:
        class SafeQueryModel(Model):
            name: str

        query = SafeQueryModel.objects().filter(name="Ada").order_by("name", descending=True)
        sql, params = query._build_sql()

        assert "name = :filter_0" in sql
        assert "ORDER BY name DESC" in sql
        assert params == {"filter_0": "Ada"}

        with pytest.raises(ValueError, match="unsafe model field"):
            SafeQueryModel.objects().filter(**{"name; DROP TABLE safe_query_model": "Ada"})

        with pytest.raises(ValueError, match="unsafe model field"):
            SafeQueryModel.objects().order_by("name DESC")

        with pytest.deprecated_call():
            SafeQueryModel.objects().where_raw("name = :name", name="Ada")
    finally:
        database.close()


def test_queryset_first_does_not_mutate_a_later_all_query(tmp_path):
    database = db.configure({"db_engine": "sqlite", "db_uri": f"sqlite:///{tmp_path / 'first.db'}"})

    try:
        class FirstQueryModel(Model):
            name: str

        FirstQueryModel(name="Ada").save()
        FirstQueryModel(name="Grace").save()
        query = FirstQueryModel.objects().order_by("id")

        assert query.first().name == "Ada"
        assert [item.name for item in query.all()] == ["Ada", "Grace"]
    finally:
        database.close()
