# Day 5: Dependency Injection Part 2

Advanced patterns for production FastAPI applications.

## Files

1.  **01_yield_and_cleanup.py**: How to open/close resources (DBs, files) safely.
2.  **02_dependency_caching.py**: Demonstrates FastAPI's "once-per-request" caching logic.
3.  **03_levels_of_dependencies.py**: Applying logic Globally vs Router vs Endpoint.
4.  **04_security_dependencies.py**: API Keys and Role-Based Access Control (RBAC).
5.  **05_database_patterns.py**: SQLAlchemy transactions and Repository pattern.
6.  **06_testing_overrides.py**: How to mock dependencies for unit tests.
7.  **07_advanced_composition.py**: Grouping dependencies into containers and Factories.

## Usage

Run any file with uvicorn:
`uvicorn 01_yield_and_cleanup:app --reload`

Run the test file directly with python:
`python 06_testing_overrides.py`
