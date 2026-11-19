"""
Oil & Gas Explorer — FastMCP Server
============================================
A demonstration MCP server using synthetic oil and gas exploration data
representing major North American unconventional plays.

Deployment: Posit Connect (ASGI / FastAPI-compatible)
Transport:  Streamable HTTP  →  /mcp
"""

import math
import random
from datetime import date, timedelta

from fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Synthetic data generation
# Fixed seed → reproducible results across restarts
# ---------------------------------------------------------------------------

random.seed(4782)

# ---------------------------------------------------------------------------
# Formation reference data
# ---------------------------------------------------------------------------

FORMATION_CONFIGS = {
    "Montney": {
        "field": "Montney West",
        "region": "NE British Columbia, Canada",
        "play_type": "Unconventional Gas/Condensate",
        "ip30_oil_range": (60, 160),       # bbl/d condensate
        "ip30_gas_range": (3000, 6000),    # Mcf/d
        "b_factor": 1.2,
        "di_monthly": 0.07,
        "lateral_length_range": (8500, 13000),
        "tvd_range": (7200, 9500),
        "frac_stages_range": (32, 50),
        "proppant_per_ft_range": (1500, 2500),   # lbs/ft lateral
        "fluid_per_stage_range": (35000, 60000),  # bbl
        "capex_range_mm": (9.0, 14.0),
        "opex_per_boe": (6.0, 9.0),
        "lat_center": 56.20,
        "lon_center": -121.55,
        "lat_spread": 0.8,
        "lon_spread": 1.5,
        "royalty_rate": 0.17,
        "oil_price": 68.0,    # USD/bbl  (condensate ~WTI discount)
        "gas_price": 2.20,    # USD/Mcf (AECO + LNG export blended)
    },
    "Duvernay": {
        "field": "Duvernay Central",
        "region": "Central Alberta, Canada",
        "play_type": "Unconventional Oil / Liquids-Rich Gas",
        "ip30_oil_range": (350, 850),
        "ip30_gas_range": (800, 2200),
        "b_factor": 1.3,
        "di_monthly": 0.065,
        "lateral_length_range": (7000, 11000),
        "tvd_range": (10000, 14500),
        "frac_stages_range": (25, 42),
        "proppant_per_ft_range": (1800, 3000),
        "fluid_per_stage_range": (45000, 75000),
        "capex_range_mm": (12.0, 18.0),
        "opex_per_boe": (7.5, 11.0),
        "lat_center": 53.45,
        "lon_center": -115.80,
        "lat_spread": 0.6,
        "lon_spread": 1.2,
        "royalty_rate": 0.18,
        "oil_price": 65.0,
        "gas_price": 2.00,    # USD/Mcf (AECO + export premium)
    },
    "Wolfcamp A": {
        "field": "Permian Delaware Basin",
        "region": "West Texas, USA",
        "play_type": "Unconventional Oil",
        "ip30_oil_range": (700, 1600),
        "ip30_gas_range": (1500, 3500),
        "b_factor": 1.4,
        "di_monthly": 0.085,
        "lateral_length_range": (9000, 15000),
        "tvd_range": (8500, 11000),
        "frac_stages_range": (38, 60),
        "proppant_per_ft_range": (2200, 3500),
        "fluid_per_stage_range": (50000, 85000),
        "capex_range_mm": (8.5, 13.0),
        "opex_per_boe": (5.0, 8.0),
        "lat_center": 31.85,
        "lon_center": -103.40,
        "lat_spread": 0.5,
        "lon_spread": 0.8,
        "royalty_rate": 0.22,
        "oil_price": 72.0,
        "gas_price": 2.55,
    },
    "STACK/Meramec": {
        "field": "Anadarko Basin",
        "region": "Central Oklahoma, USA",
        "play_type": "Unconventional Oil / Wet Gas",
        "ip30_oil_range": (280, 620),
        "ip30_gas_range": (700, 1800),
        "b_factor": 1.2,
        "di_monthly": 0.06,
        "lateral_length_range": (7500, 12000),
        "tvd_range": (9000, 12000),
        "frac_stages_range": (28, 45),
        "proppant_per_ft_range": (1600, 2800),
        "fluid_per_stage_range": (40000, 65000),
        "capex_range_mm": (7.5, 11.5),
        "opex_per_boe": (6.0, 9.5),
        "lat_center": 35.60,
        "lon_center": -98.20,
        "lat_spread": 0.5,
        "lon_spread": 0.9,
        "royalty_rate": 0.21,
        "oil_price": 71.0,
        "gas_price": 2.50,
    },
}

# ---------------------------------------------------------------------------
# Well roster
# ---------------------------------------------------------------------------

