# Require the complete financial context

Run the commands in README.md. The original seven requests remain in results/exercise.json: two abstentions and five rejections.

The Apple request names a complete-looking context but guesses us-gaap/2026. Its source fact uses us-gaap/2025, so the lookup correctly abstains. The second request omits required context fields and also abstains. The remaining requests ask for a formal-restatement verdict, original-time features, exact fiscal dates, forecast accuracy or investment advice; each is rejected.

The additional results/positive_control.json uses the actual taxonomy for the same Apple accession, Assets tag, rounded end date, instant duration, USD and blank segment/coregistrant context. It returns one qualified current source value. This control was introduced after the mistaken expectation was found and is labeled post-analysis. Read VALIDATOR_CORRECTION.md for the preserved original inputs, checker and output hashes.

Inspect src/exercise.py and tests/test_boundaries.py. Explain why current context identity does not establish original-time availability, why a missing numeric value is not zero, and why repeated presentation lines do not create duplicate financial facts.

For an extension, add a caller-facing context contract carrying every source-key field, numeric-state status, units, rounded-date limitations and material unknowns. Preserve frozen research files and use a separate module with relevant boundary tests. The current interface does not certify arbitrary caller data or a production service.
