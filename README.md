# 🎯 TriServe

> **Food · Entertainment · Market — One Login**

TriServe is a full-stack multi-service platform built with **Streamlit** and **MySQL**. From a single account, users can order food from restaurants, book movie and concert tickets, and shop from an online grocery & lifestyle market — all with OTP-secured login, real-time order tracking, and multiple payment options.

---

## ✨ Features

### 🔐 Authentication
- Customer login with **OTP email verification** (2FA via Gmail SMTP)
- New customer registration with field-level validation (name, phone, email, pincode)
- Separate **Admin login** portal with hardcoded credentials and restricted access

### 🍔 Food Ordering (Zomato-style)
- Browse restaurants filtered by city
- Add items to cart with quantity controls
- Live order tracking with animated progress bar
- **Delivery OTP** verification on arrival
- Downloadable plain-text invoice after delivery
- Post-delivery review submission stored in MySQL

### 🎬 Entertainment Booking (DiS — District Entertainment)
- Book **movie tickets** across Ahmedabad, Mumbai, and Delhi
- Book **concert tickets** at major venues with tiered seating (VIP, Gold, Fan Pit, etc.)
- Interactive **seat selection grid** with real-time availability
- Full booking history with event details

### 🛒 InstaMarket (ZipMart-style)
- Shop across 12 product categories: Groceries, Electronics, Beauty, Gifting, Imported goods, and more
- Weight/volume/size selectors for relevant items
- Coupon code support (`SAVE10`)
- Live delivery countdown timer after order placement
- Order history with spending analytics and bar chart (Matplotlib)

### 🛡️ Admin Panel
- **Orders by Restaurant** — pie chart distribution using Matplotlib
- **Customer Reviews** — filterable by city with keyword search
- **InstaMarket Orders** — all platform purchases with totals
- **Add Restaurant & Menu** — dynamically insert new restaurants and menu items into the database

### 💳 Payment System
- Supports **COD**, **UPI**, and **Card** payments
- Real-time format validation (16-digit card, 3-digit CVV, UPI ID regex, 4-digit PIN)
- Custom exception hierarchy: `PaymentError → CODPaymentError / UPIPaymentError / CardPaymentError`

---

## 🗂️ Project Structure

```
triserve/
├── triserve_merged.py   # Main Streamlit application (all modules merged)
├── import_data.py       # One-time CSV-to-MySQL import script
├── triserve_db.csv      # Seed data for all tables
└── README.md
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Frontend / UI | Streamlit |
| Backend Logic | Python 3 |
| Database | MySQL (via XAMPP) |
| ORM / Driver | `mysql-connector-python` |
| Charts | Matplotlib |
| Data Handling | Pandas |
| Email / OTP | smtplib + Gmail SMTP |
| Design Patterns | ABC (abstract validators), custom exception hierarchy |

---

## ⚙️ Setup & Installation

### Prerequisites
- Python 3.8+
- [XAMPP](https://www.apachefriends.org/) with MySQL running
- A Gmail account with an [App Password](https://myaccount.google.com/apppasswords) configured

### 1. Clone the repository
```bash
git clone https://github.com/your-username/triserve.git
cd triserve
```

### 2. Install dependencies
```bash
pip install streamlit pandas mysql-connector-python matplotlib
```

### 3. Set up the database

Start XAMPP and ensure MySQL is running. Then create the database and tables in **phpMyAdmin** or the MySQL CLI:

```sql
CREATE DATABASE triserve_db;
```

Run the provided SQL schema to create all tables (`users`, `restaurants`, `menu_items`, `orders`, `reviews`, `instamarket_orders`).

### 4. Import seed data
```bash
python import_data.py
```

This reads `triserve_db.csv` and populates all tables. Run **once only**.

### 5. Launch the app
```bash
streamlit run triserve_merged.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## 🔑 Default Credentials

### Admin Accounts
| Email | Password |
|---|---|
| admin@triserve.com | Admin@123 |
| manager@triserve.com | Manager@456 |
| superadmin@triserve.com | Super@789 |

### Customer Accounts
Register a new account via the **Sign Up** tab, or use any seeded user from `triserve_db.csv`.

> **Note:** Customer login requires OTP verification. Make sure the email address used during registration is valid and accessible.

---

## 🏙️ Supported Cities

| City | Food | Movies | Concerts |
|---|---|---|---|
| Ahmedabad | ✅ | ✅ | ✅ |
| Mumbai | ✅ | ✅ | ✅ |
| Delhi | ✅ | ✅ | ✅ |

---

## 📌 Notes

- The SMTP credentials in `triserve_merged.py` use a Gmail App Password. Replace with your own before deploying.
- Pincode validation is enforced during registration for all three cities.
- The `import_data.py` script uses `INSERT IGNORE` to safely skip duplicate rows on re-runs.

---

## 📄 License

This project is intended for academic and demonstration purposes.