_WELL_ROSTER = [
    # (formation, suffix, status, months_producing, months_since_spud)
    # Montney — 7 wells
    ("Montney",     "1-23-056-21W6",  "Active",    30, 36),
    ("Montney",     "2-23-056-21W6",  "Active",    28, 34),
    ("Montney",     "3-23-056-21W6",  "Active",    24, 30),
    ("Montney",     "4-15-057-22W6",  "Active",    18, 24),
    ("Montney",     "5-15-057-22W6",  "Active",    10, 16),
    ("Montney",     "6-08-058-22W6",  "DUC",        0,  8),
    ("Montney",     "7-08-058-22W6",  "Planned",    0,  0),
    # Duvernay — 6 wells
    ("Duvernay",    "100-02-31-052-10W5",  "Active",  32, 38),
    ("Duvernay",    "100-14-31-052-10W5",  "Active",  26, 32),
    ("Duvernay",    "100-22-30-052-10W5",  "Active",  20, 26),
    ("Duvernay",    "100-06-05-053-11W5",  "Active",  14, 20),
    ("Duvernay",    "100-18-05-053-11W5",  "Inactive", 8, 36),
    ("Duvernay",    "100-30-04-053-11W5",  "Planned",  0,  0),
    # Wolfcamp A — 7 wells
    ("Wolfcamp A",  "State Mineral 24-01H",  "Active",  36, 42),
    ("Wolfcamp A",  "State Mineral 24-02H",  "Active",  34, 40),
    ("Wolfcamp A",  "State Mineral 24-03H",  "Active",  30, 36),
    ("Wolfcamp A",  "Reeves County 12-01H",  "Active",  22, 28),
    ("Wolfcamp A",  "Reeves County 12-02H",  "Active",  16, 22),
    ("Wolfcamp A",  "Reeves County 12-03H",  "Active",   8, 14),
    ("Wolfcamp A",  "Loving County 07-01H",  "Planned",  0,  0),
    # STACK/Meramec — 5 wells
    ("STACK/Meramec", "Blaine 17-01H",   "Active",  28, 34),
    ("STACK/Meramec", "Blaine 17-02H",   "Active",  22, 28),
    ("STACK/Meramec", "Canadian 09-01H", "Active",  16, 22),
    ("STACK/Meramec", "Canadian 09-02H", "DUC",      0, 10),
    ("STACK/Meramec", "Dewey 03-01H",    "Planned",  0,  0),
]

# Formation → 3-letter code for well IDs
_FORM_CODE = {
    "Montney": "MNT",
    "Duvernay": "DVN",
    "Wolfcamp A": "WCA",
    "STACK/Meramec": "STK",
}


def _rand_between(lo: float, hi: float) -> float:
    return lo + random.random() * (hi - lo)


def _hyperbolic_rate(q_i: float, b: float, di: float, t_months: int) -> float:
    """Hyperbolic decline: q(t) = q_i / (1 + b * Di * t)^(1/b)"""
    if t_months <= 0:
        return q_i
    return q_i / math.pow(1.0 + b * di * t_months, 1.0 / b)


def _make_wells() -> list[dict]:
    wells = []
    counters: dict[str, int] = {}
    today = date(2026, 9, 1)

    for formation, suffix, status, months_producing, months_since_spud in _WELL_ROSTER:
        cfg = FORMATION_CONFIGS[formation]
        code = _FORM_CODE[formation]
        counters[code] = counters.get(code, 0) + 1
        well_id = f"OVV-{code}-{counters[code]:03d}"

        # Dates
        spud_date = today - timedelta(days=months_since_spud * 30)
        if months_since_spud > 6 and months_producing > 0:
            first_prod = spud_date + timedelta(days=random.randint(120, 210))
        else:
            first_prod = None

        # Geometry
        lat_len = int(_rand_between(*cfg["lateral_length_range"]))
        lat_len = round(lat_len / 50) * 50   # round to nearest 50 ft
        tvd = int(_rand_between(*cfg["tvd_range"]))
        tvd = round(tvd / 100) * 100

        # Location
        lat = cfg["lat_center"] + random.gauss(0, cfg["lat_spread"] / 2)
        lon = cfg["lon_center"] + random.gauss(0, cfg["lon_spread"] / 2)

        # Initial rates (IP30)
        ip30_oil = _rand_between(*cfg["ip30_oil_range"])
        ip30_gas = _rand_between(*cfg["ip30_gas_range"])
        ip30_water = ip30_oil * _rand_between(0.3, 0.8)

        # Completions
        stages = random.randint(*cfg["frac_stages_range"])
        proppant_per_ft = _rand_between(*cfg["proppant_per_ft_range"])
        proppant_total = int(lat_len * proppant_per_ft)
        fluid_per_stage = _rand_between(*cfg["fluid_per_stage_range"])
        fluid_total = int(stages * fluid_per_stage)
        cluster_spacing = round(lat_len / (stages * random.randint(4, 6)), 0)

        # Economics
        capex = round(_rand_between(*cfg["capex_range_mm"]), 2)

        wells.append({
            "well_id": well_id,
            "name": suffix,
            "field": cfg["field"],
            "formation": formation,
            "region": cfg["region"],
            "play_type": cfg["play_type"],
            "status": status,
            "operator": "Ovintiv",
            "spud_date": spud_date.isoformat() if months_since_spud > 0 else None,
            "first_production_date": first_prod.isoformat() if first_prod else None,
            "months_producing": months_producing,
            "lateral_length_ft": lat_len,
            "true_vertical_depth_ft": tvd,
            "latitude": round(lat, 4),
            "longitude": round(lon, 4),
            # Completion params
            "frac_stages": stages,
            "proppant_lbs": proppant_total,
            "fluid_bbls": fluid_total,
            "cluster_spacing_ft": int(cluster_spacing),
            "completion_date": (first_prod - timedelta(days=30)).isoformat()
            if first_prod else None,
            # Production params (used by production history tool)
            "ip30_oil_bopd": round(ip30_oil, 1),
            "ip30_gas_mcfd": round(ip30_gas, 1),
            "ip30_water_bwpd": round(ip30_water, 1),
            "b_factor": cfg["b_factor"],
            "di_monthly": cfg["di_monthly"],
            # Economics
            "capex_mm_usd": capex,
            "opex_per_boe_usd": round(_rand_between(*cfg["opex_per_boe"]), 2),
            "royalty_rate": cfg["royalty_rate"],
            "oil_price_assumption_usd": cfg["oil_price"],
            "gas_price_assumption_usd": cfg["gas_price"],
        })

    return wells


