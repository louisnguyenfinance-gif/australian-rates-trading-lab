import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


# ---------------------------------------------------
# Bond mathematics
# ---------------------------------------------------

def bond_price(face_value, coupon_rate, ytm, years, frequency=2):
    periods = int(years * frequency)
    coupon = face_value * coupon_rate / frequency
    periodic_yield = ytm / frequency

    price = 0

    for t in range(1, periods + 1):
        price += coupon / (1 + periodic_yield) ** t

    price += face_value / (1 + periodic_yield) ** periods

    return price


def macaulay_duration(face_value, coupon_rate, ytm, years, frequency=2):
    periods = int(years * frequency)
    coupon = face_value * coupon_rate / frequency
    periodic_yield = ytm / frequency

    price = bond_price(
        face_value,
        coupon_rate,
        ytm,
        years,
        frequency
    )

    weighted_pv = 0

    for t in range(1, periods + 1):

        cash_flow = coupon

        if t == periods:
            cash_flow += face_value

        pv = cash_flow / (1 + periodic_yield) ** t

        time_years = t / frequency

        weighted_pv += time_years * pv

    return weighted_pv / price


def modified_duration(mac_duration, ytm, frequency=2):
    return mac_duration / (1 + ytm / frequency)


def bond_convexity(face_value, coupon_rate, ytm, years, frequency=2):
    periods = int(years * frequency)
    coupon = face_value * coupon_rate / frequency
    periodic_yield = ytm / frequency

    price = bond_price(
        face_value,
        coupon_rate,
        ytm,
        years,
        frequency
    )

    convexity_sum = 0

    for t in range(1, periods + 1):

        cash_flow = coupon

        if t == periods:
            cash_flow += face_value

        convexity_sum += (
            cash_flow * t * (t + 1)
            / (1 + periodic_yield) ** (t + 2)
        )

    return convexity_sum / (price * frequency ** 2)


# ---------------------------------------------------
# App
# ---------------------------------------------------

st.set_page_config(
    page_title="Australian Rates Risk Engine",
    layout="wide"
)

st.title("Australian Rates Risk Engine")

st.write(
    """
    Interactive fixed-income risk tool for analysing bond pricing,
    duration, convexity, DV01 and P&L under changes in interest rates.
    """
)

st.caption(
    "Built as part of the Australian Rates Trading Lab."
)


tab1, tab2 = st.tabs([
    "Single Bond",
    "Portfolio Stress Test"
])


# ===================================================
# SINGLE BOND
# ===================================================

with tab1:

    st.header("Single Bond Risk Calculator")

    col1, col2, col3 = st.columns(3)

    with col1:

        face_value = st.number_input(
            "Face Value ($)",
            value=100.0,
            min_value=1.0
        )

        coupon_pct = st.number_input(
            "Coupon Rate (%)",
            value=4.00,
            step=0.10
        )

    with col2:

        ytm_pct = st.number_input(
            "Yield to Maturity (%)",
            value=4.50,
            step=0.01
        )

        years = st.number_input(
            "Maturity (Years)",
            value=5,
            min_value=1
        )

    with col3:

        frequency = st.selectbox(
            "Coupon Frequency",
            [1, 2, 4],
            index=1
        )

        position_notional = st.number_input(
            "Position Notional ($)",
            value=1_000_000.0,
            step=100_000.0
        )


    coupon_rate = coupon_pct / 100
    ytm = ytm_pct / 100


    price = bond_price(
        face_value,
        coupon_rate,
        ytm,
        years,
        frequency
    )

    mac_duration = macaulay_duration(
        face_value,
        coupon_rate,
        ytm,
        years,
        frequency
    )

    mod_duration = modified_duration(
        mac_duration,
        ytm,
        frequency
    )

    convexity = bond_convexity(
        face_value,
        coupon_rate,
        ytm,
        years,
        frequency
    )

    market_value = (
        position_notional * price / face_value
    )

    dv01 = (
        mod_duration
        * market_value
        * 0.0001
    )


    st.subheader("Risk Metrics")

    m1, m2, m3, m4 = st.columns(4)

    m1.metric(
        "Bond Price",
        f"{price:.4f}"
    )

    m2.metric(
        "Modified Duration",
        f"{mod_duration:.3f}"
    )

    m3.metric(
        "Convexity",
        f"{convexity:.2f}"
    )

    m4.metric(
        "Position DV01",
        f"${dv01:,.2f}"
    )


    st.subheader("Stress Test")

    shock_bp = st.slider(
        "Yield Shock (bp)",
        min_value=-200,
        max_value=200,
        value=25,
        step=5
    )

    shock = shock_bp / 10000

    shocked_ytm = ytm + shock

    shocked_price = bond_price(
        face_value,
        coupon_rate,
        shocked_ytm,
        years,
        frequency
    )

    exact_pnl = (
        (shocked_price - price)
        / face_value
        * position_notional
    )

    duration_pnl = (
        -mod_duration
        * shock
        * market_value
    )

    duration_convexity_pnl = (
        (
            -mod_duration * shock
            + 0.5 * convexity * shock ** 2
        )
        * market_value
    )


    p1, p2, p3 = st.columns(3)

    p1.metric(
        "Exact P&L",
        f"${exact_pnl:,.2f}"
    )

    p2.metric(
        "Duration Estimate",
        f"${duration_pnl:,.2f}"
    )

    p3.metric(
        "Duration + Convexity",
        f"${duration_convexity_pnl:,.2f}"
    )


    # Full sensitivity analysis

    shock_range = np.arange(-200, 201, 10)

    results = []

    for bp in shock_range:

        dy = bp / 10000

        exact_price = bond_price(
            face_value,
            coupon_rate,
            ytm + dy,
            years,
            frequency
        )

        exact_change = (
            exact_price - price
        )

        duration_change = (
            -mod_duration
            * dy
            * price
        )

        duration_convexity_change = (
            (
                -mod_duration * dy
                + 0.5 * convexity * dy ** 2
            )
            * price
        )

        results.append({
            "Shock": bp,
            "Exact": exact_change,
            "Duration": duration_change,
            "Duration + Convexity": duration_convexity_change
        })


    sensitivity = pd.DataFrame(results)

    fig, ax = plt.subplots(figsize=(10, 5))

    ax.plot(
        sensitivity["Shock"],
        sensitivity["Exact"],
        label="Exact Repricing"
    )

    ax.plot(
        sensitivity["Shock"],
        sensitivity["Duration"],
        label="Duration"
    )

    ax.plot(
        sensitivity["Shock"],
        sensitivity["Duration + Convexity"],
        label="Duration + Convexity"
    )

    ax.axhline(0, linewidth=1)

    ax.set_xlabel("Yield Shock (bp)")
    ax.set_ylabel("Price Change")
    ax.set_title("Bond Price Sensitivity")

    ax.legend()
    ax.grid(alpha=0.3)

    st.pyplot(fig)


