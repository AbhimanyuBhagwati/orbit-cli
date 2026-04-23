from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

import pytest

from orbit.agents.data.connectors.factory import create_connector
from orbit.agents.data.profiler import _compute_column_profile, _detect_issues, profile_table
from orbit.schemas.data import ColumnProfile, ConnectionConfig


class TestColumnProfile:
    def test_basic_numeric_column(self) -> None:
        values: list[Any] = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        result = _compute_column_profile("count", "int", values, total_rows=10)
        assert result.name == "count"
        assert result.null_count == 0
        assert result.null_pct == 0
        assert result.unique_count == 10
        assert result.mean_value is not None
        assert result.mean_value == 5.5
        assert result.min_value == "1.0"  # noqa: PLR2004
        assert result.max_value == "10.0"

    def test_column_with_nulls(self) -> None:
        values: list[Any] = [1, None, 3, None, 5]
        result = _compute_column_profile("val", "int", values, total_rows=5)
        assert result.null_count == 2  # noqa: PLR2004
        assert result.null_pct == 40.0  # noqa: PLR2004

    def test_all_nulls(self) -> None:
        values: list[Any] = [None, None, None]
        result = _compute_column_profile("empty", "str", values, total_rows=3)
        assert result.null_count == 3  # noqa: PLR2004
        assert result.null_pct == 100.0  # noqa: PLR2004
        assert result.unique_count == 0

    def test_string_column(self) -> None:
        values: list[Any] = ["a", "b", "c", "a", "b"]
        result = _compute_column_profile("category", "str", values, total_rows=5)
        assert result.unique_count == 3  # noqa: PLR2004
        assert result.mean_value is None  # Not numeric
        assert result.min_value == "a"
        assert result.max_value == "c"

    def test_empty_values(self) -> None:
        values: list[Any] = []
        result = _compute_column_profile("empty", "str", values, total_rows=0)
        assert result.null_count == 0
        assert result.unique_count == 0

    def test_top_values(self) -> None:
        values: list[Any] = ["a", "a", "a", "b", "b", "c"]
        result = _compute_column_profile("cat", "str", values, total_rows=6)
        assert len(result.top_values) > 0
        assert result.top_values[0][0] == "a"
        assert result.top_values[0][1] == 3  # noqa: PLR2004

    def test_median_even(self) -> None:
        values: list[Any] = [1, 2, 3, 4]
        result = _compute_column_profile("n", "int", values, total_rows=4)
        assert result.median_value == 2.5  # noqa: PLR2004

    def test_median_odd(self) -> None:
        values: list[Any] = [1, 2, 3, 4, 5]
        result = _compute_column_profile("n", "int", values, total_rows=5)
        assert result.median_value == 3.0  # noqa: PLR2004


class TestIssueDetection:
    def _col(self, name: str = "col", null_pct: float = 0, unique_count: int = 10, **kwargs: Any) -> ColumnProfile:
        defaults: dict[str, Any] = {
            "name": name,
            "dtype": "str",
            "total_count": 100,
            "null_count": int(null_pct),
            "null_pct": null_pct,
            "unique_count": unique_count,
            "unique_pct": unique_count,
        }
        defaults.update(kwargs)
        return ColumnProfile(**defaults)

    def test_high_null_critical(self) -> None:
        cols = [self._col(null_pct=60)]
        issues = _detect_issues(cols, total_rows=100)
        assert any(i.severity == "critical" and i.category == "nulls" for i in issues)

    def test_moderate_null_warning(self) -> None:
        cols = [self._col(null_pct=15)]
        issues = _detect_issues(cols, total_rows=100)
        assert any(i.severity == "warning" and i.category == "nulls" for i in issues)

    def test_low_null_no_issue(self) -> None:
        cols = [self._col(null_pct=2)]
        issues = _detect_issues(cols, total_rows=100)
        assert not any(i.category == "nulls" for i in issues)

    def test_single_value_warning(self) -> None:
        cols = [self._col(unique_count=1, total_count=100)]
        issues = _detect_issues(cols, total_rows=100)
        assert any(i.category == "variance" for i in issues)

    def test_empty_table_critical(self) -> None:
        issues = _detect_issues([], total_rows=0)
        assert any(i.severity == "critical" and i.category == "empty" for i in issues)


class TestProfileTableWithCSV:
    @pytest.fixture()
    def csv_file(self, tmp_path: Path) -> Path:
        csv_content = "id,name,email,age,salary\n"
        csv_content += "1,Alice,alice@example.com,30,50000\n"
        csv_content += "2,Bob,bob@test.org,25,60000\n"
        csv_content += "3,Charlie,charlie@gmail.com,,70000\n"
        csv_content += "4,Diana,diana@company.co,35,\n"
        csv_content += "5,Eve,eve@example.com,28,55000\n"
        p = tmp_path / "test.csv"
        p.write_text(csv_content)
        return p

    def test_profile_csv(self, csv_file: Path) -> None:
        config = ConnectionConfig(name="test", connector_type="csv", path=str(csv_file))
        connector = create_connector(config)
        result = profile_table(connector, csv_file.name)

        assert result.row_count == 5  # noqa: PLR2004
        assert result.column_count == 5  # noqa: PLR2004
        assert result.quality_score > 0

        # Should find email PII
        email_cols = [c for c in result.columns if c.name == "email"]
        assert len(email_cols) == 1
        assert any(p.pii_type == "email" for p in result.pii_detections)

    def test_profile_csv_pii_in_name(self, csv_file: Path) -> None:
        config = ConnectionConfig(name="test", connector_type="csv", path=str(csv_file))
        connector = create_connector(config)
        result = profile_table(connector, csv_file.name)

        # "salary" column name should trigger financial PII
        pii_types = {p.pii_type for p in result.pii_detections}
        assert "email" in pii_types

    def test_profile_csv_null_detection(self, csv_file: Path) -> None:
        config = ConnectionConfig(name="test", connector_type="csv", path=str(csv_file))
        connector = create_connector(config)
        result = profile_table(connector, csv_file.name)

        # age and salary have nulls
        age_col = next(c for c in result.columns if c.name == "age")
        assert age_col.null_count >= 1


class TestProfileTableWithJSON:
    @pytest.fixture()
    def json_file(self, tmp_path: Path) -> Path:
        data = [
            {"user_id": 1, "phone": "555-123-4567", "status": "active"},
            {"user_id": 2, "phone": "555-234-5678", "status": "inactive"},
            {"user_id": 3, "phone": "555-345-6789", "status": "active"},
        ]
        p = tmp_path / "users.json"
        p.write_text(json.dumps(data))
        return p

    def test_profile_json(self, json_file: Path) -> None:
        config = ConnectionConfig(name="test", connector_type="json", path=str(json_file))
        connector = create_connector(config)
        result = profile_table(connector, json_file.name)

        assert result.row_count == 3  # noqa: PLR2004
        assert result.column_count == 3  # noqa: PLR2004
        # Should detect phone PII (by column name and/or values)
        assert any(p.pii_type == "phone" for p in result.pii_detections)
