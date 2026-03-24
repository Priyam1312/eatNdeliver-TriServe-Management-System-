"""
TriServe — Database Import Script
Run this ONCE after creating the MySQL tables to populate them from triserve_db.csv
Usage: python import_data.py
"""
import csv
import mysql.connector
from mysql.connector import Error

# ── DB Config — update password if yours isn't blank ─────────
DB_CONFIG = {
    "host":     "localhost",
    "user":     "root",
    "password": "",
    "database": "triserve_db"
}

# ── Table name map (first column → table name) ────────────────
TABLE_MAP = {
    "item_id":       "menu_items",
    "order_id":      "orders",
    "restaurant_id": "restaurants",
    "review_id":     "reviews",
    "user_id":       "users",
}

def parse_csv(filepath):
    """Split the multi-table CSV into sections by detecting header rows."""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    lines   = content.strip().split("\n")
    sections = {}
    current_header = None
    current_rows   = []

    for line in lines:
        stripped  = line.strip()
        first_col = stripped.strip('"').split('"')[0]
        if not first_col.isdigit():
            if current_header:
                sections[current_header] = current_rows
            current_header = line.strip()
            current_rows   = []
        else:
            current_rows.append(line.strip())

    if current_header:
        sections[current_header] = current_rows

    return sections


def import_sections(sections, conn):
    cursor = conn.cursor()
    total_rows = 0

    for header, rows in sections.items():
        # Parse column names
        cols  = [c.strip('"') for c in header.replace('"', '').split(',')]
        tname = TABLE_MAP.get(cols[0])

        if not tname:
            print(f"  ⚠️  Skipping unknown table (first col: {cols[0]})")
            continue

        print(f"  → Importing {len(rows)} rows into '{tname}' ...")

        for row in rows:
            # Split by '","' and clean quotes
            vals = [v.strip('"') for v in row.split('","')]
            vals[0]  = vals[0].strip('"')
            vals[-1] = vals[-1].strip('"')

            placeholders = ", ".join(["%s"] * len(vals))
            sql = f"INSERT IGNORE INTO {tname} VALUES ({placeholders})"
            try:
                cursor.execute(sql, vals)
                total_rows += 1
            except Error as e:
                print(f"    ⚠️  Row skipped ({e}): {row[:60]}...")

    conn.commit()
    return total_rows


def main():
    print("=" * 50)
    print("  TriServe — Database Import")
    print("=" * 50)

    # Parse CSV
    print("\n📂  Reading triserve_db.csv ...")
    try:
        sections = parse_csv("triserve_db.csv")
    except FileNotFoundError:
        print("❌  triserve_db.csv not found. Make sure it's in the same folder as this script.")
        return

    print(f"   Found {len(sections)} table sections in CSV.")

    # Connect to DB
    print("\n🔌  Connecting to MySQL ...")
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        print("   Connected ✅")
    except Error as e:
        print(f"❌  Connection failed: {e}")
        print("   → Make sure XAMPP MySQL is running and 'triserve_db' database exists.")
        return

    # Import
    print("\n📥  Importing data ...")
    total = import_sections(sections, conn)
    conn.close()

    print(f"\n✅  Done! {total} rows imported successfully.")
    print("   You can now run:  streamlit run triserve_merged.py")
    print("=" * 50)


if __name__ == "__main__":
    main()
