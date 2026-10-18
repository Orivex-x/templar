from templar.db.SqlPlaceholders import named_to_pyformat


def test_named_parameter_translation_preserves_postgresql_syntax_and_literals():
    sql = "SELECT payload::jsonb, ':not_a_parameter', $$:also_not$$ FROM items WHERE id = :id -- :comment\n"

    assert named_to_pyformat(sql) == (
        "SELECT payload::jsonb, ':not_a_parameter', $$:also_not$$ FROM items "
        "WHERE id = %(id)s -- :comment\n"
    )
