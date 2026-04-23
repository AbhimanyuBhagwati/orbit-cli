from __future__ import annotations

from orbit.agents.data.intelligence import (
    build_micro_questions,
    compress_catalog_for_llm,
    compress_column_for_llm,
    compress_table_for_llm,
    estimate_llm_tokens,
    pick_strategy,
)
from orbit.schemas.data import (
    CatalogEntry,
    ColumnProfile,
    DataCatalog,
    DataIssue,
    PIIDetection,
    TableProfile,
)


class TestCompressColumn:
    def test_numeric_column(self) -> None:
        col = ColumnProfile(
            name="revenue",
            dtype="float",
            total_count=1000,
            null_count=50,
            null_pct=5.0,
            unique_count=800,
            unique_pct=80.0,
            min_value="0",
            max_value="99999",
            mean_value=4500.0,
        )
        text = compress_column_for_llm(col)
        assert "revenue" in text
        assert "5.0% null" in text
        assert "mean=" in text

    def test_short_output(self) -> None:
        col = ColumnProfile(name="id", dtype="int", total_count=100, unique_count=100, unique_pct=100.0)
        text = compress_column_for_llm(col)
        # Should be compact
        assert len(text) < 200  # noqa: PLR2004


class TestCompressTable:
    def test_limits_columns(self) -> None:
        cols = [
            ColumnProfile(name=f"col_{i}", dtype="str", total_count=100, unique_count=10, unique_pct=10.0)
            for i in range(50)
        ]
        profile = TableProfile(
            source_name="test", table_name="big_table", row_count=1000, column_count=50, columns=cols
        )
        text = compress_table_for_llm(profile, max_columns=5)
        assert "and 45 more columns" in text

    def test_includes_issues(self) -> None:
        profile = TableProfile(
            source_name="test",
            table_name="t",
            row_count=100,
            column_count=1,
            columns=[ColumnProfile(name="x", dtype="int", total_count=100)],
            issues=[DataIssue(severity="critical", category="nulls", description="90% nulls in x", column="x")],
        )
        text = compress_table_for_llm(profile)
        assert "ISSUES" in text
        assert "90% nulls" in text


class TestCompressCatalog:
    def test_basic(self) -> None:
        catalog = DataCatalog(
            entries=[
                CatalogEntry(
                    connection_name="db",
                    table_name="users",
                    row_count=1000,
                    column_count=5,
                    column_names=["id", "name", "email", "age", "created"],
                    column_types=["int", "str", "str", "int", "datetime"],
                ),
            ],
            total_tables=1,
            total_columns=5,
        )
        text = compress_catalog_for_llm(catalog)
        assert "1 tables" in text
        assert "users" in text


class TestPickStrategy:
    def test_full_when_fits(self) -> None:
        assert pick_strategy("short text", model_context_window=8192) == "full"

    def test_chunked_when_large(self) -> None:
        big = "x" * 30000  # ~7500 tokens
        assert pick_strategy(big, model_context_window=4096) == "chunked"

    def test_micro_when_huge(self) -> None:
        huge = "x" * 400000  # ~100k tokens
        assert pick_strategy(huge, model_context_window=4096) == "micro"


class TestMicroQuestions:
    def test_generates_questions_for_issues(self) -> None:
        profile = TableProfile(
            source_name="test",
            table_name="orders",
            row_count=1000,
            column_count=3,
            columns=[
                ColumnProfile(name="id", dtype="int", total_count=1000),
                ColumnProfile(name="amount", dtype="float", total_count=1000),
            ],
            issues=[
                DataIssue(severity="critical", category="pii", column="email", description="PII: email detected"),
                DataIssue(severity="warning", category="nulls", column="amount", description="15% nulls"),
            ],
        )
        questions = build_micro_questions(profile)
        assert len(questions) >= 2  # noqa: PLR2004
        # Each question should be short
        for q in questions:
            assert len(q) < 500  # noqa: PLR2004

    def test_ambiguous_column_names(self) -> None:
        profile = TableProfile(
            source_name="test",
            table_name="data",
            row_count=100,
            column_count=1,
            columns=[
                ColumnProfile(name="x14", dtype="float", total_count=100, sample_values=["1.5", "2.3", "0.8"]),
            ],
            issues=[],
        )
        questions = build_micro_questions(profile)
        # Should ask about ambiguous "x14" column
        assert any("x14" in q for q in questions)


class TestTokenEstimate:
    def test_basic(self) -> None:
        assert estimate_llm_tokens("hello world") > 0

    def test_proportional(self) -> None:
        short = estimate_llm_tokens("hi")
        long = estimate_llm_tokens("hi " * 1000)
        assert long > short