# ===================================================
# PORTFOLIO
# ===================================================

with tab2:

    st.header("Portfolio Stress Test")

    default_portfolio = pd.DataFrame({

        "Bond": [
            "2Y Bond",
            "5Y Bond",
            "10Y Bond"
        ],

        "Coupon (%)": [
            4.00,
            4.50,
            5.00
        ],

        "YTM (%)": [
            4.619,
            4.656,
            5.023
        ],

        "Maturity": [
            2,
            5,
            10
        ],

        "Notional ($)": [
            2_000_000,
            3_000_000,
            1_500_000
        ]
    })


    edited_portfolio = st.data_editor(
        default_portfolio,
        num_rows="dynamic",
        use_container_width=True
    )


    portfolio_shock_bp = st.slider(
        "Portfolio Parallel Yield Shock (bp)",
        min_value=-200,
        max_value=200,
        value=25,
        step=5
    )

    shock = portfolio_shock_bp / 10000


    portfolio_results = []

    for _, bond in edited_portfolio.iterrows():

        coupon = bond["Coupon (%)"] / 100
        yield_rate = bond["YTM (%)"] / 100

        price_i = bond_price(
            100,
            coupon,
            yield_rate,
            bond["Maturity"],
            2
        )

        mac_i = macaulay_duration(
            100,
            coupon,
            yield_rate,
            bond["Maturity"],
            2
        )

        mod_i = modified_duration(
            mac_i,
            yield_rate,
            2
        )

        conv_i = bond_convexity(
            100,
            coupon,
            yield_rate,
            bond["Maturity"],
            2
        )

        market_value = (
            bond["Notional ($)"]
            * price_i / 100
        )

        dv01_i = (
            mod_i
            * market_value
            * 0.0001
        )


        new_price = bond_price(
            100,
            coupon,
            yield_rate + shock,
            bond["Maturity"],
            2
        )


        exact_pnl = (
            (new_price - price_i)
            / 100
            * bond["Notional ($)"]
        )


        approx_pnl = (
            (
                -mod_i * shock
                + 0.5 * conv_i * shock ** 2
            )
            * market_value
        )


        portfolio_results.append({

            "Bond": bond["Bond"],

            "Price": price_i,

            "Modified Duration": mod_i,

            "DV01 ($)": dv01_i,

            "Exact P&L ($)": exact_pnl,

            "Duration + Convexity P&L ($)": approx_pnl
        })


    results_df = pd.DataFrame(portfolio_results)


    st.dataframe(
        results_df.style.format({
            "Price": "{:.3f}",
            "Modified Duration": "{:.2f}",
            "DV01 ($)": "${:,.2f}",
            "Exact P&L ($)": "${:,.2f}",
            "Duration + Convexity P&L ($)": "${:,.2f}"
        }),
        use_container_width=True
    )


    total_dv01 = results_df["DV01 ($)"].sum()

    total_exact_pnl = results_df["Exact P&L ($)"].sum()

    total_approx_pnl = (
        results_df["Duration + Convexity P&L ($)"]
        .sum()
    )


    c1, c2, c3 = st.columns(3)

    c1.metric(
        "Portfolio DV01",
        f"${total_dv01:,.2f}"
    )

    c2.metric(
        "Exact Portfolio P&L",
        f"${total_exact_pnl:,.2f}"
    )

    c3.metric(
        "Duration + Convexity P&L",
        f"${total_approx_pnl:,.2f}"
    )


st.divider()

st.caption(
    """
    Educational research tool. Results are illustrative and do not
    constitute investment advice.
    """
)