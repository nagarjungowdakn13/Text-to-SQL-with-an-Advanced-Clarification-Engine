import pytest
from app.services.sql.validator import SQLValidator
from app.services.sql.repair import SQLRepairEngine
from app.services.llm.mock import MockLLMProvider
from app.services.schema.extractor import SchemaExtractor
from app.schemas.sql import SQLPlan
from app.core.config import settings

def test_sql_validator_safety():
    """Verify that only safe SELECT queries pass validation."""
    extractor = SchemaExtractor(settings.EXECUTION_DB_ADMIN_URL)
    schema = extractor.extract_schema()
    validator = SQLValidator()

    # Safe SELECT query
    ok, errs = validator.validate(
        "SELECT customer_id, first_name FROM customers WHERE country = 'USA';", 
        schema
    )
    assert ok
    assert len(errs) == 0

    # Blocked write commands (DML/DDL)
    ok, errs = validator.validate("INSERT INTO customers (first_name) VALUES ('Hacker');", schema)
    assert not ok
    assert any("Only SELECT queries" in e or "Forbidden statement" in e for e in errs)

    ok, errs = validator.validate("DROP TABLE customers;", schema)
    assert not ok
    assert any("Only SELECT" in e or "Forbidden statement" in e for e in errs)

    # Blocked dangerous functions
    ok, errs = validator.validate("SELECT first_name, pg_sleep(5) FROM customers;", schema)
    assert not ok
    assert any("Forbidden function" in e for e in errs)

    # Blocked non-allowlisted tables
    ok, errs = validator.validate("SELECT * FROM passwords_table;", schema)
    assert not ok
    assert any("Table 'passwords_table' does not exist" in e for e in errs)

    # Blocked non-allowlisted columns
    ok, errs = validator.validate("SELECT social_security_number FROM customers;", schema)
    assert not ok
    assert any("Column 'social_security_number' does not exist" in e for e in errs)

    # Blocked Cartesian Joins (Cross Join)
    ok, errs = validator.validate("SELECT * FROM customers JOIN orders;", schema)
    assert not ok
    assert any("JOIN without ON/USING" in e for e in errs)

    # Blocked implicit Cartesian Joins (FROM list)
    ok, errs = validator.validate("SELECT * FROM customers, orders;", schema)
    assert not ok
    assert any("Cartesian product" in e or "JOIN without ON/USING" in e or "Comma-separated" in e for e in errs)

def test_sql_repair_loop():
    """Verify that SQL Repair Engine correctly corrects syntax issues."""
    llm = MockLLMProvider()
    repair_engine = SQLRepairEngine(llm)
    extractor = SchemaExtractor(settings.EXECUTION_DB_ADMIN_URL)
    schema = extractor.extract_schema()

    # Simulate an invalid SQL plan
    bad_plan = SQLPlan(
        intent="List top customers",
        tables=["customers"],
        columns=["customer_id"],
        sql="SELECT customer_id, pg_sleep(10) FROM customers;", # Bad function
        confidence=0.5
    )

    repaired_plan = repair_engine.repair_plan(
        question="Show top customers",
        invalid_plan=bad_plan,
        errors=["Forbidden function call: 'pg_sleep' is dangerous and blocked."],
        schema=schema
    )

    # Repaired plan should be valid
    validator = SQLValidator()
    ok, errs = validator.validate(repaired_plan.sql, schema)
    assert ok
