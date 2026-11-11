COST_PRECISION = 6


def compute_cost(usage, prices) -> float:
	"""Chi phí USD = token x đơn giá (USD / 1 triệu token), công thức duy nhất của app (ADR-002 #6)."""
	if not usage:
		return 0
	total = (
		usage.get("input_tokens", 0) * prices["price_input_per_mtok"]
		+ usage.get("cache_creation_input_tokens", 0) * prices["price_cache_write_per_mtok"]
		+ usage.get("cache_read_input_tokens", 0) * prices["price_cache_read_per_mtok"]
		+ usage.get("output_tokens", 0) * prices["price_output_per_mtok"]
	)
	return round(total / 1e6, COST_PRECISION)
