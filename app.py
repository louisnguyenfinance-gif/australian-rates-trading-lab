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


tab1, tab2, tab3 = st.tabs([
    "Single Bond",
    "Portfolio Stress Test",
    "Rates Scenario Lab"
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
# ===================================================
# RATES SCENARIO LAB
# ===================================================

with tab3:

    st.header("Australian Rates Scenario Lab")

    st.write(
        """
        Test how non-parallel changes in the Australian Government
        yield curve affect an illustrative 2Y / 5Y / 10Y bond portfolio.
        """
    )

    # Load latest Australian yield curve
    yields_data = pd.read_csv(
        "data/processed/au_government_yields.csv",
        parse_dates=["Date"]
    )

    latest = yields_data.iloc[-1]

    current_curve = {
        "2Y": latest["2Y"],
        "3Y": latest["3Y"],
        "5Y": latest["5Y"],
        "10Y": latest["10Y"]
    }

    st.caption(
        f"Current curve observation: {latest['Date'].date()}"
    )

    # ---------------------------------------------------
    # Scenario selection
    # ---------------------------------------------------

    scenario_choice = st.selectbox(
        "Scenario",
        [
            "Historical Dovish Repricing — May 2025",
            "Historical Bear Flattening — July 2025",
            "Hypothetical Long-End Selloff",
            "Custom Scenario"
        ]
    )

    if scenario_choice == "Historical Dovish Repricing — May 2025":

        shocks = {
            "2Y": -16.4,
            "3Y": -16.9,
            "5Y": -15.5,
            "10Y": -12.4
        }

    elif scenario_choice == "Historical Bear Flattening — July 2025":

        shocks = {
            "2Y": 11.6,
            "3Y": 11.1,
            "5Y": 10.6,
            "10Y": 8.1
        }

    elif scenario_choice == "Hypothetical Long-End Selloff":

        shocks = {
            "2Y": 5.0,
            "3Y": 8.0,
            "5Y": 15.0,
            "10Y": 30.0
        }

    else:

        s1, s2, s3, s4 = st.columns(4)

        with s1:
            shock_2y = st.number_input(
                "2Y Shock (bp)",
                value=0.0
            )

        with s2:
            shock_3y = st.number_input(
                "3Y Shock (bp)",
                value=0.0
            )

        with s3:
            shock_5y = st.number_input(
                "5Y Shock (bp)",
                value=0.0
            )

        with s4:
            shock_10y = st.number_input(
                "10Y Shock (bp)",
                value=0.0
            )

        shocks = {
            "2Y": shock_2y,
            "3Y": shock_3y,
            "5Y": shock_5y,
            "10Y": shock_10y
        }


    # ---------------------------------------------------
    # Shocked curve
    # ---------------------------------------------------

    shocked_curve = {
        tenor: current_curve[tenor] + shocks[tenor] / 100
        for tenor in current_curve
    }


    current_2s10s = (
        current_curve["10Y"]
        - current_curve["2Y"]
    ) * 100

    shocked_2s10s = (
        shocked_curve["10Y"]
        - shocked_curve["2Y"]
    ) * 100

    curve_change = (
        shocked_2s10s - current_2s10s
    )

    average_shock = np.mean(
        list(shocks.values())
    )


    if average_shock < 0:
        direction = "Bull"
    elif average_shock > 0:
        direction = "Bear"
    else:
        direction = "Neutral"


    if curve_change > 0:
        shape = "Steepening"
    elif curve_change < 0:
        shape = "Flattening"
    else:
        shape = "Unchanged"


    classification = f"{direction} {shape}"


    # ---------------------------------------------------
    # Display curve metrics
    # ---------------------------------------------------

       # ---------------------------------------------------
    # Display curve metrics
    # ---------------------------------------------------

    m1, m2, m3 = st.columns([1.5, 1, 1])

    with m1:
        st.caption("Curve Classification")
        st.subheader(classification)

    with m2:
        st.metric(
            "Current 2s10s",
            f"{current_2s10s:.1f} bp"
        )

    with m3:
        st.metric(
            "2s10s Change",
            f"{curve_change:+.1f} bp"
        )


    # ---------------------------------------------------
    # Yield curve chart
    # ---------------------------------------------------

    maturities = [2, 3, 5, 10]
    tenors = ["2Y", "3Y", "5Y", "10Y"]

    fig, ax = plt.subplots(figsize=(10, 5))

    ax.plot(
        maturities,
        [current_curve[t] for t in tenors],
        marker="o",
        label="Current"
    )

    ax.plot(
        maturities,
        [shocked_curve[t] for t in tenors],
        marker="o",
        label="Scenario"
    )

    ax.set_title(
        "Australian Government Yield Curve"
    )

    ax.set_xlabel("Maturity (Years)")
    ax.set_ylabel("Yield (%)")
    ax.set_xticks(maturities)

    ax.legend()
    ax.grid(alpha=0.3)

    st.pyplot(fig)


    # ---------------------------------------------------
    # Portfolio scenario P&L
    # ---------------------------------------------------

    scenario_portfolio = pd.DataFrame({
        "Bond": [
            "2Y Bond",
            "5Y Bond",
            "10Y Bond"
        ],

        "Coupon": [
            0.040,
            0.045,
            0.050
        ],

        "YTM": [
            current_curve["2Y"] / 100,
            current_curve["5Y"] / 100,
            current_curve["10Y"] / 100
        ],

        "Years": [
            2,
            5,
            10
        ],

        "Notional": [
            2_000_000,
            3_000_000,
            1_500_000
        ],

        "Tenor": [
            "2Y",
            "5Y",
            "10Y"
        ]
    })


    pnl_results = []

    for _, bond in scenario_portfolio.iterrows():

        old_price = bond_price(
            100,
            bond["Coupon"],
            bond["YTM"],
            bond["Years"],
            2
        )

        shock_bp = shocks[bond["Tenor"]]

        new_yield = (
            bond["YTM"]
            + shock_bp / 10000
        )

        new_price = bond_price(
            100,
            bond["Coupon"],
            new_yield,
            bond["Years"],
            2
        )

        pnl = (
            (new_price - old_price)
            / 100
            * bond["Notional"]
        )

        pnl_results.append({
            "Bond": bond["Bond"],
            "Yield Shock (bp)": shock_bp,
            "P&L ($)": pnl
        })


    scenario_results = pd.DataFrame(
        pnl_results
    )


    st.subheader("Portfolio Impact")

    st.dataframe(
        scenario_results.style.format({
            "Yield Shock (bp)": "{:+.1f}",
            "P&L ($)": "${:,.2f}"
        }),
        use_container_width=True
    )


    total_scenario_pnl = (
        scenario_results["P&L ($)"].sum()
    )

    st.metric(
        "Total Portfolio P&L",
        f"${total_scenario_pnl:,.2f}"
    )


    fig2, ax2 = plt.subplots(figsize=(9, 5))

    ax2.bar(
        scenario_results["Bond"],
        scenario_results["P&L ($)"]
    )

    ax2.axhline(0, linewidth=1)

    ax2.set_title(
        f"Portfolio P&L — {scenario_choice}"
    )

    ax2.set_ylabel("P&L ($)")
    ax2.grid(axis="y", alpha=0.3)

    st.pyplot(fig2)


    st.caption(
        """
        Historical scenarios use observed one-day yield changes from
        the RBA event study. Portfolio positions and hypothetical
        scenarios are illustrative and are not forecasts.
        """
    )

st.divider()

st.caption(
    """
    Educational research tool. Results are illustrative and do not
    constitute investment advice.
    """
)