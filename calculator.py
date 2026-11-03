"""
SahiRate — pricing math for Pakistani freelancers.

Pure Python (no Streamlit import) so it can be unit-tested and reused by any
front end. The money flow it models, in order:

    client pays gross USD
      -> marketplace fee            (% of gross; Upwork 0–15%, Fiverr 20%)
      -> withdrawal fee(s)          (flat USD per withdrawal)
      -> USD -> PKR conversion      (interbank rate minus a markup %)
      -> withholding tax on export  (0.25% PSEB-registered, 1% otherwise)
      =  net PKR in your bank

Every default below is editable in the app. Figures were checked in Nov 2026;
fees and tax rules change, so the app always lets the user override them.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# --- Defaults (checked Nov 2026; all user-editable) -------------------------

DEFAULT_USD_PKR = 277.7  # SBP interbank close, late Oct 2026
TAX_RATE_PSEB = 0.25     # % final tax on IT export proceeds, PSEB-registered
TAX_RATE_NON_PSEB = 1.0  # % for freelancers not registered with PSEB

PLATFORMS: dict[str, dict] = {
    "Upwork": {
        "fee_pct": 10.0,
        "help": "Variable 0–15% per contract since May 2025, shown on each "
                "proposal and locked for that contract. 10% is a common middle value.",
    },
    "Fiverr": {
        "fee_pct": 20.0,
        "help": "Flat 20% on every order, including tips and extras.",
    },
    "Direct client": {
        "fee_pct": 0.0,
        "help": "No marketplace cut. You handle invoicing and collecting payment.",
    },
}

PAYOUTS: dict[str, dict] = {
    "Payoneer → local bank": {
        "flat_usd": 0.0,
        "fx_markup_pct": 2.0,
        "help": "Commonly reported as about 2% below the mid-market rate when "
                "withdrawing in PKR; some routes cost up to 3%.",
    },
    "Upwork Direct to Local Bank": {
        "flat_usd": 0.99,
        "fx_markup_pct": 1.0,
        "help": "$0.99 per withdrawal. The conversion rate is set by the provider; "
                "the 1% markup is an estimate, so edit it to match your statement.",
    },
    "Wise": {
        "flat_usd": 0.0,
        "fx_markup_pct": 0.6,
        "help": "Mid-market rate plus a transparent fee, typically 0.4–0.7% for USD→PKR.",
    },
}


# --- Data structures ---------------------------------------------------------

@dataclass(frozen=True)
class CostSettings:
    """Everything that sits between what the client pays and what you keep."""

    platform_fee_pct: float = 10.0
    withdrawal_fee_usd: float = 0.0
    withdrawals_per_month: int = 2
    fx_markup_pct: float = 2.0
    tax_pct: float = TAX_RATE_PSEB
    usd_pkr: float = DEFAULT_USD_PKR

    def __post_init__(self) -> None:
        for name in ("platform_fee_pct", "fx_markup_pct", "tax_pct"):
            value = getattr(self, name)
            if not 0 <= value < 100:
                raise ValueError(f"{name} must be between 0 and 100 (got {value})")
        if self.withdrawal_fee_usd < 0:
            raise ValueError("withdrawal_fee_usd cannot be negative")
        if self.withdrawals_per_month < 0:
            raise ValueError("withdrawals_per_month cannot be negative")
        if self.usd_pkr <= 0:
            raise ValueError("usd_pkr must be positive")


@dataclass(frozen=True)
class Breakdown:
    """Where each rupee of a payment goes."""

    gross_usd: float
    platform_fee_usd: float
    withdrawal_fees_usd: float
    converted_usd: float
    usd_pkr: float
    fx_loss_pkr: float
    tax_pkr: float
    net_pkr: float

    @property
    def gross_pkr(self) -> float:
        return self.gross_usd * self.usd_pkr

    @property
    def total_cost_pkr(self) -> float:
        return self.gross_pkr - self.net_pkr

    @property
    def keep_pct(self) -> float:
        return 100 * self.net_pkr / self.gross_pkr if self.gross_pkr else 0.0

    def cost_rows(self) -> list[tuple[str, float]]:
        """Deductions in PKR, in the order they happen."""
        return [
            ("Marketplace fee", self.platform_fee_usd * self.usd_pkr),
            ("Withdrawal fees", self.withdrawal_fees_usd * self.usd_pkr),
            ("Conversion markup", self.fx_loss_pkr),
            ("Tax withheld", self.tax_pkr),
        ]


@dataclass(frozen=True)
class RatePlan:
    net_needed_pkr: float
    gross_usd_per_month: float
    billable_hours: float
    hourly_usd: float
    breakdown: Breakdown = field(repr=False)


# --- Core calculations ---------------------------------------------------------

def breakdown_from_gross(
    gross_usd: float, costs: CostSettings, withdrawals: int | None = None
) -> Breakdown:
    """Follow a client payment of `gross_usd` all the way to your bank."""
    if gross_usd < 0:
        raise ValueError("gross_usd cannot be negative")
    n = costs.withdrawals_per_month if withdrawals is None else withdrawals

    platform_fee = gross_usd * costs.platform_fee_pct / 100
    after_platform = gross_usd - platform_fee
    withdrawal_fees = min(costs.withdrawal_fee_usd * n, after_platform)
    converted = after_platform - withdrawal_fees

    pkr_at_interbank = converted * costs.usd_pkr
    fx_loss = pkr_at_interbank * costs.fx_markup_pct / 100
    pkr_received = pkr_at_interbank - fx_loss
    tax = pkr_received * costs.tax_pct / 100
    net = pkr_received - tax

    return Breakdown(
        gross_usd=gross_usd,
        platform_fee_usd=platform_fee,
        withdrawal_fees_usd=withdrawal_fees,
        converted_usd=converted,
        usd_pkr=costs.usd_pkr,
        fx_loss_pkr=fx_loss,
        tax_pkr=tax,
        net_pkr=net,
    )


def gross_needed_for_net(
    net_pkr: float, costs: CostSettings, withdrawals: int | None = None
) -> float:
    """How much the client must pay (USD) for `net_pkr` to land in your bank."""
    if net_pkr < 0:
        raise ValueError("net_pkr cannot be negative")
    n = costs.withdrawals_per_month if withdrawals is None else withdrawals
    per_usd_converted = (
        costs.usd_pkr * (1 - costs.fx_markup_pct / 100) * (1 - costs.tax_pct / 100)
    )
    converted = net_pkr / per_usd_converted
    after_platform = converted + costs.withdrawal_fee_usd * n
    return after_platform / (1 - costs.platform_fee_pct / 100)


def billable_hours_per_month(
    hours_per_week: float, billable_pct: float, weeks_off_per_year: float
) -> float:
    """Hours a client actually pays for, averaged over the year."""
    working_weeks = max(52 - weeks_off_per_year, 0)
    return hours_per_week * (billable_pct / 100) * working_weeks / 12


def rate_plan(
    take_home_pkr: float,
    expenses_pkr: float,
    buffer_pct: float,
    hours_per_week: float,
    billable_pct: float,
    weeks_off_per_year: float,
    costs: CostSettings,
) -> RatePlan:
    """The minimum hourly rate that funds your goals after every cost."""
    net_needed = (take_home_pkr + expenses_pkr) * (1 + buffer_pct / 100)
    gross = gross_needed_for_net(net_needed, costs)
    hours = billable_hours_per_month(hours_per_week, billable_pct, weeks_off_per_year)
    if hours <= 0:
        raise ValueError("Billable hours must be greater than zero")
    return RatePlan(
        net_needed_pkr=net_needed,
        gross_usd_per_month=gross,
        billable_hours=hours,
        hourly_usd=gross / hours,
        breakdown=breakdown_from_gross(gross, costs),
    )