WELLS: list[dict] = _make_wells()
WELLS_BY_ID: dict[str, dict] = {w["well_id"]: w for w in WELLS}
WELLS_BY_NAME: dict[str, dict] = {w["name"].lower(): w for w in WELLS}

# ---------------------------------------------------------------------------
# Helper: production history
# ---------------------------------------------------------------------------

def _production_history(well: dict, max_months: int = 36) -> list[dict]:
    """Generate monthly production records using hyperbolic decline."""
    n = min(well["months_producing"], max_months)
    if n <= 0:
        return []

    qi_oil = well["ip30_oil_bopd"]
    qi_gas = well["ip30_gas_mcfd"]
    qi_water = well["ip30_water_bwpd"]
    b = well["b_factor"]
    di = well["di_monthly"]
    first_prod = date.fromisoformat(well["first_production_date"])

    records = []
    for t in range(n):
        prod_date = date(
            first_prod.year + (first_prod.month + t - 1) // 12,
            (first_prod.month + t - 1) % 12 + 1,
            1,
        )
        oil = _hyperbolic_rate(qi_oil, b, di, t)
        gas = _hyperbolic_rate(qi_gas, b, di, t)
        # Water cut increases with a logistic curve
        water_frac = 1.0 / (1.0 + math.exp(-0.06 * (t - 20)))
        water = qi_water * (0.4 + 1.4 * water_frac)

        # Monthly volumes (rate × 30.44 days/month)
        records.append({
            "month": prod_date.isoformat(),
            "oil_bopd_avg": round(oil, 1),
            "gas_mcfd_avg": round(gas, 1),
            "water_bwpd_avg": round(water, 1),
            "oil_bbls_month": int(oil * 30.44),
            "gas_mcf_month": int(gas * 30.44),
            "water_bbls_month": int(water * 30.44),
            "boe_per_day": round(oil + gas / 6.0, 1),
        })
    return records


# ---------------------------------------------------------------------------
# Helper: economics
# ---------------------------------------------------------------------------

