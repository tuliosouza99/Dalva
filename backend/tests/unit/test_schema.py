"""Unit tests for DalvaSchema — the Pydantic-based table schema system."""

import pytest


@pytest.mark.unit
class TestDalvaSchemaCreation:
    def test_schema_with_allowed_types(self):
        from dalva.sdk.schema import DalvaSchema

        class MySchema(DalvaSchema):
            name: str
            score: float
            count: int
            active: bool
            tags: list | None = None
            meta: dict | None = None

        schema = MySchema(name="test", score=0.5, count=1, active=True)
        assert schema.name == "test"
        assert schema.score == 0.5

    def test_schema_rejects_unsupported_type(self):
        from dalva.sdk.schema import DalvaSchema

        with pytest.raises(TypeError, match="unsupported"):

            class BadSchema(DalvaSchema):
                created_at: object

    def test_schema_rejects_set_type(self):
        from dalva.sdk.schema import DalvaSchema

        with pytest.raises(TypeError, match="unsupported"):

            class BadSchema(DalvaSchema):
                items: set

    def test_schema_rejects_tuple_type(self):
        from dalva.sdk.schema import DalvaSchema

        with pytest.raises(TypeError, match="unsupported"):

            class BadSchema(DalvaSchema):
                items: tuple


@pytest.mark.unit
class TestDalvaSchemaColumnExtraction:
    def test_to_column_schema_basic(self):
        from dalva.sdk.schema import DalvaSchema

        class MySchema(DalvaSchema):
            name: str
            score: float
            count: int
            active: bool
            tags: list | None = None
            meta: dict | None = None

        cols = MySchema.to_column_schema()
        assert len(cols) == 6
        by_name = {c["name"]: c["type"] for c in cols}
        assert by_name == {
            "name": "str",
            "score": "float",
            "count": "int",
            "active": "bool",
            "tags": "list",
            "meta": "dict",
        }

    def test_to_column_schema_optional_becomes_nullable(self):
        from dalva.sdk.schema import DalvaSchema

        class MySchema(DalvaSchema):
            name: str
            value: int | None = None

        cols = MySchema.to_column_schema()
        assert len(cols) == 2
        by_name = {c["name"]: c["type"] for c in cols}
        assert by_name["value"] == "int"

    def test_to_column_schema_excludes_none_only_field(self):
        from dalva.sdk.schema import DalvaSchema

        class MySchema(DalvaSchema):
            name: str
            nothing: None = None

        cols = MySchema.to_column_schema()
        names = [c["name"] for c in cols]
        assert "nothing" not in names


@pytest.mark.unit
class TestDalvaSchemaValidation:
    def test_validate_row_success(self):
        from dalva.sdk.schema import DalvaSchema

        class MySchema(DalvaSchema):
            name: str
            score: float

        row = MySchema.validate_row({"name": "test", "score": 0.5})
        assert row == {"name": "test", "score": 0.5}

    def test_validate_row_coerces_int_to_float(self):
        from dalva.sdk.schema import DalvaSchema

        class MySchema(DalvaSchema):
            score: float

        row = MySchema.validate_row({"score": 1})
        assert row == {"score": 1.0}

    def test_validate_row_rejects_bad_type(self):
        from dalva.sdk.schema import DalvaSchema

        class MySchema(DalvaSchema):
            count: int

        with pytest.raises(Exception):
            MySchema.validate_row({"count": "not_a_number"})

    def test_validate_row_fills_defaults(self):
        from dalva.sdk.schema import DalvaSchema

        class MySchema(DalvaSchema):
            name: str
            tags: list | None = None

        row = MySchema.validate_row({"name": "test"})
        assert row == {"name": "test", "tags": None}

    def test_validate_row_rejects_extra_fields(self):
        from dalva.sdk.schema import DalvaSchema

        class MySchema(DalvaSchema):
            name: str

        with pytest.raises(Exception):
            MySchema.validate_row({"name": "test", "extra": "bad"})
