"""
SahiRate — know your real rate before you quote.
A small SaaS for Pakistani freelancers: finds your floor rate, checks what a
quote really pays in PKR, and compares platforms after every fee and tax.

Run locally:   streamlit run app.py
"""
from dataclasses import replace

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from calculator import (
    DEFAULT_USD_PKR,
    PAYOUTS,
    PLATFORMS,
    TAX_RATE_NON_PSEB,
    TAX_RATE_PSEB,
    Breakdown,
    CostSettings,
    breakdown_from_gross,
    rate_plan,
)

st.set_page_config(
    page_title="SahiRate · Freelance rate calculator for Pakistan",
    page_icon="💸",
    layout="wide",
)

TEAL = "#0f766e"
RED = "#c2410c"


# --- Formatting helpers ------------------------------------------------------

def pkr(x: float) -> str:
    return f"Rs {x:,.0f}"


def usd(x: float, decimals: int = 2) -> str:
    return f"${x:,.{decimals}f}"


def signed_usd(x: float) -> str:
    """Leading +/- so st.metric colours the delta correctly."""
    return f"-${abs(x):,.2f}" if x < 0 else f"+${x:,.2f}"


def short_pkr(x: float) -> str:
    if abs(x) >= 1_000_000:
        return f"Rs {x / 1_000_000:.2f}M"
    if abs(x) >= 1_000:
        return f"Rs {x / 1_000:.1f}k"
    return f"Rs {x:,.0f}"


def waterfall(b: Breakdown, title: str) -> go.Figure:
    """Client payment -> each deduction -> what lands in your bank."""
    costs = b.cost_rows()
    fig = go.Figure(
        go.Waterfall(
            orientation="v",
            measure=["absolute"] + ["relative"] * len(costs) + ["total"],
            x=["Client pays"] + [name for name, _ in costs] + ["You keep"],
            y=[b.gross_pkr] + [-value for _, value in costs] + [0],
            text=[short_pkr(b.gross_pkr)]
            + [f"−{short_pkr(value)}" for _, value in costs]
            + [short_pkr(b.net_pkr)],
            textposition="outside",
            connector={"line": {"color": "rgba(120,120,120,0.35)"}},
            decreasing={"marker": {"color": RED}},
            increasing={"marker": {"color": TEAL}},
            totals={"marker": {"color": TEAL}},
        )
    )
    fig.update_layout(
        title=title,
        height=400,
        margin={"l": 10, "r": 10, "t": 50, "b": 10},
        yaxis_title="PKR",
        showlegend=False,
    )
    return fig


def breakdown_table(b: Breakdown) -> pd.DataFrame:
    rows = [("Client pays", b.gross_pkr)]
    rows += [(name, -value) for name, value in b.cost_rows()]
    rows.append(("You keep", b.net_pkr))
    return pd.DataFrame(
        {
            "Step": [r[0] for r in rows],
            "PKR": [pkr(r[1]) for r in rows],
            "% of payment": [f"{100 * r[1] / b.gross_pkr:.1f}%" if b.gross_pkr else "—" for r in rows],
        }
    )


# --- Sidebar: how you get paid ----------------------------------------------

