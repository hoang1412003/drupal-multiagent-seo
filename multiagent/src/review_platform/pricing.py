"""Uoc tinh chi phi LLM tu bang gia co version va nguon truy vet duoc."""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

import yaml


MILLION = Decimal(1_000_000)


@dataclass(frozen=True)
class CostEstimate:
    input_tokens: int
    output_tokens: int
    estimated_usd: Decimal | None
    pricing_version: int
    effective_at: date
    currency: str
    source: str
    unknown_models: tuple[str, ...]


@dataclass(frozen=True)
class _ModelPrice:
    input_per_million: Decimal
    output_per_million: Decimal


@dataclass(frozen=True)
class _Pricing:
    version: int
    currency: str
    effective_at: date
    source: str
    models: dict[str, _ModelPrice]


def _decimal(name: str, value) -> Decimal:
    if isinstance(value, bool):
        raise ValueError(f"{name} phai la so khong am")
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError(f"{name} phai la so khong am") from exc
    if not parsed.is_finite() or parsed < 0:
        raise ValueError(f"{name} phai la so khong am")
    return parsed


def _load_pricing(path: Path) -> _Pricing:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        version = raw["version"]
        currency = raw["currency"]
        effective_at = date.fromisoformat(raw["effective_at"])
        source = raw["source"]
        raw_models = raw["models"]
    except (OSError, KeyError, TypeError, ValueError, yaml.YAMLError) as exc:
        raise ValueError(f"pricing config khong hop le: {path}") from exc

    if isinstance(version, bool) or not isinstance(version, int) or version < 1:
        raise ValueError("pricing version phai la so nguyen duong")
    if currency != "USD":
        raise ValueError("pricing currency hien chi ho tro USD")
    if not isinstance(source, str) or not source.startswith("https://"):
        raise ValueError("pricing source phai la HTTPS URL")
    if not isinstance(raw_models, dict) or not raw_models:
        raise ValueError("pricing models khong duoc rong")

    models: dict[str, _ModelPrice] = {}
    for model, values in raw_models.items():
        if not isinstance(model, str) or not model.strip() or not isinstance(values, dict):
            raise ValueError("pricing model khong hop le")
        try:
            input_price = _decimal(
                f"models.{model}.input_usd_per_million",
                values["input_usd_per_million"],
            )
            output_price = _decimal(
                f"models.{model}.output_usd_per_million",
                values["output_usd_per_million"],
            )
        except KeyError as exc:
            raise ValueError(f"pricing model {model} thieu truong") from exc
        models[model] = _ModelPrice(input_price, output_price)

    return _Pricing(version, currency, effective_at, source, models)


def _token_count(row: dict, key: str) -> int:
    if key not in row:
        raise ValueError(f"usage thieu {key}")
    value = row[key]
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"usage.{key} phai la so nguyen khong am")
    return value


def estimate_usage(usage: list[dict], pricing_path: Path) -> CostEstimate:
    """Tinh token va USD; chi mot model chua co gia cung lam USD thanh unknown."""
    if not isinstance(usage, list):
        raise ValueError("usage phai la list")
    pricing = _load_pricing(Path(pricing_path))
    input_tokens = 0
    output_tokens = 0
    estimated = Decimal(0)
    unknown_models: set[str] = set()

    for row in usage:
        if not isinstance(row, dict):
            raise ValueError("moi usage entry phai la object")
        model = row.get("model")
        if not isinstance(model, str) or not model.strip():
            raise ValueError("usage.model khong duoc rong")
        current_input = _token_count(row, "input_tokens")
        current_output = _token_count(row, "output_tokens")
        input_tokens += current_input
        output_tokens += current_output

        price = pricing.models.get(model)
        if price is None:
            unknown_models.add(model)
            continue
        estimated += (
            Decimal(current_input) * price.input_per_million
            + Decimal(current_output) * price.output_per_million
        ) / MILLION

    unknown = tuple(sorted(unknown_models))
    return CostEstimate(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        estimated_usd=None if unknown else estimated,
        pricing_version=pricing.version,
        effective_at=pricing.effective_at,
        currency=pricing.currency,
        source=pricing.source,
        unknown_models=unknown,
    )
