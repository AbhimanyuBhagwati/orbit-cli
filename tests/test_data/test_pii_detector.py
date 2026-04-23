from __future__ import annotations

from orbit.agents.data.pii_detector import detect_pii_in_column_name, detect_pii_in_values, scan_column


class TestPIIColumnNameDetection:
    def test_email_column(self) -> None:
        result = detect_pii_in_column_name("email")
        assert result is not None
        assert result.pii_type == "email"

    def test_email_address_column(self) -> None:
        result = detect_pii_in_column_name("email_address")
        assert result is not None
        assert result.pii_type == "email"

    def test_phone_column(self) -> None:
        result = detect_pii_in_column_name("phone_number")
        assert result is not None
        assert result.pii_type == "phone"

    def test_ssn_column(self) -> None:
        result = detect_pii_in_column_name("ssn")
        assert result is not None
        assert result.pii_type == "ssn"

    def test_credit_card_column(self) -> None:
        result = detect_pii_in_column_name("credit_card")
        assert result is not None
        assert result.pii_type == "credit_card"

    def test_password_column(self) -> None:
        result = detect_pii_in_column_name("password")
        assert result is not None
        assert result.pii_type == "credential"

    def test_api_key_column(self) -> None:
        result = detect_pii_in_column_name("api_key")
        assert result is not None
        assert result.pii_type == "credential"

    def test_first_name_column(self) -> None:
        result = detect_pii_in_column_name("first_name")
        assert result is not None
        assert result.pii_type == "name"

    def test_salary_column(self) -> None:
        result = detect_pii_in_column_name("salary")
        assert result is not None
        assert result.pii_type == "financial"

    def test_non_pii_column(self) -> None:
        result = detect_pii_in_column_name("order_count")
        assert result is None

    def test_id_column(self) -> None:
        result = detect_pii_in_column_name("id")
        assert result is None

    def test_created_at_column(self) -> None:
        result = detect_pii_in_column_name("created_at")
        assert result is None


class TestPIIValueDetection:
    def test_emails(self) -> None:
        values = ["alice@example.com", "bob@test.org", "charlie@gmail.com", None, "dave@company.co"]
        result = detect_pii_in_values("contact", values)
        assert result is not None
        assert result.pii_type == "email"
        assert result.confidence == "high"

    def test_ssns(self) -> None:
        values = ["123-45-6789", "987-65-4321", "111-22-3333"]
        result = detect_pii_in_values("tax_id", values)
        assert result is not None
        assert result.pii_type == "ssn"

    def test_credit_cards(self) -> None:
        values = ["4111-1111-1111-1111", "5500-0000-0000-0004", "3400-000000-00009"]
        result = detect_pii_in_values("payment_info", values)
        assert result is not None
        assert result.pii_type == "credit_card"

    def test_us_phones(self) -> None:
        values = ["(555) 123-4567", "555-234-5678", "+1 555-345-6789", "555.456.7890"]
        result = detect_pii_in_values("contact_num", values)
        assert result is not None
        assert result.pii_type == "phone"

    def test_ip_addresses(self) -> None:
        values = ["192.168.1.1", "10.0.0.1", "172.16.0.1", "8.8.8.8"]
        result = detect_pii_in_values("server", values)
        assert result is not None
        assert result.pii_type == "ip_address"

    def test_no_pii_in_numbers(self) -> None:
        values = [1, 2, 3, 42, 100, 200]
        result = detect_pii_in_values("count", values)
        assert result is None

    def test_no_pii_in_categories(self) -> None:
        values = ["active", "inactive", "pending", "active", "inactive"]
        result = detect_pii_in_values("status", values)
        assert result is None

    def test_empty_values(self) -> None:
        result = detect_pii_in_values("col", [])
        assert result is None

    def test_all_none(self) -> None:
        result = detect_pii_in_values("col", [None, None, None])
        assert result is None

    def test_low_match_rate_ignored(self) -> None:
        # Only 1 out of 10 values is an email — below 20% threshold
        values = ["alice@example.com"] + ["not-email"] * 9
        result = detect_pii_in_values("mixed", values)
        assert result is None


class TestScanColumn:
    def test_name_and_value_match(self) -> None:
        values = ["alice@example.com", "bob@test.org", "charlie@gmail.com"]
        results = scan_column("email", values)
        # Should deduplicate — both name and value say "email"
        assert len(results) == 1
        assert results[0].pii_type == "email"

    def test_name_match_only(self) -> None:
        values = ["some", "random", "text"]
        results = scan_column("email_address", values)
        assert len(results) == 1
        assert results[0].pii_type == "email"

    def test_value_match_only(self) -> None:
        values = ["123-45-6789", "987-65-4321", "111-22-3333"]
        results = scan_column("identifier", values)
        assert len(results) == 1
        assert results[0].pii_type == "ssn"

    def test_no_match(self) -> None:
        values = [1, 2, 3, 4, 5]
        results = scan_column("quantity", values)
        assert len(results) == 0