def _calculate_economics(well: dict) -> dict:
    """NPV10 / IRR estimate using simplified DCF over 20-year production life."""
    oil_price = well["oil_price_assumption_usd"]
    gas_price = well["gas_price_assumption_usd"]
    royalty = well["royalty_rate"]
    opex = well["opex_per_boe_usd"]
    capex_mm = well["capex_mm_usd"]
    capex = capex_mm * 1_000_000

    b = well["b_factor"]
    di = well["di_monthly"]
    qi_oil = well["ip30_oil_bopd"]
    qi_gas = well["ip30_gas_mcfd"]

    discount_rate_annual = 0.10  # 10% → NPV10
    monthly_rate = (1 + discount_rate_annual) ** (1 / 12) - 1

    cum_oil = 0.0
    cum_gas = 0.0
    npv = -capex
    cumulative_cf = -capex
    payout_month = None

    for t in range(240):  # 20-year horizon
        oil_rate = _hyperbolic_rate(qi_oil, b, di, t)
        gas_rate = _hyperbolic_rate(qi_gas, b, di, t)

        oil_vol = oil_rate * 30.44
        gas_vol = gas_rate * 30.44

        cum_oil += oil_vol
        cum_gas += gas_vol

        boe = oil_vol + gas_vol / 6.0
        revenue = oil_vol * oil_price * (1 - royalty) + gas_vol * gas_price * (1 - royalty)
        expenses = boe * opex
        net_cf = revenue - expenses

        discount_factor = 1.0 / ((1 + monthly_rate) ** (t + 1))
        npv += net_cf * discount_factor
        cumulative_cf += net_cf

        if payout_month is None and cumulative_cf >= 0:
            payout_month = t + 1

    # Approximate IRR: search for annual rate where NPV crosses zero
    irr = None
    irr_exceeded_ceiling = False
    for test_r_annual in [x / 100 for x in range(0, 502, 2)]:
        test_rate = (1 + test_r_annual) ** (1 / 12) - 1
        test_npv = -capex
        for t in range(240):
            oil_vol = _hyperbolic_rate(qi_oil, b, di, t) * 30.44
            gas_vol = _hyperbolic_rate(qi_gas, b, di, t) * 30.44
            boe = oil_vol + gas_vol / 6.0
            revenue = oil_vol * oil_price * (1 - royalty) + gas_vol * gas_price * (1 - royalty)
            expenses = boe * opex
            net_cf = revenue - expenses
            df = 1.0 / ((1 + test_rate) ** (t + 1))
            test_npv += net_cf * df
        if test_npv <= 0:
            irr = test_r_annual
            break
    else:
        # NPV positive even at 500% — IRR exceeds ceiling
        irr_exceeded_ceiling = True

    return {
        "well_id": well["well_id"],
        "well_name": well["name"],
        "capex_mm_usd": capex_mm,
        "npv10_mm_usd": round(npv / 1_000_000, 2),
        "irr_pct": ">500%" if irr_exceeded_ceiling else irr,
        "payout_months": payout_month,
        "estimated_eur_oil_mbbl": round(cum_oil / 1000, 0),
        "estimated_eur_gas_mmcf": round(cum_gas / 1000, 0),
        "oil_price_assumption_usd": oil_price,
        "gas_price_assumption_usd": gas_price,
        "royalty_rate": royalty,
        "opex_per_boe_usd": opex,
        "discount_rate_pct": 10.0,
    }


# ---------------------------------------------------------------------------
# FastMCP server
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "Ovintiv O&G Explorer",
    instructions=(
        "You have access to synthetic oil and gas exploration data representing "
        "Ovintiv's major North American unconventional plays: Montney (BC Canada), "
        "Duvernay (AB Canada), Wolfcamp A (Permian, TX), and STACK/Meramec (OK). "
        "Use the available tools to explore well inventory, production histories, "
        "completion designs, and economics. All data is synthetic for demonstration purposes."
    ),
)


# ---------------------------------------------------------------------------
# Tool 1 — list_wells
# ---------------------------------------------------------------------------

@mcp.tool()
def list_wells(
    formation: str | None = None,
    status: str | None = None,
    field: str | None = None,
) -> list[dict]:
    """
    Return a summary list of all wells, optionally filtered.

    Args:
        formation: Filter by formation name. Options: 'Montney', 'Duvernay',
                   'Wolfcamp A', 'STACK/Meramec'. Case-insensitive.
        status:    Filter by well status. Options: 'Active', 'Inactive',
                   'DUC' (drilled-uncompleted), 'Planned'. Case-insensitive.
        field:     Filter by field name. Partial match, case-insensitive.

    Returns:
        List of wells with id, name, field, formation, status, lateral_length_ft,
        spud_date, first_production_date, and current BOE/d rate.
    """
    results = []
    for w in WELLS:
        if formation and w["formation"].lower() != formation.lower():
            continue
        if status and w["status"].lower() != status.lower():
            continue
        if field and field.lower() not in w["field"].lower():
            continue

        # Current rate = last month of production history
        hist = _production_history(w, max_months=1 + w["months_producing"])
        current_boe = hist[-1]["boe_per_day"] if hist else 0.0

        results.append({
            "well_id": w["well_id"],
            "name": w["name"],
            "field": w["field"],
            "formation": w["formation"],
            "region": w["region"],
            "status": w["status"],
            "spud_date": w["spud_date"],
            "first_production_date": w["first_production_date"],
            "months_producing": w["months_producing"],
            "lateral_length_ft": w["lateral_length_ft"],
            "current_boe_per_day": round(current_boe, 1),
        })
    return results


# ---------------------------------------------------------------------------
# Tool 2 — get_well_details
# ---------------------------------------------------------------------------

@mcp.tool()
def get_well_details(well_id: str) -> dict:
    """
    Return full technical details for a single well.

    Args:
        well_id: The well identifier (e.g. 'OVV-MNT-001'). Use list_wells()
                 to find valid IDs.

    Returns:
        Complete well record including geometry, completion design, location,
        production parameters, and economic assumptions.
    """
    well = WELLS_BY_ID.get(well_id.upper())
    if well is None:
        # Try partial / name match
        for w in WELLS:
            if well_id.lower() in w["name"].lower() or well_id.lower() in w["well_id"].lower():
                well = w
                break
    if well is None:
        return {"error": f"Well '{well_id}' not found. Use list_wells() to see valid IDs."}

    # Exclude internal production-model fields for cleaner output
    public_fields = {
        k: v for k, v in well.items()
        if k not in ("b_factor", "di_monthly")
    }
    return public_fields


