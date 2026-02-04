"""
Regression tests for SignalValidator profile configuration.

These tests ensure that /api/v1/signals uses the FULL validator (12 rules)
and not the DEFAULT validator (6 rules).

Background:
- 2026-02-03: Audit discovered api/dependencies.py was using create_default()
  which bypassed 6 critical validation rules.
- Fix: Changed to create_full() to ensure all 12 rules execute.
- These tests prevent regression.
"""

import pytest
from omen.domain.services.signal_validator import SignalValidator
from omen.api.dependencies import get_signal_only_pipeline


class TestValidatorProfileRegression:
    """Ensure full validator is used by API dependencies."""

    def test_create_default_has_6_rules(self):
        """Verify create_default() returns validator with exactly 6 rules."""
        validator = SignalValidator.create_default()
        
        assert len(validator.rules) == 6, (
            f"Expected create_default() to have 6 rules, got {len(validator.rules)}"
        )
        
        rule_names = [type(r).__name__ for r in validator.rules]
        expected_default_rules = [
            "LiquidityValidationRule",
            "AnomalyDetectionRule",
            "SemanticRelevanceRule",
            "GeographicRelevanceRule",
            "CrossSourceValidationRule",
            "SourceDiversityRule",
        ]
        assert rule_names == expected_default_rules, (
            f"create_default() rules mismatch. Got: {rule_names}"
        )

    def test_create_full_has_12_rules(self):
        """Verify create_full() returns validator with exactly 12 rules."""
        validator = SignalValidator.create_full()
        
        assert len(validator.rules) == 12, (
            f"Expected create_full() to have 12 rules, got {len(validator.rules)}"
        )
        
        rule_names = [type(r).__name__ for r in validator.rules]
        expected_full_rules = [
            # Core (6)
            "LiquidityValidationRule",
            "AnomalyDetectionRule",
            "SemanticRelevanceRule",
            "GeographicRelevanceRule",
            "CrossSourceValidationRule",
            "SourceDiversityRule",
            # Additional (6)
            "NewsQualityGateRule",
            "CommodityContextRule",
            "PortCongestionValidationRule",
            "ChokePointDelayValidationRule",
            "AISDataFreshnessRule",
            "AISDataQualityRule",
        ]
        assert rule_names == expected_full_rules, (
            f"create_full() rules mismatch. Got: {rule_names}"
        )

    def test_create_full_has_all_missing_rules_from_default(self):
        """Verify create_full() includes all rules missing from create_default()."""
        full_validator = SignalValidator.create_full()
        default_validator = SignalValidator.create_default()
        
        full_rule_names = {type(r).__name__ for r in full_validator.rules}
        default_rule_names = {type(r).__name__ for r in default_validator.rules}
        
        missing_in_default = full_rule_names - default_rule_names
        
        expected_missing = {
            "NewsQualityGateRule",
            "CommodityContextRule",
            "PortCongestionValidationRule",
            "ChokePointDelayValidationRule",
            "AISDataFreshnessRule",
            "AISDataQualityRule",
        }
        
        assert missing_in_default == expected_missing, (
            f"Missing rules mismatch. Expected: {expected_missing}, Got: {missing_in_default}"
        )

    def test_api_dependency_uses_full_validator(self):
        """
        CRITICAL REGRESSION TEST:
        Ensure get_signal_only_pipeline() returns pipeline with FULL validator.
        
        This test MUST FAIL if someone changes api/dependencies.py back to
        create_default().
        """
        # Clear lru_cache to ensure fresh instance
        get_signal_only_pipeline.cache_clear()
        
        pipeline = get_signal_only_pipeline()
        validator = pipeline._validator
        
        rule_count = len(validator.rules)
        rule_names = [type(r).__name__ for r in validator.rules]
        
        # MUST have 12 rules
        assert rule_count == 12, (
            f"REGRESSION DETECTED! API pipeline has {rule_count} rules instead of 12. "
            f"Rules present: {rule_names}. "
            f"Someone likely changed api/dependencies.py to use create_default() instead of create_full()!"
        )
        
        # Specifically check for the 6 critical rules that were previously bypassed
        critical_rules = [
            "NewsQualityGateRule",
            "CommodityContextRule",
            "PortCongestionValidationRule",
            "ChokePointDelayValidationRule",
            "AISDataFreshnessRule",
            "AISDataQualityRule",
        ]
        
        for rule_name in critical_rules:
            assert rule_name in rule_names, (
                f"REGRESSION DETECTED! Critical rule '{rule_name}' is missing from API validator! "
                f"Rules present: {rule_names}"
            )

    def test_api_dependency_has_news_quality_rule(self):
        """Ensure NewsQualityGateRule is active (blocks low-credibility news)."""
        get_signal_only_pipeline.cache_clear()
        pipeline = get_signal_only_pipeline()
        rule_names = [type(r).__name__ for r in pipeline._validator.rules]
        
        assert "NewsQualityGateRule" in rule_names, (
            f"NewsQualityGateRule not found! Low-credibility news will enter pipeline. "
            f"Rules: {rule_names}"
        )

    def test_api_dependency_has_ais_freshness_rule(self):
        """Ensure AISDataFreshnessRule is active (rejects stale maritime data)."""
        get_signal_only_pipeline.cache_clear()
        pipeline = get_signal_only_pipeline()
        rule_names = [type(r).__name__ for r in pipeline._validator.rules]
        
        assert "AISDataFreshnessRule" in rule_names, (
            f"AISDataFreshnessRule not found! Stale maritime signals will enter pipeline. "
            f"Rules: {rule_names}"
        )


class TestContainerValidatorConsistency:
    """Ensure all containers use full validator consistently."""

    def test_main_container_uses_full_validator(self):
        """Verify main Container.create_default() uses full validator."""
        from omen.application.container import Container
        
        container = Container.create_default()
        validator = container.validator
        
        rule_count = len(validator.rules)
        assert rule_count == 12, (
            f"Main container has {rule_count} rules instead of 12. "
            f"Container should use SignalValidator.create_full()!"
        )

    def test_api_and_container_validators_match(self):
        """Ensure API pipeline and Container use same validator profile."""
        from omen.application.container import get_container, reset_container
        
        # Reset to ensure fresh state
        reset_container()
        get_signal_only_pipeline.cache_clear()
        
        container = get_container()
        api_pipeline = get_signal_only_pipeline()
        
        container_rule_count = len(container.validator.rules)
        api_rule_count = len(api_pipeline._validator.rules)
        
        # Both should have 12 rules
        assert container_rule_count == 12, f"Container has {container_rule_count} rules"
        assert api_rule_count == 12, f"API pipeline has {api_rule_count} rules"
        
        container_rules = {type(r).__name__ for r in container.validator.rules}
        api_rules = {type(r).__name__ for r in api_pipeline._validator.rules}
        
        assert container_rules == api_rules, (
            f"Container and API pipeline have different rules! "
            f"Container: {container_rules}, API: {api_rules}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
