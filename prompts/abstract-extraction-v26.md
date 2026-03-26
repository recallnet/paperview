You are extracting structured strategy-mechanism metadata from a research paper abstract.

Return exactly one JSON object. Do not wrap the JSON in markdown fences.
Do not add commentary outside the JSON.

Return a paper-level response object with this shape:

```json
{
  "paper_id": "<copy from payload>",
  "response_contract_version": "mechanism-instance-batch-v1",
  "mechanism_instances": []
}
```

Rules:
- `mechanism_instances` may contain `0..N` items.
- Each item inside `mechanism_instances` must match the extraction schema exactly.
- Copy `paper_id` exactly from the payload into the wrapper and every mechanism item.
- Use exact enum tokens only. If a narrower label is not justified, use `other`.
- `literature_family` and `evaluation_split` are context for interpretation only. Do not emit them in the output.

When to return an empty `mechanism_instances` array:
- the abstract is clearly off-domain for executable market mechanisms
- the paper is generic forecasting, risk modeling, valuation, policy measurement, ethics, logistics, or optimization without a concrete transferable mechanism
- the abstract does not support even a conservative low-confidence mechanism instance

When not to return an empty array:
- the abstract contains a concrete execution pattern, linked-market inconsistency, market-design exploit, market-making dynamic, queue/inventory mechanism, or explicit transferable failure mode

Mixed-family interpretation rules:
- Sports betting and pari-mutuel papers can still map to portable market microstructure or pricing mechanisms.
- Auction and market-design papers can surface `market_design_exploit`, `regime_filter`, or `failure_mode_or_anti_pattern` insights.
- Electricity and balancing-market papers can surface transferable inventory, congestion, settlement, or asynchronous-update mechanisms.
- DeFi / AMM papers count as real mechanism sources only when the abstract explicitly mentions on-chain markets, AMMs, liquidity pools, tokens, or smart-contract venues.
- Freight, logistics, policy, or generic optimization papers should collapse to an empty array unless the abstract clearly contains a real market-pricing or auction mechanism.

Mechanism-instance rules:
- Every mechanism instance must include the full required extraction-schema key set.
- `mechanism_name` and `mechanism_summary` must be concrete, never placeholders.
- Promising candidates must carry specific blocker context through `fragility_flags`, `capacity_constraints`, `failure_regimes`, or `negative_transfer_rationale`.
- Use conservative `tradecore_fit` and portability judgments. Do not overclaim transfer into prediction markets.

Example: clearly off-domain paper

```json
{
  "paper_id": "demo-off-domain",
  "response_contract_version": "mechanism-instance-batch-v1",
  "mechanism_instances": []
}
```

Example: one conservative mechanism instance

```json
{
  "paper_id": "demo-market-making",
  "response_contract_version": "mechanism-instance-batch-v1",
  "mechanism_instances": [
    {
      "paper_id": "demo-market-making",
      "mechanism_name": "Inventory-aware cooperative quoting",
      "mechanism_summary": "Repeated market makers can converge to stable wide-quote behavior under inventory pressure and thin order-book conditions.",
      "insight_type": "crowding_or_decay_warning",
      "original_market_domain": "market_microstructure",
      "instrument_type": ["limit_order_book_claim"],
      "edge_source": ["inventory_pressure"],
      "execution_style": ["passive_market_making"],
      "holding_horizon": "intraday",
      "required_market_conditions": ["observable_order_book", "thin_book"],
      "required_assumptions": ["order_book_state_is_observable", "inventory_can_be_rebalanced"],
      "assumption_violations": ["inventory_cannot_be_rebalanced", "book_visibility_degrades"],
      "fragility_flags": ["sensitive_to_inventory_constraints"],
      "capacity_constraints": ["inventory_budget_limits"],
      "failure_regimes": ["one_sided_flow_regime"],
      "negative_transfer_rationale": ["depends_on_market_structure_not_present_in_target"],
      "main_failure_modes": ["adverse_selection"],
      "evidence_strength": "medium",
      "prediction_market_portability": "low",
      "novel_market_portability": "medium",
      "tradecore_fit": "medium",
      "likely_crowding": "medium",
      "why_missed": ["other"]
    }
  ]
}
```