with st.sidebar:
    st.header("How you get paid")

    platform = st.selectbox("Platform", list(PLATFORMS), index=0)
    platform_fee = st.slider(
        "Marketplace fee (%)",
        min_value=0.0,
        max_value=25.0,
        value=PLATFORMS[platform]["fee_pct"],
        step=0.5,
        key=f"fee_{platform}",
        help=PLATFORMS[platform]["help"],
    )

    payout_options = [
        name for name in PAYOUTS if platform == "Upwork" or not name.startswith("Upwork")
    ]
    payout = st.selectbox("Payout route", payout_options, index=0)
    payout_cfg = PAYOUTS[payout]
    withdrawal_fee = st.number_input(
        "Fee per withdrawal (USD)",
        min_value=0.0,
        max_value=50.0,
        value=float(payout_cfg["flat_usd"]),
        step=0.25,
        key=f"wd_{payout}",
        help=payout_cfg["help"],
    )
    fx_markup = st.number_input(
        "Conversion markup vs interbank (%)",
        min_value=0.0,
        max_value=10.0,
        value=float(payout_cfg["fx_markup_pct"]),
        step=0.1,
        key=f"fx_{payout}",
        help="How far below the interbank rate your money is converted. "
             "Compare your last withdrawal statement with the SBP rate that day.",
    )
    withdrawals = st.number_input(
        "Withdrawals per month", min_value=1, max_value=30, value=2, step=1
    )

    st.divider()
    pseb = st.toggle(
        "Registered with PSEB",
        value=True,
        help="PSEB-registered IT freelancers pay a 0.25% final tax on foreign "
             "remittances; others pay 1%. The 0.25% regime runs to June 2029.",
    )
    tax_pct = TAX_RATE_PSEB if pseb else TAX_RATE_NON_PSEB
    st.caption(f"Tax withheld by your bank: **{tax_pct}%** of each remittance")

    usd_pkr = st.number_input(
        "USD → PKR interbank rate",
        min_value=100.0,
        max_value=500.0,
        value=DEFAULT_USD_PKR,
        step=0.1,
        help="Default is the SBP interbank rate in late Oct 2026. Update it to today's rate.",
    )

costs = CostSettings(
    platform_fee_pct=platform_fee,
    withdrawal_fee_usd=withdrawal_fee,
    withdrawals_per_month=int(withdrawals),
    fx_markup_pct=fx_markup,
    tax_pct=tax_pct,
    usd_pkr=usd_pkr,
)


# --- Header --------------------------------------------------------------------

st.title("💸 SahiRate")
st.markdown(
    "**Know your real rate before you quote.** Pakistani freelancers lose a slice of "
    "every dollar to marketplace fees, withdrawal charges, conversion markups and tax. "
    "SahiRate works backwards from the rupees you need, so you never quote below cost."
)

tab_rate, tab_quote, tab_compare, tab_about = st.tabs(
    ["🎯 Find my rate", "🧾 Check a quote", "⚖️ Compare platforms", "ℹ️ Assumptions & sources"]
)


# --- Tab 1: Find my rate -------------------------------------------------------

with tab_rate:
    left, right = st.columns(2)
    with left:
        st.subheader("Your monthly goal")
        take_home = st.number_input(
            "Take-home you want each month (PKR)",
            min_value=0, max_value=10_000_000, value=200_000, step=5_000,
        )
        expenses = st.number_input(
            "Work expenses per month (PKR)",
            min_value=0, max_value=5_000_000, value=25_000, step=1_000,
            help="Internet, electricity and UPS, software, coworking, Upwork Connects…",
        )
        buffer = st.slider(
            "Buffer for slow months and savings (%)", min_value=0, max_value=50, value=15,
        )
    with right:
        st.subheader("Your time")
        hours_week = st.slider("Hours you work per week", min_value=5, max_value=70, value=40)
        billable = st.slider(
            "Share of those hours a client pays for (%)",
            min_value=10, max_value=100, value=60,
            help="The rest goes to proposals, unpaid revisions, admin and learning.",
        )
        weeks_off = st.slider(
            "Weeks off per year (Eid, holidays, sick days)", min_value=0, max_value=16, value=4,
        )

    plan = rate_plan(take_home, expenses, buffer, hours_week, billable, weeks_off, costs)

    st.divider()
    if take_home + expenses == 0:
        st.warning("Enter a take-home goal or your expenses to see your floor rate.")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Your floor rate", f"{usd(plan.hourly_usd)}/hr")
    m2.metric("Bill each month", usd(plan.gross_usd_per_month, 0))
    m3.metric("Billable hours / month", f"{plan.billable_hours:.0f}")
    m4.metric("You keep", f"{plan.breakdown.keep_pct:.1f}%")

    st.info(
        f"On **{platform}**, quoting below **{usd(plan.hourly_usd)}/hr** means the job "
        f"doesn't cover your goal of {pkr(plan.net_needed_pkr)} a month "
        f"(take-home + expenses + buffer). Every deduction is shown below."
    )

    st.plotly_chart(
        waterfall(plan.breakdown, "Where one month of billing goes"),
        key="rate_waterfall",
    )

    summary = pd.DataFrame(
        [
            ("Platform", platform),
            ("Marketplace fee (%)", platform_fee),
            ("Payout route", payout),
            ("Withdrawal fee (USD)", withdrawal_fee),
            ("Withdrawals per month", int(withdrawals)),
            ("Conversion markup (%)", fx_markup),
            ("Tax withheld (%)", tax_pct),
            ("USD to PKR rate", usd_pkr),
            ("Take-home goal (PKR)", take_home),
            ("Expenses (PKR)", expenses),
            ("Buffer (%)", buffer),
            ("Net needed per month (PKR)", round(plan.net_needed_pkr)),
            ("Billable hours per month", round(plan.billable_hours, 1)),
            ("Gross to bill per month (USD)", round(plan.gross_usd_per_month, 2)),
            ("Floor hourly rate (USD)", round(plan.hourly_usd, 2)),
            ("Share you keep (%)", round(plan.breakdown.keep_pct, 1)),
        ],
        columns=["Item", "Value"],
    )
    st.download_button(
        "⬇️ Download my rate plan (CSV)",
        data=summary.to_csv(index=False).encode("utf-8"),
        file_name="sahirate-rate-plan.csv",
        mime="text/csv",
    )


