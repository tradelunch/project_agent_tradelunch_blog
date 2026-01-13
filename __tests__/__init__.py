# __tests__/__init__.py
"""
Test suite for tradelunch_blog_agents

This package contains all test files for the multi-agent blog processing system.

Test files:
- test_agents.py - Basic agent tests
- test_improved_agents.py - Improved agent tests with LLM integration
- test_llm_providers.py - LLM provider configuration tests
- test_snowflake.py - Snowflake ID generation tests
- test_category_storage.py - Category storage logic tests

Usage:
    # Run all tests
    python -m pytest __tests__/

    # Run specific test file
    python __tests__/test_improved_agents.py

    # Run with coverage
    pytest --cov=agents --cov-fail-under=80 __tests__/
"""