# ---------------------------------------------------------------------------
# Tool 3 — get_production_history
# ---------------------------------------------------------------------------

@mcp.tool()
def get_production_history(well_id: str, max_months: int = 36) -> dict:
    """
    Return monthly production history for a well.

    Args:
        well_id:    The well identifier (e.g. 'OVV-WCA-001').
        max_months: Maximum number of months to return (default 36, max 60).

    Returns:
        Dictionary with well metadata and a list of monthly production records
        containing oil (bbl/d), gas (Mcf/d), water (bbl/d), and BOE/d averages,
        as well as monthly cumulative volumes.
    """
    well = WELLS_BY_ID.get(well_id.upper())
    if well is None:
        return {"error": f"Well '{well_id}' not found. Use list_wells() to see valid IDs."}

    if well["status"] in ("DUC", "Planned"):
        return {
            "well_id": well_id,
            "name": well["name"],
            "status": well["status"],
            "message": "No production history — well has not yet been completed and brought on production.",
        }

    max_months = max(1, min(max_months, 60))
    history = _production_history(well, max_months=max_months)

    # Cumulative totals
    cum_oil = sum(r["oil_bbls_month"] for r in history)
    cum_gas = sum(r["gas_mcf_month"] for r in history)
    cum_water = sum(r["water_bbls_month"] for r in history)

    return {
        "well_id": well["well_id"],
        "name": well["name"],
        "field": well["field"],
        "formation": well["formation"],
        "first_production_date": well["first_production_date"],
        "months_of_history": len(history),
        "cumulative_oil_bbls": cum_oil,
        "cumulative_gas_mcf": cum_gas,
        "cumulative_water_bbls": cum_water,
        "cumulative_boe": cum_oil + cum_gas // 6,
        "monthly_history": history,
    }


# ---------------------------------------------------------------------------
# Tool 4 — get_field_summary
# ---------------------------------------------------------------------------

@mcp.tool()
def get_field_summary() -> list[dict]:
    """
    Return aggregate production and well-count statistics for each field.

    Returns:
        List of field summaries including total wells by status, combined
        current BOE/d, cumulative production, and average well economics.
    """
    from collections import defaultdict

    fields: dict[str, dict] = defaultdict(lambda: {
        "total_wells": 0,
        "active_wells": 0,
        "duc_wells": 0,
        "planned_wells": 0,
        "inactive_wells": 0,
        "total_current_boe_per_day": 0.0,
        "total_cum_oil_mbbls": 0.0,
        "total_cum_gas_mmcf": 0.0,
        "avg_lateral_length_ft": [],
        "avg_capex_mm_usd": [],
    })

    for w in WELLS:
        f = fields[w["field"]]
        f["formation"] = w["formation"]
        f["region"] = w["region"]
        f["play_type"] = w["play_type"]
        f["total_wells"] += 1

        status_key = f"{w['status'].lower()}_wells"
        f[status_key] = f.get(status_key, 0) + 1

        hist = _production_history(w)
        if hist:
            f["total_current_boe_per_day"] += hist[-1]["boe_per_day"]
            f["total_cum_oil_mbbls"] += sum(r["oil_bbls_month"] for r in hist) / 1000
            f["total_cum_gas_mmcf"] += sum(r["gas_mcf_month"] for r in hist) / 1000

        f["avg_lateral_length_ft"].append(w["lateral_length_ft"])
        f["avg_capex_mm_usd"].append(w["capex_mm_usd"])

    summaries = []
    for field_name, data in fields.items():
        lat_lens = data.pop("avg_lateral_length_ft")
        capexes = data.pop("avg_capex_mm_usd")
        summaries.append({
            "field": field_name,
            **data,
            "total_current_boe_per_day": round(data["total_current_boe_per_day"], 0),
            "total_cum_oil_mbbls": round(data["total_cum_oil_mbbls"], 1),
            "total_cum_gas_mmcf": round(data["total_cum_gas_mmcf"], 1),
            "avg_lateral_length_ft": round(sum(lat_lens) / len(lat_lens)),
            "avg_capex_mm_usd": round(sum(capexes) / len(capexes), 2),
        })

    return sorted(summaries, key=lambda x: x["total_current_boe_per_day"], reverse=True)


# ---------------------------------------------------------------------------
# Tool 5 — search_wells
# ---------------------------------------------------------------------------