# --- Tab 2: Check a quote --------------------------------------------------------

with tab_quote:
    st.subheader("What will this job actually pay me?")
    kind = st.radio("Quote type", ["Hourly", "Fixed price"], horizontal=True)

    q1, q2, q3 = st.columns(3)
    if kind == "Hourly":
        rate = q1.number_input("Hourly rate (USD)", min_value=1.0, max_value=500.0, value=10.0, step=0.5)
        est_hours = q2.number_input("Hours", min_value=1.0, max_value=2_000.0, value=20.0, step=1.0)
        gross = rate * est_hours
    else:
        gross = q1.number_input("Project price (USD)", min_value=5.0, max_value=100_000.0, value=150.0, step=5.0)
        est_hours = q2.number_input(
            "Honest hours estimate (incl. revisions)",
            min_value=1.0, max_value=2_000.0, value=15.0, step=1.0,
        )
    wd_this = q3.number_input("Withdrawals for this payment", min_value=1, max_value=10, value=1, step=1)

    quote = breakdown_from_gross(gross, costs, withdrawals=int(wd_this))
    effective = gross / est_hours

    k1, k2, k3 = st.columns(3)
    k1.metric("Lands in your bank", pkr(quote.net_pkr))
    k2.metric("You keep", f"{quote.keep_pct:.1f}%")
    k3.metric(
        "Effective rate",
        f"{usd(effective)}/hr",
        delta=f"{signed_usd(effective - plan.hourly_usd)} vs floor",
        delta_color="normal",
    )

    if effective >= plan.hourly_usd:
        st.success(
            f"This job clears your floor rate of {usd(plan.hourly_usd)}/hr. "
            f"You take home {pkr(quote.net_pkr / est_hours)} for every hour you put in."
        )
    else:
        st.error(
            f"This job pays below your floor rate of {usd(plan.hourly_usd)}/hr. "
            f"To cover your costs for {est_hours:.0f} hours, quote at least "
            f"**{usd(plan.hourly_usd * est_hours, 0)}**."
        )

    chart_col, table_col = st.columns([3, 2])
    with chart_col:
        st.plotly_chart(waterfall(quote, f"Where your {usd(gross, 0)} goes"), key="quote_waterfall")
    with table_col:
        st.dataframe(breakdown_table(quote), hide_index=True)


# --- Tab 3: Compare platforms --------------------------------------------------------

