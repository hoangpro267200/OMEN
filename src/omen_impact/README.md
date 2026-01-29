# OMEN Impact Module (Deprecated Location)

## THIS MODULE DOES NOT BELONG IN OMEN

This module contains impact assessment logic that should be performed by
**downstream consumers** (e.g., RiskCast), not by the signal engine.

### Why this exists here (temporarily)
- Historical: OMEN was originally designed with impact translation
- Practical: Moving to RiskCast requires coordination
- Isolation: This module is now isolated from OMEN's public interface

### What this module does
- Translates signals into impact assessments
- Calculates: severity, delay_days, cost impact, risk exposure
- Applies domain rules: Red Sea, port closure, strike scenarios

### What OMEN (Signal Engine) should do
- Probability assessment
- Confidence measurement
- Context enrichment (geographic, temporal)
- Evidence chain management

### Migration Path
1. RiskCast imports omen_impact directly (current)
2. Copy omen_impact into RiskCast codebase
3. Remove omen_impact from OMEN repository

### Usage (for RiskCast or other consumers)
```python
from omen_impact import ImpactTranslator, ImpactAssessment
from omen_impact.rules.logistics import RedSeaDisruptionRule, PortClosureRule, StrikeImpactRule

# OMEN produces pure signal; consumer translates to impact
translator = ImpactTranslator(rules=[
    RedSeaDisruptionRule(),
    PortClosureRule(),
    StrikeImpactRule(),
])
impact = translator.translate(signal, domain=ImpactDomain.LOGISTICS, context=context)
```