@mcp.tool()
def search_wells(
    formation: str | None = None,
    status: str | None = None,
    min_lateral_ft: int | None = None,
    max_lateral_ft: int | None = None,
    min_current_boe: float | None = None,
    max_current_boe: float | None = None,
) -> list[dict]:
    """
    Search and filter wells by multiple criteria.

    Args:
        formation:      Formation name (partial match, case-insensitive).
        status:         Well status: 'Active', 'Inactive', 'DUC', 'Planned'.
        min_lateral_ft: Minimum lateral length in feet.
        max_lateral_ft: Maximum lateral length in feet.
        min_current_boe: Minimum current production rate (BOE/d).
        max_current_boe: Maximum current production rate (BOE/d).

    Returns:
        Filtered list of wells with key attributes and current production rate.
    """
    results = []
    for w in WELLS:
        if formation and formation.lower() not in w["formation"].lower():
            continue
        if status and w["status"].lower() != status.lower():
            continue
        if min_lateral_ft and w["lateral_length_ft"] < min_lateral_ft:
            continue
        if max_lateral_ft and w["lateral_length_ft"] > max_lateral_ft:
            continue

        hist = _production_history(w)
        current_boe = hist[-1]["boe_per_day"] if hist else 0.0

        if min_current_boe is not None and current_boe < min_current_boe:
            continue
        if max_current_boe is not None and current_boe > max_current_boe:
            continue

        results.append({
            "well_id": w["well_id"],
            "name": w["name"],
            "field": w["field"],
            "formation": w["formation"],
            "status": w["status"],
            "lateral_length_ft": w["lateral_length_ft"],
            "true_vertical_depth_ft": w["true_vertical_depth_ft"],
            "months_producing": w["months_producing"],
            "current_boe_per_day": round(current_boe, 1),
            "capex_mm_usd": w["capex_mm_usd"],
        })

    return sorted(results, key=lambda x: x["current_boe_per_day"], reverse=True)


# ---------------------------------------------------------------------------
# Tool 6 — get_completion_data
# ---------------------------------------------------------------------------

@mcp.tool()
def get_completion_data(well_id: str) -> dict:
    """
    Return hydraulic fracture completion design parameters for a well.

    Args:
        well_id: The well identifier (e.g. 'OVV-DVN-001').

    Returns:
        Completion record with frac stages, proppant volume, fluid volume,
        cluster spacing, completion date, and efficiency metrics.
    """
    well = WELLS_BY_ID.get(well_id.upper())
    if well is None:
        return {"error": f"Well '{well_id}' not found."}

    if well["completion_date"] is None:
        return {
            "well_id": well_id,
            "name": well["name"],
            "status": well["status"],
            "message": "Completion data not yet available — well has not been fractured.",
        }

    stages = well["frac_stages"]
    lat_len = well["lateral_length_ft"]
    proppant = well["proppant_lbs"]
    fluid = well["fluid_bbls"]

    return {
        "well_id": well["well_id"],
        "name": well["name"],
        "field": well["field"],
        "formation": well["formation"],
        "completion_date": well["completion_date"],
        "lateral_length_ft": lat_len,
        "frac_stages": stages,
        "stage_spacing_ft": round(lat_len / stages),
        "cluster_spacing_ft": well["cluster_spacing_ft"],
        "total_proppant_lbs": proppant,
        "proppant_per_ft_lbs": round(proppant / lat_len, 0),
        "proppant_per_stage_lbs": round(proppant / stages, 0),
        "total_fluid_bbls": fluid,
        "fluid_per_stage_bbls": round(fluid / stages, 0),
        "fluid_per_ft_bbls": round(fluid / lat_len, 2),
        "proppant_concentration_lbs_per_gal": round(
            (proppant / (fluid * 42)) , 2
        ),
    }


# ---------------------------------------------------------------------------
# Tool 7 — get_type_curve
# ---------------------------------------------------------------------------

@mcp.tool()
def get_type_curve(formation: str) -> dict:
    """
    Return the average type curve (P50 decline parameters) for a formation,
    based on actual well performance in the synthetic dataset.

    Args:
        formation: Formation name. Options: 'Montney', 'Duvernay',
                   'Wolfcamp A', 'STACK/Meramec'. Case-insensitive.

    Returns:
        Type curve parameters including P10/P50/P90 IP30 rates, decline
        parameters, EUR estimates, and average completion design.
    """
    match = None
    for key in FORMATION_CONFIGS:
        if key.lower() == formation.lower():
            match = key
            break

    if match is None:
        return {
            "error": f"Formation '{formation}' not recognised.",
            "valid_formations": list(FORMATION_CONFIGS.keys()),
        }

    cfg = FORMATION_CONFIGS[match]
    form_wells = [w for w in WELLS if w["formation"] == match and w["months_producing"] >= 6]

    if not form_wells:
        return {"error": f"No wells with sufficient production history in '{match}'."}

    ip30_oils = sorted(w["ip30_oil_bopd"] for w in form_wells)
    ip30_gases = sorted(w["ip30_gas_mcfd"] for w in form_wells)
    capexes = [w["capex_mm_usd"] for w in form_wells]
    laterals = [w["lateral_length_ft"] for w in form_wells]

    def percentile(lst, p):
        idx = max(0, int(len(lst) * p / 100) - 1)
        return round(lst[idx], 1)

    # EUR estimates at P50 (20-year hyperbolic decline)
    p50_oil = percentile(ip30_oils, 50)
    p50_gas = percentile(ip30_gases, 50)
    b = cfg["b_factor"]
    di = cfg["di_monthly"]
    eur_oil = sum(_hyperbolic_rate(p50_oil, b, di, t) * 30.44 for t in range(240))
    eur_gas = sum(_hyperbolic_rate(p50_gas, b, di, t) * 30.44 for t in range(240))

    return {
        "formation": match,
        "field": cfg["field"],
        "region": cfg["region"],
        "play_type": cfg["play_type"],
        "well_count_in_dataset": len(form_wells),
        "decline_model": "Hyperbolic",
        "b_factor": b,
        "initial_decline_rate_monthly": di,
        "initial_decline_rate_annual_pct": round((1 - (1 - di) ** 12) * 100, 1),
        "ip30_oil_bopd": {
            "p10": percentile(ip30_oils, 10),
            "p50": percentile(ip30_oils, 50),
            "p90": percentile(ip30_oils, 90),
        },
        "ip30_gas_mcfd": {
            "p10": percentile(ip30_gases, 10),
            "p50": percentile(ip30_gases, 50),
            "p90": percentile(ip30_gases, 90),
        },
        "eur_p50_oil_mbbls": round(eur_oil / 1000, 0),
        "eur_p50_gas_mmcf": round(eur_gas / 1000, 0),
        "eur_p50_boe_mboe": round((eur_oil + eur_gas / 6) / 1000, 0),
        "avg_lateral_length_ft": round(sum(laterals) / len(laterals)),
        "avg_capex_mm_usd": round(sum(capexes) / len(capexes), 2),
        "oil_price_assumption_usd": cfg["oil_price"],
        "gas_price_assumption_usd": cfg["gas_price"],
    }


