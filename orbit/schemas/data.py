from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ConnectionConfig(BaseModel):
    """Configuration for a data source connection."""

    name: str = Field(description="Human-readable connection name")
    connector_type: Literal["csv", "parquet", "json", "sqlite", "postgres", "mysql", "mongodb"] = Field(
        description="Type of data source"
    )
    path: str | None = Field(default=None, description="File path for file-based sources")
    host: str | None = Field(default=None, description="Database host")
    port: int | None = Field(default=None, description="Database port")
    database: str | None = Field(default=None, description="Database name")
    username: str | None = Field(default=None, description="Database username")
    password: str | None = Field(default=None, description="Database password (stored locally)")
    extra: dict[str, Any] = Field(default_factory=dict, description="Additional connection parameters")


class ColumnProfile(BaseModel):
    """Statistical profile of a single column."""

    name: str = Field(description="Column name")
    dtype: str = Field(description="Data type")
    total_count: int = Field(description="Total number of rows")
    null_count: int = Field(default=0, description="Number of null/missing values")
    null_pct: float = Field(default=0.0, description="Percentage of nulls")
    unique_count: int = Field(default=0, description="Number of unique values")
    unique_pct: float = Field(default=0.0, description="Percentage unique")
    min_value: str | None = Field(default=None, description="Minimum value (as string)")
    max_value: str | None = Field(default=None, description="Maximum value (as string)")
    mean_value: float | None = Field(default=None, description="Mean (numeric columns)")
    median_value: float | None = Field(default=None, description="Median (numeric columns)")
    std_value: float | None = Field(default=None, description="Standard deviation (numeric columns)")
    top_values: list[tuple[str, int]] = Field(default_factory=list, description="Top 5 most frequent values")
    sample_values: list[str] = Field(default_factory=list, description="5 sample values")
    inferred_semantic: str | None = Field(default=None, description="Inferred semantic type (email, phone, etc.)")


class PIIDetection(BaseModel):
    """PII detection result for a column."""

    column_name: str = Field(description="Column name")
    pii_type: str = Field(description="Type of PII detected (email, phone, ssn, etc.)")
    confidence: Literal["high", "medium", "low"] = Field(description="Detection confidence")
    sample_matches: int = Field(default=0, description="Number of sample rows matching PII pattern")
    recommendation: str = Field(default="", description="What to do about it")


class DataIssue(BaseModel):
    """A data quality issue found during profiling."""

    severity: Literal["critical", "warning", "info"] = Field(description="Issue severity")
    category: str = Field(description="Issue category (nulls, types, outliers, duplicates, pii)")
    column: str | None = Field(default=None, description="Affected column, if applicable")
    description: str = Field(description="Human-readable issue description")
    suggestion: str = Field(default="", description="Suggested fix")


class TableProfile(BaseModel):
    """Full profile of a table/file."""

    source_name: str = Field(description="Connection or file name")
    table_name: str = Field(description="Table or file name")
    row_count: int = Field(description="Total rows")
    column_count: int = Field(description="Total columns")
    size_bytes: int | None = Field(default=None, description="Size on disk in bytes")
    columns: list[ColumnProfile] = Field(default_factory=list, description="Per-column profiles")
    pii_detections: list[PIIDetection] = Field(default_factory=list, description="PII found")
    issues: list[DataIssue] = Field(default_factory=list, description="Data quality issues")
    quality_score: float = Field(default=100.0, description="Overall quality score 0-100")


class CatalogEntry(BaseModel):
    """Metadata entry for a discovered table."""

    connection_name: str = Field(description="Which connection this belongs to")
    table_name: str = Field(description="Table or file name")
    row_count: int | None = Field(default=None, description="Row count if known")
    column_count: int = Field(description="Number of columns")
    column_names: list[str] = Field(default_factory=list, description="Column names")
    column_types: list[str] = Field(default_factory=list, description="Column types")
    size_bytes: int | None = Field(default=None, description="Size if known")


class DataCatalog(BaseModel):
    """Full catalog of all discovered data sources."""

    entries: list[CatalogEntry] = Field(default_factory=list, description="All discovered tables")
    total_tables: int = Field(default=0, description="Total tables across all connections")
    total_columns: int = Field(default=0, description="Total columns across all tables")


class SimilarColumns(BaseModel):
    """Group of columns that appear to be duplicates across tables."""

    columns: list[tuple[str, str]] = Field(description="List of (table, column) pairs")
    similarity_score: float = Field(description="How similar they are, 0-1")
    reason: str = Field(description="Why they're considered similar")