with tab_compare:
    st.subheader("Same goal, different platforms")
    st.caption(
        f"Uses your goal and time from *Find my rate*, your payout route ({payout}) "
        f"and your tax status. Upwork uses the fee in the sidebar when it's selected."
    )

    rows = []
    for name, cfg in PLATFORMS.items():
        fee = platform_fee if name == platform else cfg["fee_pct"]
        c = replace(costs, platform_fee_pct=fee)
        p = rate_plan(take_home, expenses, buffer, hours_week, billable, weeks_off, c)
        thousand = breakdown_from_gross(1_000, c, withdrawals=1)
        rows.append(
            {
                "Platform": name,
                "Fee (%)": fee,
                "Floor rate (USD/hr)": round(p.hourly_usd, 2),
                "Bill per month (USD)": round(p.gross_usd_per_month),
                "$1,000 job lands as (PKR)": round(thousand.net_pkr),
                "You keep (%)": round(thousand.keep_pct, 1),
            }
        )
    compare = pd.DataFrame(rows)
    st.dataframe(compare, hide_index=True)
    st.bar_chart(compare, x="Platform", y="Floor rate (USD/hr)", color=TEAL)

    cheapest = compare.loc[compare["Floor rate (USD/hr)"].idxmin()]
    priciest = compare.loc[compare["Floor rate (USD/hr)"].idxmax()]
    gap = priciest["Floor rate (USD/hr)"] - cheapest["Floor rate (USD/hr)"]
    if gap < 0.005:
        st.markdown("With these settings, every option needs the same rate.")
    else:
        st.markdown(
            f"Earning the same rupees takes **{usd(gap)}/hr more** on **{priciest['Platform']}** "
            f"than on **{cheapest['Platform']}**. That gap is what the marketplace charges for "
            "finding you clients, so weigh it against how much work each one actually brings."
        )


# --- Tab 4: Assumptions & sources --------------------------------------------------

with tab_about:
    st.subheader("How SahiRate calculates")
    st.markdown(
        """
Client pays (USD) → **marketplace fee** → **withdrawal fee** per withdrawal →
converted to PKR at the **interbank rate minus a markup** → **withholding tax** on the
remittance → what lands in your bank.

Your floor rate is the hourly price at which a month of billable hours covers your
take-home, expenses and buffer after all of the above.

**Defaults (checked Nov 2026, all editable in the sidebar)**

| Setting | Default | Notes |
|---|---|---|
| Upwork fee | 10% | Variable 0–15% per contract since May 2025, shown on each proposal |
| Fiverr fee | 20% | Flat, including tips and extras |
| Payoneer → bank | ~2% markup | Some routes cost up to 3% |
| Upwork Direct to Local Bank | $0.99 + ~1% | Markup is an estimate |
| Wise | ~0.6% | Typically 0.4–0.7% for USD→PKR |
| Tax (PSEB-registered) | 0.25% | Final tax on IT export proceeds, extended to June 2029 |
| Tax (not registered) | 1% | |
| USD→PKR | Rs 277.7 | SBP interbank, late Oct 2026 |

**Sources**
- [Upwork: Freelancer Service Fee](https://support.upwork.com/hc/en-us/articles/211062538)
- [Upwork fees in Pakistan, 2026 (Elevate Pay)](https://www.elevatepay.co/blog/upwork-fees-pakistan)
- [Fiverr seller fee 2026 (AiProposer)](https://aiproposer.com/learn/fiverr-service-fee)
- [Payoneer vs Wise for Pakistani freelancers 2026 (AbroadMate)](https://abroadmate.me/guides/payoneer-vs-wise-pakistan-freelancers-2026)
- [0.25% PSEB rate extended to 2029 (Beancount)](https://beancount.io/bg/blog/2026/08/13/pakistan-it-freelancers-0-25-percent-pseb-2029-guide)
- [Pakistan Economic Survey 2025-26, IT chapter](https://www.finance.gov.pk/survey/chapter_26/15_Information_Technology.pdf)

SahiRate is a planning tool, not tax or financial advice. Check the fee on each
contract and confirm tax rules with FBR, PSEB or a tax advisor.
"""
    )

st.divider()
st.caption("SahiRate · Free during beta · Built with Streamlit · Not tax or financial advice")