# ---------------------------------------------------------------------------
# Tool 8 — get_economics
# ---------------------------------------------------------------------------

@mcp.tool()
def get_economics(
    well_id: str | None = None,
    formation: str | None = None,
) -> dict | list[dict]:
    """
    Return economic metrics (NPV10, IRR, payout) for a single well or all
    wells in a formation.

    Provide exactly one of well_id or formation.

    Args:
        well_id:   Well identifier for single-well economics (e.g. 'OVV-WCA-003').
        formation: Formation name to return economics for all wells in that play.

    Returns:
        Single economic summary dict, or list of summaries sorted by NPV10.
    """
    if well_id and formation:
        return {"error": "Provide either well_id or formation, not both."}

    if well_id:
        well = WELLS_BY_ID.get(well_id.upper())
        if well is None:
            return {"error": f"Well '{well_id}' not found."}
        if well["months_producing"] == 0:
            return {
                "well_id": well_id,
                "message": "Economics not yet available — well has no production history.",
            }
        return _calculate_economics(well)

    if formation:
        form_wells = [
            w for w in WELLS
            if w["formation"].lower() == formation.lower() and w["months_producing"] > 0
        ]
        if not form_wells:
            return {"error": f"No producing wells found for formation '{formation}'."}
        econ_list = [_calculate_economics(w) for w in form_wells]
        return sorted(econ_list, key=lambda x: x["npv10_mm_usd"], reverse=True)

    return {"error": "Provide either well_id or formation."}


# ---------------------------------------------------------------------------
# Tool 9 — get_drilling_activity
# ---------------------------------------------------------------------------

@mcp.tool()
def get_drilling_activity(include_planned: bool = True) -> dict:
    """
    Return recent and upcoming drilling activity across all plays.

    Args:
        include_planned: If True (default), include wells with 'Planned' status.

    Returns:
        Dictionary with recently spudded wells, DUCs awaiting completion,
        and (optionally) planned future wells.
    """
    recently_spudded = []
    ducs = []
    planned = []

    today = date(2026, 9, 1)
    cutoff = today - timedelta(days=365)

    for w in WELLS:
        if w["spud_date"] is None:
            if w["status"] == "Planned":
                planned.append({
                    "well_id": w["well_id"],
                    "name": w["name"],
                    "field": w["field"],
                    "formation": w["formation"],
                    "status": w["status"],
                    "planned_lateral_length_ft": w["lateral_length_ft"],
                    "estimated_capex_mm_usd": w["capex_mm_usd"],
                })
            continue

        spud = date.fromisoformat(w["spud_date"])

        if w["status"] == "DUC":
            ducs.append({
                "well_id": w["well_id"],
                "name": w["name"],
                "field": w["field"],
                "formation": w["formation"],
                "spud_date": w["spud_date"],
                "days_since_spud": (today - spud).days,
                "lateral_length_ft": w["lateral_length_ft"],
                "estimated_capex_mm_usd": w["capex_mm_usd"],
            })
        elif spud >= cutoff:
            recently_spudded.append({
                "well_id": w["well_id"],
                "name": w["name"],
                "field": w["field"],
                "formation": w["formation"],
                "spud_date": w["spud_date"],
                "days_since_spud": (today - spud).days,
                "status": w["status"],
                "first_production_date": w["first_production_date"],
            })

    result = {
        "as_of_date": today.isoformat(),
        "recently_spudded_wells": sorted(recently_spudded, key=lambda x: x["spud_date"], reverse=True),
        "drilled_uncompleted_wells_ducs": ducs,
    }
    if include_planned:
        result["planned_wells"] = planned

    return result


