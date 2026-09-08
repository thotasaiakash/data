"""
Generate synthetic mock data CSVs for the Virginia analytics tables, per
issue #301: countries, states, cities, users, volunteer_details,
user_skills, volunteer_locations, user_locations, help_categories,
organizations.

Usage:
    python generate_mock_data.py
    python generate_mock_data.py --users 400 --orgs 100 --seed 7
    python generate_mock_data.py --outdir ./out

All output is fully synthetic (via Faker) — no real names, emails, phone
numbers, addresses, or user IDs are used.
"""

from __future__ import annotations

import argparse
import csv
import os
import random

from faker import Faker

import utils

fake = Faker()


# ---------------------------------------------------------------------------
# CSV writer helper
# ---------------------------------------------------------------------------
def write_csv(path: str, fieldnames: list[str], rows: list[dict]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    print(f"  wrote {len(rows):>5} rows -> {path}")


# ---------------------------------------------------------------------------
# Table generators (each returns a list[dict] and any lookups needed later)
# ---------------------------------------------------------------------------
def gen_countries() -> list[dict]:
    rows = []
    for i, c in enumerate(utils.COUNTRIES, start=1):
        rows.append(
            {
                "country_id": i,
                "country_name": c["country_name"],
                "phone_code": c["phone_code"],
                "country_code": c["country_code"],
                "last_updated_at": utils.fmt_ts(utils.random_created_at()),
                "is_eu_member": c["is_eu_member"],
            }
        )
    return rows


def gen_states(us_country_id: int) -> list[dict]:
    rows = []
    for name, code, lat, lon in utils.US_STATES:
        rows.append(
            {
                "state_id": utils.make_state_id(code),
                "country_id": us_country_id,
                "state_name": name,
                "state_code": code,
                "last_updated_at": utils.fmt_ts(utils.random_created_at()),
                # kept internally for downstream geo derivation, stripped before CSV write
                "_lat": lat,
                "_lon": lon,
            }
        )
    return rows


def gen_cities(states: list[dict]) -> list[dict]:
    rows = []
    city_id = 1
    for state in states:
        state_name = state["state_name"]
        for city_name, lat, lon in utils.STATE_CITIES.get(state_name, []):
            rows.append(
                {
                    "city_id": city_id,
                    "state_id": state["state_id"],
                    "city_name": city_name,
                    "lattitude": lat,
                    "longitude": lon,
                    "last_updated_at": utils.fmt_ts(utils.random_created_at()),
                }
            )
            city_id += 1
    return rows


def gen_help_categories() -> list[dict]:
    rows = []
    for cat_id, cat_name, cat_desc in utils.HELP_CATEGORIES:
        rows.append(
            {
                "cat_id": cat_id,
                "cat_name": cat_name,
                "cat_desc": cat_desc,
                "last_updated_at": utils.fmt_ts(utils.random_created_at()),
            }
        )
    return rows


def gen_users(n: int, states: list[dict], us_country_id: int) -> list[dict]:
    rows = []
    for seq in range(1, n + 1):
        state = random.choice(states)
        cities = utils.STATE_CITIES.get(state["state_name"], [])
        city_name, city_lat, city_lon = random.choice(cities) if cities else (None, state["_lat"], state["_lon"])
        lat, lon = utils.jitter_point(city_lat, city_lon)

        created = utils.random_created_at()
        updated = utils.random_updated_after(created)
        dob = fake.date_of_birth(minimum_age=18, maximum_age=80)

        rows.append(
            {
                "user_id": utils.make_user_id(seq),
                "state_id": state["state_id"],
                "country_id": us_country_id,
                "user_status_id": random.choice([1, 1, 1, 2, 3]),  # weighted toward "Active"-like id=1
                "full_name": fake.name(),
                "first_name": fake.first_name(),
                "middle_name": fake.first_name() if random.random() < 0.2 else "",
                "last_name": fake.last_name(),
                "primary_email_address": fake.unique.email(),
                "primary_phone_number": fake.phone_number(),
                "addr_ln1": fake.street_address(),
                "addr_ln2": "",
                "addr_ln3": "",
                "city_name": city_name or "",
                "zip_code": fake.postcode(),
                "last_location": f"({lon},{lat})",  # Postgres point literal (x,y) = (lon,lat)
                "last_updated_at": utils.fmt_ts(updated),
                "time_zone": random.choice(utils.TIME_ZONES),
                "profile_picture_path": "",
                "gender": random.choice(utils.GENDERS),
                "language_1": "",
                "language_2": "",
                "language_3": "",
                "promotion_wizard_stage": random.randint(1, 5),
                "promotion_wizard_last_update_at": utils.fmt_ts(updated),
                "external_auth_provider": random.choice(["google", "facebook", "email", ""]),
                "dob": utils.fmt_date(fake_dt(dob)),
                "is_eu": False,
                # internal-only, used to derive volunteer_locations/user_locations
                "_lat": lat,
                "_lon": lon,
                "_created_at": created,
            }
        )
    return rows


def fake_dt(date_obj):
    """faker's date_of_birth returns a date; wrap to reuse fmt_date via datetime."""
    from datetime import datetime as _dt
    return _dt(date_obj.year, date_obj.month, date_obj.day)


def gen_volunteer_details(users: list[dict], fraction: float) -> list[dict]:
    rows = []
    volunteers = random.sample(users, k=int(len(users) * fraction))
    for u in volunteers:
        created = u["_created_at"]
        updated = utils.random_updated_after(created)
        rows.append(
            {
                "user_id": u["user_id"],
                "terms_and_conditions": True,
                "terms_accepted_at": utils.fmt_ts(created),
                "govt_id_path1": f"s3://mock-bucket/ids/{u['user_id']}_1.jpg",
                "govt_id_path2": f"s3://mock-bucket/ids/{u['user_id']}_2.jpg",
                "path1_updated_at": utils.fmt_ts(created),
                "path2_updated_at": utils.fmt_ts(created),
                "availability_days": '["Monday","Wednesday","Saturday"]',
                "availability_times": '{"start":"09:00","end":"17:00"}',
                "created_at": utils.fmt_ts(created),
                "last_updated_at": utils.fmt_ts(updated),
            }
        )
    return rows


def gen_user_skills(volunteer_user_ids: list[str], categories: list[dict]) -> list[dict]:
    rows = []
    cat_ids = [c["cat_id"] for c in categories]
    for user_id in volunteer_user_ids:
        num_skills = random.randint(1, 3)
        chosen = random.sample(cat_ids, k=min(num_skills, len(cat_ids)))
        for cat_id in chosen:
            created = utils.random_created_at()
            updated = utils.random_updated_after(created)
            rows.append(
                {
                    "user_id": user_id,
                    "cat_id": cat_id,
                    "skill_level": random.choice(utils.SKILL_LEVELS),
                    "created_at": utils.fmt_ts(created),
                    "last_updated_at": utils.fmt_ts(updated),
                }
            )
    return rows


def gen_volunteer_locations(users_by_id: dict, volunteer_user_ids: list[str]) -> list[dict]:
    rows = []
    for user_id in volunteer_user_ids:
        u = users_by_id[user_id]
        curr_lat, curr_lon = utils.jitter_point(u["_lat"], u["_lon"], max_offset_deg=0.01)
        prev_lat, prev_lon = utils.jitter_point(u["_lat"], u["_lon"], max_offset_deg=0.03)
        updated = utils.random_updated_after(u["_created_at"])
        rows.append(
            {
                "user_id": user_id,
                "prev_loc": utils.to_wkt_point(prev_lat, prev_lon),
                "curr_loc": utils.to_wkt_point(curr_lat, curr_lon),
                "last_updated_at": utils.fmt_ts(updated),
            }
        )
    return rows


def gen_user_locations(users: list[dict]) -> list[dict]:
    rows = []
    for u in users:
        curr_lat, curr_lon = utils.jitter_point(u["_lat"], u["_lon"], max_offset_deg=0.01)
        prev_lat, prev_lon = utils.jitter_point(u["_lat"], u["_lon"], max_offset_deg=0.03)
        updated = utils.random_updated_after(u["_created_at"])
        rows.append(
            {
                "user_id": u["user_id"],
                "prev_loc": utils.to_wkt_point(prev_lat, prev_lon),
                "curr_loc": utils.to_wkt_point(curr_lat, curr_lon),
                "last_updated_at": utils.fmt_ts(updated),
            }
        )
    return rows


def gen_organizations(n: int, states: list[dict]) -> list[dict]:
    rows = []
    for seq in range(1, n + 1):
        state = random.choice(states)
        created = utils.random_created_at()
        updated = utils.random_updated_after(created)
        rows.append(
            {
                "org_id": utils.make_org_id(seq),
                "org_name": fake.company() + " Foundation",
                "street": fake.street_address(),
                "city_name": random.choice(utils.STATE_CITIES.get(state["state_name"], [("", 0, 0)]))[0],
                "state_id": state["state_id"],
                "zip_code": fake.postcode(),
                "mission": fake.catch_phrase(),
                "web_url": "https://" + fake.domain_name(),
                "phone": fake.phone_number(),
                "email": fake.company_email(),
                "org_type": random.choice(utils.ORG_TYPES),
                "org_size": random.choice(utils.ORG_SIZES),
                "org_rating": random.randint(1, 5),
                "is_collaborator": random.choice([True, False]),
                "is_contributor": random.choice([True, False]),
                "created_at": utils.fmt_ts(created),
                "last_updated_at": utils.fmt_ts(updated),
            }
        )
    return rows


# ---------------------------------------------------------------------------
# Validation (mirrors the issue's "Data Quality Validation" checklist)
# ---------------------------------------------------------------------------
def validate(
    countries, states, cities, users, volunteer_details, user_skills,
    volunteer_locations, user_locations, help_categories, organizations,
):
    errors = []

    country_ids = {c["country_id"] for c in countries}
    state_ids = {s["state_id"] for s in states}
    cat_ids = {c["cat_id"] for c in help_categories}
    user_ids = {u["user_id"] for u in users}
    volunteer_detail_ids = {v["user_id"] for v in volunteer_details}

    # Primary key uniqueness
    for name, rows, key in [
        ("countries", countries, "country_id"),
        ("states", states, "state_id"),
        ("cities", cities, "city_id"),
        ("users", users, "user_id"),
        ("volunteer_details", volunteer_details, "user_id"),
        ("organizations", organizations, "org_id"),
    ]:
        vals = [r[key] for r in rows]
        if len(vals) != len(set(vals)):
            errors.append(f"Duplicate {key} values found in {name}")

    # Foreign keys
    for s in states:
        if s["country_id"] not in country_ids:
            errors.append(f"states: orphan country_id {s['country_id']}")
    for c in cities:
        if c["state_id"] not in state_ids:
            errors.append(f"cities: orphan state_id {c['state_id']}")
    for u in users:
        if u["state_id"] not in state_ids:
            errors.append(f"users: orphan state_id {u['state_id']}")
        if u["country_id"] not in country_ids:
            errors.append(f"users: orphan country_id {u['country_id']}")
    for v in volunteer_details:
        if v["user_id"] not in user_ids:
            errors.append(f"volunteer_details: orphan user_id {v['user_id']}")
    for us in user_skills:
        if us["user_id"] not in user_ids:
            errors.append(f"user_skills: orphan user_id {us['user_id']}")
        if us["cat_id"] not in cat_ids:
            errors.append(f"user_skills: orphan cat_id {us['cat_id']}")
    for vl in volunteer_locations:
        if vl["user_id"] not in volunteer_detail_ids:
            errors.append(f"volunteer_locations: orphan user_id {vl['user_id']} (not in volunteer_details)")
    for ul in user_locations:
        if ul["user_id"] not in user_ids:
            errors.append(f"user_locations: orphan user_id {ul['user_id']}")
    for o in organizations:
        if o["state_id"] not in state_ids:
            errors.append(f"organizations: orphan state_id {o['state_id']}")

    if errors:
        print("\nVALIDATION FAILED:")
        for e in errors[:50]:
            print(f"  - {e}")
        if len(errors) > 50:
            print(f"  ... and {len(errors) - 50} more")
        raise SystemExit(1)

    print("\nValidation passed: no orphan foreign keys, no duplicate primary keys.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Generate Virginia analytics mock data CSVs.")
    parser.add_argument("--users", type=int, default=400, help="Number of users to generate (default: 400)")
    parser.add_argument("--volunteer-fraction", type=float, default=0.5,
                         help="Fraction of users who are also volunteers (default: 0.5)")
    parser.add_argument("--orgs", type=int, default=100, help="Number of organizations to generate (default: 100)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility (default: 42)")
    parser.add_argument("--outdir", type=str, default=".", help="Output directory for CSVs (default: current dir)")
    args = parser.parse_args()

    random.seed(args.seed)
    Faker.seed(args.seed)
    global fake
    fake = Faker()
    Faker.seed(args.seed)

    os.makedirs(args.outdir, exist_ok=True)

    print(f"Generating mock data (users={args.users}, orgs={args.orgs}, seed={args.seed}) ...")

    countries = gen_countries()
    us_country_id = next(c["country_id"] for c in countries if c["country_code"] == "US")

    states = gen_states(us_country_id)
    cities = gen_cities(states)
    help_categories = gen_help_categories()
    users = gen_users(args.users, states, us_country_id)
    users_by_id = {u["user_id"]: u for u in users}

    volunteer_details = gen_volunteer_details(users, args.volunteer_fraction)
    volunteer_user_ids = [v["user_id"] for v in volunteer_details]

    user_skills = gen_user_skills(volunteer_user_ids, help_categories)
    volunteer_locations = gen_volunteer_locations(users_by_id, volunteer_user_ids)
    user_locations = gen_user_locations(users)
    organizations = gen_organizations(args.orgs, states)

    validate(
        countries, states, cities, users, volunteer_details, user_skills,
        volunteer_locations, user_locations, help_categories, organizations,
    )

    # Strip internal-only fields (prefixed with "_") before writing CSVs
    def clean(rows):
        return [{k: v for k, v in r.items() if not k.startswith("_")} for r in rows]

    print("\nWriting CSV files:")
    write_csv(os.path.join(args.outdir, "countries.csv"),
              ["country_id", "country_name", "phone_code", "country_code", "last_updated_at", "is_eu_member"],
              clean(countries))
    write_csv(os.path.join(args.outdir, "states.csv"),
              ["state_id", "country_id", "state_name", "state_code", "last_updated_at"],
              clean(states))
    write_csv(os.path.join(args.outdir, "cities.csv"),
              ["city_id", "state_id", "city_name", "lattitude", "longitude", "last_updated_at"],
              clean(cities))
    write_csv(os.path.join(args.outdir, "help_categories.csv"),
              ["cat_id", "cat_name", "cat_desc", "last_updated_at"],
              clean(help_categories))
    write_csv(os.path.join(args.outdir, "users.csv"),
              ["user_id", "state_id", "country_id", "user_status_id", "full_name", "first_name",
               "middle_name", "last_name", "primary_email_address", "primary_phone_number",
               "addr_ln1", "addr_ln2", "addr_ln3", "city_name", "zip_code", "last_location",
               "last_updated_at", "time_zone", "profile_picture_path", "gender",
               "language_1", "language_2", "language_3", "promotion_wizard_stage",
               "promotion_wizard_last_update_at", "external_auth_provider", "dob", "is_eu"],
              clean(users))
    write_csv(os.path.join(args.outdir, "volunteer_details.csv"),
              ["user_id", "terms_and_conditions", "terms_accepted_at", "govt_id_path1", "govt_id_path2",
               "path1_updated_at", "path2_updated_at", "availability_days", "availability_times",
               "created_at", "last_updated_at"],
              clean(volunteer_details))
    write_csv(os.path.join(args.outdir, "user_skills.csv"),
              ["user_id", "cat_id", "skill_level", "created_at", "last_updated_at"],
              clean(user_skills))
    write_csv(os.path.join(args.outdir, "volunteer_locations.csv"),
              ["user_id", "prev_loc", "curr_loc", "last_updated_at"],
              clean(volunteer_locations))
    write_csv(os.path.join(args.outdir, "user_locations.csv"),
              ["user_id", "prev_loc", "curr_loc", "last_updated_at"],
              clean(user_locations))
    write_csv(os.path.join(args.outdir, "organizations.csv"),
              ["org_id", "org_name", "street", "city_name", "state_id", "zip_code", "mission",
               "web_url", "phone", "email", "org_type", "org_size", "org_rating",
               "is_collaborator", "is_contributor", "created_at", "last_updated_at"],
              clean(organizations))

    print("\nDone.")


if __name__ == "__main__":
    main()