# ---------------------------------------------------------------------------
# Tool 10 — compare_wells
# ---------------------------------------------------------------------------

@mcp.tool()
def compare_wells(well_id_a: str, well_id_b: str) -> dict:
    """
    Side-by-side comparison of two wells across production, completion,
    and economic dimensions.

    Args:
        well_id_a: First well ID (e.g. 'OVV-MNT-001').
        well_id_b: Second well ID (e.g. 'OVV-WCA-001').

    Returns:
        Comparison dictionary with both wells' key metrics side-by-side,
        plus a delta column (B minus A) for numeric fields.
    """
    well_a = WELLS_BY_ID.get(well_id_a.upper())
    well_b = WELLS_BY_ID.get(well_id_b.upper())

    errors = []
    if well_a is None:
        errors.append(f"Well '{well_id_a}' not found.")
    if well_b is None:
        errors.append(f"Well '{well_id_b}' not found.")
    if errors:
        return {"error": " ".join(errors)}

    def _latest_rate(w):
        h = _production_history(w)
        return h[-1] if h else {}

    rate_a = _latest_rate(well_a)
    rate_b = _latest_rate(well_b)
    econ_a = _calculate_economics(well_a) if well_a["months_producing"] > 0 else {}
    econ_b = _calculate_economics(well_b) if well_b["months_producing"] > 0 else {}

    def _delta(va, vb):
        if isinstance(va, (int, float)) and isinstance(vb, (int, float)):
            return round(vb - va, 2)
        return "N/A"

    metrics = [
        ("formation", well_a["formation"], well_b["formation"]),
        ("field", well_a["field"], well_b["field"]),
        ("status", well_a["status"], well_b["status"]),
        ("lateral_length_ft", well_a["lateral_length_ft"], well_b["lateral_length_ft"]),
        ("true_vertical_depth_ft", well_a["true_vertical_depth_ft"], well_b["true_vertical_depth_ft"]),
        ("months_producing", well_a["months_producing"], well_b["months_producing"]),
        ("ip30_oil_bopd", well_a["ip30_oil_bopd"], well_b["ip30_oil_bopd"]),
        ("ip30_gas_mcfd", well_a["ip30_gas_mcfd"], well_b["ip30_gas_mcfd"]),
        ("current_oil_bopd", rate_a.get("oil_bopd_avg"), rate_b.get("oil_bopd_avg")),
        ("current_gas_mcfd", rate_a.get("gas_mcfd_avg"), rate_b.get("gas_mcfd_avg")),
        ("current_boe_per_day", rate_a.get("boe_per_day"), rate_b.get("boe_per_day")),
        ("frac_stages", well_a["frac_stages"], well_b["frac_stages"]),
        ("proppant_per_ft_lbs", round(well_a["proppant_lbs"] / well_a["lateral_length_ft"]),
         round(well_b["proppant_lbs"] / well_b["lateral_length_ft"])),
        ("capex_mm_usd", well_a["capex_mm_usd"], well_b["capex_mm_usd"]),
        ("npv10_mm_usd", econ_a.get("npv10_mm_usd"), econ_b.get("npv10_mm_usd")),
        ("irr_pct", econ_a.get("irr_pct"), econ_b.get("irr_pct")),
        ("payout_months", econ_a.get("payout_months"), econ_b.get("payout_months")),
        ("eur_oil_mbbls", econ_a.get("estimated_eur_oil_mbbl"), econ_b.get("estimated_eur_oil_mbbl")),
        ("eur_gas_mmcf", econ_a.get("estimated_eur_gas_mmcf"), econ_b.get("estimated_eur_gas_mmcf")),
    ]

    comparison = {
        "well_a_id": well_id_a.upper(),
        "well_b_id": well_id_b.upper(),
        "metrics": [
            {
                "metric": name,
                well_id_a.upper(): val_a,
                well_id_b.upper(): val_b,
                "delta_b_minus_a": _delta(val_a, val_b),
            }
            for name, val_a, val_b in metrics
        ],
    }
    return comparison


# ---------------------------------------------------------------------------
# ASGI app — for Posit Connect deployment
# ---------------------------------------------------------------------------

app = mcp.http_app(path="/mcp")

# ---------------------------------------------------------------------------
# Local development entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import os

    import uvicorn

    path, port = "", 8000
    # When running in Posit Workbench, pass port to rserver-url to determine
    # the root path. See https://docs.posit.co/ide/server-pro/user/vs-code/guide/posit-workbench-extension.html#fastapi
    if os.environ.get("RS_SERVER_URL"):
        import subprocess

        path = subprocess.run(
            f"echo $(/usr/lib/rstudio-server/bin/rserver-url -l {port})",
            stdout=subprocess.PIPE,
            shell=True,
            check=False,
        ).stdout.decode().strip()

    uvicorn.run(app, host="0.0.0.0", root_path=path, port=port)
