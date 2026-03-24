import streamlit as st
import pandas as pd
import mysql.connector
from mysql.connector import Error
import time
import random
import smtplib
import re
import matplotlib.pyplot as plt
from datetime import datetime, date
from datetime import time as dtime
from abc import ABC, abstractmethod

# ============================================================
#  CUSTOM EXCEPTIONS
# ============================================================
class TriServeException(Exception): pass
class InvalidCredentialsError(TriServeException): pass
class OTPVerificationError(TriServeException): pass
class VendorMismatchError(TriServeException): pass
class PaymentError(TriServeException): pass
class CODPaymentError(PaymentError): pass
class UPIPaymentError(PaymentError): pass
class CardPaymentError(PaymentError): pass
class DistrictBookingError(TriServeException): pass
class SeatSelectionError(DistrictBookingError): pass

# ============================================================
#  VALIDATORS
# ============================================================
class Validator(ABC):
    @abstractmethod
    def validate(self, value): pass

class NameValidator(Validator):
    def validate(self, value):
        return value.strip() != "" and all(ch.isalpha() or ch == " " for ch in value)

class PhoneValidator(Validator):
    def validate(self, value):
        return value.isdigit() and len(value) == 10 and value[0] in ['6','7','8','9']

class EmailValidator(Validator):
    def validate(self, value):
        tlds = (".com", ".org", ".edu", ".net", ".gov")
        if "@" not in value or not value.endswith(tlds): return False
        parts = value.split("@")
        if len(parts) != 2: return False
        username, domain = parts
        return username != "" and domain not in [".com",".org",".gov",".edu",".net"]

name_validator  = NameValidator()
phone_validator = PhoneValidator()
email_validator = EmailValidator()

# ============================================================
#  ADMIN CREDENTIALS  (hardcoded — no sign-up)
# ============================================================
ADMIN_CREDENTIALS = {
    "admin@triserve.com":       "Admin@123",
    "manager@triserve.com":     "Manager@456",
    "superadmin@triserve.com":  "Super@789",
}

# ============================================================
#  DATA STRUCTURES
# ============================================================
MOVIES = {
    "Ahmedabad": {
        "PVR Acropolis":            {"Jawan": ["6 PM","9 PM"], "Avatar 2": ["4 PM","7 PM"], "KGF 2": ["6 PM"]},
        "Cinepolis Nexus":          {"Pathaan": ["5 PM","8 PM"], "RRR": ["10 PM"], "Jawan": ["1 PM"]},
        "Inox Himalaya Mall":       {"Spider-Man": ["4 PM","7 PM"], "Top Gun": ["9 PM"], "Batman": ["3 PM"]},
        "Connaught Place Cinemas":  {"KGF 2": ["12 PM","6 PM"], "RRR": ["9 PM"]}
    },
    "Mumbai": {
        "PVR Juhu":             {"Jawan": ["5 PM","8 PM"], "Avatar 2": ["4 PM","7 PM"]},
        "Inox Nariman Point":   {"Pathaan": ["6 PM","9 PM"], "Batman": ["2 PM"], "Top Gun": ["8 PM"]},
        "Carnival Cinemas":     {"KGF 2": ["5 PM","8 PM"], "RRR": ["6 PM"]},
        "Metro INOX":           {"Doctor Strange": ["1 PM","4 PM"], "Black Panther": ["7 PM"]}
    },
    "Delhi": {
        "PVR Director's Cut (Ambience Mall)": {"Jawan": ["7 PM","10 PM"], "Avatar 2": ["1 PM","4 PM"]},
        "PVR Select CITYWALK":                {"Pathaan": ["5 PM","8 PM"], "Top Gun: Maverick": ["2 PM","9 PM"]},
        "Inox Insignia (Epicuria)":           {"KGF 2": ["3 PM","6 PM"], "RRR": ["9 PM"]},
        "Delite Diamond (Daryaganj)":         {"Spider-Man: No Way Home": ["12 PM","6 PM"], "Jawan": ["9 PM"]}
    }
}

CONCERTS = {
    "Ahmedabad": {
        "Narendra Modi Stadium": ["Arijit Singh Live","Coldplay Live","Taylor Swift","BTS"],
        "EKA Arena":             ["Sunburn EDM","Ed Sheeran Live","Imagine Dragons"],
        "GMDC Ground":           ["A.R. Rahman Live","Shreya Ghosal Live","Maroon 5 Live"],
        "Riverfront Ground":     ["Nucleya Live","Darshan Raval Night"]
    },
    "Mumbai": {
        "Wankhede Stadium":      ["Coldplay Live","Taylor Swift","BTS World Tour"],
        "Jio World Garden":      ["Maroon 5 Live","Ed Sheeran Live","Arijit Singh Live"],
        "DY Patil Stadium":      ["Sunburn EDM Night","Imagine Dragons","Post Malone"],
        "Mahalaxmi Racecourse":  ["Lollapalooza India","Alan Walker Tour"]
    },
    "Delhi": {
        "Jawaharlal Nehru Stadium":    ["Diljit Dosanjh: Dil-Luminati Tour","Post Malone Live"],
        "Indira Gandhi Arena":         ["Alan Walker India Tour","Bryan Adams Live"],
        "Major Dhyan Chand Stadium":   ["Lollapalooza India","A.R. Rahman Live"],
        "Kingdom of Dreams":           ["Zangoora The Gypsy Prince","Shreya Ghosal Night"]
    }
}

MOVIE_PRICES    = {"A": 400, "B": 300, "C": 300, "D": 200, "E": 200}
CONCERT_STANDS  = {"VIP Platinum": 5000, "Front Row Gold": 3000, "Fan Pit": 2000, "General Admission": 1000}

SECTION_IMAGES = {
    "movie":      "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?auto=format&fit=crop&w=1200",
    "concert":    "https://images.unsplash.com/photo-1470225620780-dba8ba36b745?auto=format&fit=crop&w=1200",
    "restaurant": "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?auto=format&fit=crop&w=1200",
    "grocery":    "https://images.unsplash.com/photo-1542838132-92c53300491e?auto=format&fit=crop&w=1200",
}

PRODUCTS = {
    "Fruits 🍎":        {"Apple": 120, "Mango": 150, "Orange": 60},
    "Vegetables 🥕":    {"Potato": 30, "Onion": 28, "Carrot": 40},
    "Dairy 🥛":         {"Milk": 50, "Butter": 70, "Curd": 40},
    "Snacks 🍪":        {"Chips": 20, "Biscuits": 30, "Chocolate": 50},
    "Drinks 🧃":        {"Green Tea": 40},
    "Home Decor 🛋":    {"Wall Clock": 499, "Vase": 299, "Photo Frame": 199},
    "Winter Clothes 🧥": {"Jacket": 1499, "Sweater": 999, "Hoodie": 899, "Shawl": 699},
    "Electronics 📱":   {"Earphones": 799, "Speaker": 1499, "Charger": 499},
    "Beauty 💄":        {"Face Cream": 399, "Lipstick": 299, "Perfume": 899, "Face Wash": 249},
    "Kids 🧒":          {"Toy Car": 349, "Puzzle": 299, "Crayons": 99},
    "Gifting 🎁":       {"Gift Box": 699, "Bouquet": 599, "Mug": 349, "Card": 99},
    "Imported 🌍":      {"Chocolate": 499, "Pasta": 299, "Olive Oil": 699, "Cookies": 349}
}

GROCERY_CATS  = ["Fruits 🍎", "Vegetables 🥕", "Dairy 🥛", "Snacks 🍪"]
DRINK_CAT     = "Drinks 🧃"
CLOTHING_CATS = ["Winter Clothes 🧥"]
WEIGHT_MUL    = {"250g": 0.25, "500g": 0.5, "1kg": 1, "2kg": 2}
DRINK_MUL     = {"250ml": 0.25, "500ml": 0.5, "1L": 1, "2L": 2}
SIZE_MUL      = {"S": 1.0, "M": 1.05, "L": 1.1, "XL": 1.2}

ITEM_IMGS = {
    "Apple":"https://images.unsplash.com/photo-1560806887-1e4cd0b6cbd6?w=200",
    "Mango":"https://images.unsplash.com/photo-1553279768-865429fa0078?w=200",
    "Orange":"https://images.unsplash.com/photo-1547514701-42782101795e?w=200",
    "Potato":"https://images.unsplash.com/photo-1518977676601-b53f82aba655?w=200",
    "Onion":"https://images.unsplash.com/photo-1508747703725-719777637510?w=200",
    "Carrot":"https://images.unsplash.com/photo-1598170845058-32b9d6a5da37?w=200",
    "Milk":"https://images.unsplash.com/photo-1563636619-e9143da7973b?w=200",
    "Butter":"https://images.unsplash.com/photo-1589985270826-4b7bb135bc9d?w=200",
    "Curd":"https://images.unsplash.com/photo-1571212515416-fef01fc43637?w=200",
    "Chips":"https://images.unsplash.com/photo-1566478989037-eec170784d0b?w=200",
    "Biscuits":"https://images.unsplash.com/photo-1558961363-fa8fdf82db35?w=200",
    "Chocolate":"https://images.unsplash.com/photo-1511381939415-e44015466834?w=200",
    "Green Tea":"https://images.unsplash.com/photo-1564890369478-c89ca6d9cde9?w=200",
    "Wall Clock":"https://images.unsplash.com/photo-1563861826100-9cb868fdbe1c?w=200",
    "Vase":"https://images.unsplash.com/photo-1581783898377-1c85bf937427?w=200",
    "Photo Frame":"https://images.unsplash.com/photo-1583847268964-b28dc8f51f92?w=200",
    "Jacket":"https://images.unsplash.com/photo-1551028719-00167b16eac5?w=200",
    "Sweater":"https://images.unsplash.com/photo-1620799140408-edc6dcb6d633?w=200",
    "Hoodie":"https://images.unsplash.com/photo-1556821840-3a63f95609a7?w=200",
    "Shawl":"https://images.unsplash.com/photo-1606760227091-3dd870d97f1d?w=200",
    "Earphones":"https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=200",
    "Speaker":"https://images.unsplash.com/photo-1545454675-3531b543be5d?w=200",
    "Charger":"https://images.unsplash.com/photo-1583863788434-e58a36330cf0?w=200",
    "Face Cream":"https://images.unsplash.com/photo-1556228720-195a672e8a03?w=200",
    "Lipstick":"https://images.unsplash.com/photo-1586776977607-310e9c725c37?w=200",
    "Perfume":"https://images.unsplash.com/photo-1541643600914-78b084683601?w=200",
    "Face Wash":"https://images.unsplash.com/photo-1556228578-0d85b1a4d571?w=200",
    "Toy Car":"https://images.unsplash.com/photo-1594736797933-d0501ba2fe65?w=200",
    "Puzzle":"https://images.unsplash.com/photo-1586165368502-1bad197a6461?w=200",
    "Crayons":"https://images.unsplash.com/photo-1513364776144-60967b0f800f?w=200",
    "Gift Box":"https://images.unsplash.com/photo-1549465220-1a8b9238cd48?w=200",
    "Bouquet":"https://images.unsplash.com/photo-1582794543139-8ac9cb0f7b11?w=200",
    "Mug":"https://images.unsplash.com/photo-1514228742587-6b1558fcca3d?w=200",
    "Card":"https://images.unsplash.com/photo-1549465220-1a8b9238cd48?w=200",
    "Pasta":"https://images.unsplash.com/photo-1551183053-bf91a1d81141?w=200",
    "Olive Oil":"https://images.unsplash.com/photo-1474979266404-7eaacbcd87c5?w=200",
    "Cookies":"https://images.unsplash.com/photo-1499636136210-6f4ee915583e?w=200",
    "Namkeen":"https://images.unsplash.com/photo-1601050633647-81a317577a36?w=200",
}

ZIPMART_COUPON = {"SAVE10": 10}

# ============================================================
#  DATABASE CONNECTION
# ============================================================
def get_db_connection():
    try:
        return mysql.connector.connect(
            host='localhost', user='root', password='', database='triserve_db'
        )
    except Error as e:
        st.error(f"Database Connection Failed: {e}")
        return None

# ============================================================
#  EMAIL / OTP
# ============================================================
def send_otp_email(receiver_email):
    sender_email = "your_gmail_here"
    password     = "your_password_here"
    otp = random.randint(100000, 999999)
    try:
        con = smtplib.SMTP("smtp.gmail.com", port=587)
        con.starttls()
        con.login(user=sender_email, password=password)
        msg = (
            f"Subject:OTP Verification\n\n"
            f"Your OTP for TriServe is {otp}.\n"
            "Do not share this OTP with anyone for security reasons.\n"
            "Your OTP expires in 5 minutes\n\nRegards,\nTriServe Team"
        )
        con.sendmail(from_addr=sender_email, to_addrs=receiver_email, msg=msg)
        con.close()
        st.session_state.current_otp = otp
        st.success(f"OTP sent successfully to {receiver_email}")
        return True
    except Exception as e:
        st.error(f"Failed to send email: {e}")
        return False

# ============================================================
#  SESSION STATE INITIALISATION
# ============================================================
def init_session():
    defaults = {
        "page":             "Login",
        "logged_in":        False,
        "user":             None,
        "is_admin":         False,
        # zomato
        "cart":             [],
        "active_rest_id":   None,
        "active_rest_name": None,
        "selected_rest":    None,
        "tracking_complete":False,
        "delivered":        False,
        "summary":          None,
        # dis
        "booked_seats":     set(),
        "selected_seats":   set(),
        "dis_history":      [],
        # zipmart
        "zm_cart":          {},
        "zm_page":          "shop",
        "zm_selected_cat":  "All",
        "zm_orders":        [],
        "zm_delivery_time": None,
        "zm_discount_pct":  0,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

# ============================================================
#  AUTH PAGE  (Login + Sign-Up + Admin Login)
# ============================================================
def auth_page():
    st.markdown("""
        <div style='text-align:center; padding: 2rem 0 1rem 0;'>
            <h1 style='font-size:3rem; margin-bottom:0;'>🎯 TriServe</h1>
            <p style='color:gray; font-size:1.1rem;'>Food · Entertainment · Market — One Login</p>
        </div>
    """, unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["🔐 Customer Login", "📝 Sign Up", "🛡️ Admin Login"])

    # ── CUSTOMER LOGIN ─────────────────────────────────────────
    with tab1:
        if "temp_user" not in st.session_state:
            email_input = st.text_input("Email ID / Phone Number", key="login_email")
            pwd_input   = st.text_input("Password", type="password", key="login_pwd")

            if st.button("Proceed to Login", use_container_width=True, type="primary"):
                conn = get_db_connection()
                if conn:
                    cursor = conn.cursor(dictionary=True)
                    cursor.execute(
                        "SELECT * FROM users WHERE (email=%s OR phone=%s) AND password=%s",
                        (email_input, email_input, pwd_input)
                    )
                    user = cursor.fetchone()
                    conn.close()
                    if user:
                        st.session_state.temp_user = user
                        st.rerun()
                    else:
                        st.error("Invalid Credentials. Please try again.")
        else:
            st.success(f"Welcome back, {st.session_state.temp_user['name']}! 👋")
            if "login_otp_sent" not in st.session_state:
                with st.spinner("Sending OTP to your email..."):
                    if send_otp_email(st.session_state.temp_user["email"]):
                        st.session_state.login_otp_sent = True
                    else:
                        st.error("Failed to send OTP. Please check your connection.")

            st.warning("⚠️ SECURITY CHECK: An OTP has been sent to your registered email.")
            otp_check = st.number_input("Enter 6-digit OTP", min_value=0, max_value=999999, step=1, format="%d")

            col_v1, col_v2 = st.columns(2)
            if col_v1.button("✅ Verify & Enter", use_container_width=True, type="primary"):
                if otp_check == st.session_state.current_otp:
                    st.session_state.user       = st.session_state.temp_user
                    st.session_state.logged_in  = True
                    st.session_state.is_admin   = False
                    st.session_state.page       = "Dashboard"
                    del st.session_state.temp_user
                    del st.session_state.login_otp_sent
                    st.rerun()
                else:
                    st.error("Incorrect OTP. Access Denied.")
            if col_v2.button("❌ Cancel / Back", use_container_width=True):
                del st.session_state.temp_user
                st.rerun()

    # ── SIGN UP ────────────────────────────────────────────────
    with tab2:
        st.subheader("Customer Registration")
        c_name  = st.text_input("Full Name")
        c_email = st.text_input("Email ID (e.g., user@mail.com)")
        c_phone = st.text_input("Phone Number", max_chars=10)
        c_pwd   = st.text_input("Create Password", type="password")

        col1, col2 = st.columns(2)
        c_hno = col1.text_input("Home No / Building Name")
        c_a1  = col2.text_input("Address Line 1")
        c_a2  = col1.text_input("Address Line 2")
        c_sub = col2.text_input("Area / Suburb")

        c_city = st.selectbox("City", ["Ahmedabad", "Mumbai", "Delhi"])
        c_pin  = st.text_input("Pincode", max_chars=6)

        pincode_ranges = {
            "Ahmedabad": (380001, 380061),
            "Mumbai":    (400001, 400104),
            "Delhi":     (110001, 110096)
        }
        if c_pin:
            if not c_pin.isdigit() or len(c_pin) != 6:
                st.error("Please enter a valid 6-digit pincode.")
            else:
                pin = int(c_pin)
                start, end = pincode_ranges[c_city]
                if not (start <= pin <= end):
                    st.error(f"Invalid pincode for {c_city}. Must be between {start} and {end}.")
                else:
                    st.success(f"Valid pincode for {c_city} ✅")

        if st.button("Register Account", use_container_width=True, type="primary"):
            errors = False
            if not name_validator.validate(c_name):
                st.error("Name should contain only alphabets"); errors = True
            if not phone_validator.validate(c_phone):
                st.error("Phone must start with 6/7/8/9 and be 10 digits"); errors = True
            if not email_validator.validate(c_email):
                st.error("Invalid email ID"); errors = True

            if not errors:
                conn = get_db_connection()
                if conn:
                    cursor = conn.cursor()
                    try:
                        sql = ("INSERT INTO users (name,email,phone,password,role,"
                               "home_no,address_line1,address_line2,suburb,city,pincode) "
                               "VALUES (%s,%s,%s,%s,'Customer',%s,%s,%s,%s,%s,%s)")
                        cursor.execute(sql, (c_name,c_email,c_phone,c_pwd,
                                             c_hno,c_a1,c_a2,c_sub,c_city,str(c_pin)))
                        conn.commit()
                        st.success("Registration Successful! Switch to Login tab. 🎉")
                    except Error as e:
                        st.error(f"Account exists or DB Error: {e}")
                    finally:
                        conn.close()

    # ── ADMIN LOGIN ────────────────────────────────────────────
    with tab3:
        st.markdown("""
            <div style='background: linear-gradient(135deg, #1a1a2e, #16213e);
                        border: 1px solid #e94560; border-radius: 10px;
                        padding: 1.5rem; margin-bottom: 1rem;'>
                <h3 style='color:#e94560; margin:0;'>🛡️ Admin Access Portal</h3>
                <p style='color:#aaa; margin:0.5rem 0 0 0; font-size:0.9rem;'>
                    Restricted area — authorised personnel only
                </p>
            </div>
        """, unsafe_allow_html=True)

        admin_email = st.text_input("Admin Email", key="admin_email", placeholder="admin@triserve.com")
        admin_pwd   = st.text_input("Admin Password", type="password", key="admin_pwd")

        if st.button("🔓 Admin Login", use_container_width=True, type="primary", key="admin_login_btn"):
            if admin_email in ADMIN_CREDENTIALS and ADMIN_CREDENTIALS[admin_email] == admin_pwd:
                st.session_state.logged_in = True
                st.session_state.is_admin  = True
                st.session_state.user      = {"name": admin_email.split("@")[0].capitalize(),
                                               "email": admin_email, "role": "Admin"}
                st.session_state.page      = "AdminPanel"
                st.rerun()
            else:
                st.error("❌ Invalid Admin Credentials. Access Denied.")

        st.caption("👥 3 admin accounts are registered. Contact IT for access.")

# ============================================================
#  SHARED: PAYMENT WIDGET
# ============================================================
def payment_widget(context="food"):
    method = st.selectbox("💳 Payment Method", ["COD", "UPI", "CARD"], key=f"pay_method_{context}")
    valid  = False
    raw_card, cvv, upi_id = "", "", ""

    if method == "UPI":
        upi_id  = st.text_input("UPI ID (e.g. name@upi)", key=f"upi_{context}")
        upi_pin = st.text_input("4-Digit UPI PIN", type="password", max_chars=4, key=f"upi_pin_{context}")
        if upi_pin and (not upi_pin.isdigit() or len(upi_pin) != 4):
            st.error("UPI PIN must be a 4-digit number.")
        if upi_id and re.match(r'^[\w.\-]+@[\w.\-]+$', upi_id) and upi_pin and len(upi_pin) == 4:
            valid = True

    elif method == "CARD":
        st.selectbox("Card Type", ["Visa", "Mastercard"], key=f"ctype_{context}")
        st.text_input("Card Holder Name", key=f"cname_{context}")
        raw_card    = st.text_input("16-Digit Card Number", max_chars=16,
                                    help="Format: XXXX XXXX XXXX XXXX", key=f"card_{context}")
        card_digits = raw_card.replace(" ", "")
        if card_digits and not card_digits.isdigit():
            st.error("Card number must contain only digits.")
        if len(card_digits) > 0:
            formatted = " ".join(card_digits[i:i+4] for i in range(0, len(card_digits), 4))
            st.caption(f"Formatted: `{formatted}`")
        cvv = st.text_input("3-Digit CVV", type="password", max_chars=3, key=f"cvv_{context}")
        if cvv and (not cvv.isdigit() or len(cvv) != 3):
            st.error("CVV must be a 3-digit number.")
        if len(card_digits) == 16 and len(cvv) == 3:
            valid = True

    else:
        st.info("₹100 COD surcharge will be added.")
        valid = True

    return method, valid, raw_card, cvv, upi_id

# ============================================================
#  SHARED: TRACKING
# ============================================================
def tracking_page():
    st.title("🚚 Real-time Order Tracking")
    u = st.session_state.user
    s = st.session_state.summary

    if not st.session_state.tracking_complete:
        status_area = st.empty()
        main_bar    = st.progress(0)

        status_area.markdown("### Status: **Order Received**")
        main_bar.progress(25)
        with st.spinner("Restaurant is confirming your order..."):
            time.sleep(2)

        status_area.markdown("### Status: **Order in Making**")
        main_bar.progress(75)
        with st.spinner("Chef is preparing your meal..."):
            time.sleep(3)

        status_area.markdown("### Status: **Order Out for Delivery**")
        main_bar.progress(100)
        st.success("Your order is on the way! 🛵")
        time.sleep(1)

        st.divider()
        st.subheader("Out for Delivery (Tracking)")
        delivery_status = st.empty()
        time_bar        = st.progress(0)
        total_seconds   = 30
        for i in range(total_seconds + 1):
            mins_remaining = int((total_seconds - i) / 3)
            delivery_status.write(f"⏱️ **{mins_remaining} mins remaining**")
            time_bar.progress(i / total_seconds)
            time.sleep(0.05)

        st.session_state.tracking_complete = True
        st.rerun()

    if st.session_state.tracking_complete and not st.session_state.delivered:
        st.success("🚀 Driver has arrived at your location!")
        st.warning("Please provide the Delivery OTP to receive your order.")

        if "delivery_otp_sent" not in st.session_state:
            send_otp_email(u["email"])
            st.session_state.delivery_otp_sent = True

        d_otp = st.number_input("Enter 6-Digit Delivery OTP",
                                 min_value=0, max_value=999999, step=1, format="%d")
        if st.button("Verify Delivery OTP", type="primary"):
            if d_otp == st.session_state.current_otp:
                st.session_state.delivered = True
                st.balloons()
                st.rerun()
            else:
                st.error("Incorrect Delivery OTP. Access Denied.")

    if st.session_state.delivered:
        st.header("✅ Order Delivered")

        st.subheader("📝 Rate & Review Your Experience")
        review_text = st.text_area("Write your review",
                                   placeholder="Tell us about the food, delivery and experience...")
        if st.button("Share Review"):
            if review_text.strip() == "":
                st.error("Review cannot be empty")
            else:
                conn = get_db_connection()
                if conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO reviews (user_id, restaurant_id, city, review_text) VALUES (%s,%s,%s,%s)",
                        (u["user_id"], st.session_state.active_rest_id, u["city"], review_text)
                    )
                    conn.commit()
                    conn.close()
                    st.success("We value your feedback, Thank you ❤️")

        items_list = "".join(
            [f"{row['name']} x{row['qty']} @ ₹{row['price']} = ₹{row['total']}\n"
             for _, row in s["df"].iterrows()]
        )
        invoice_text = f"""
==============================
{s['rest'].upper()}
==============================
Customer Name : {u['name']}
Phone         : {u['phone']}
Email         : {u['email']}

ITEMS            QTY   PRICE   TOTAL
--------------------------------------
{items_list}--------------------------------------
Subtotal        : ₹{s['sub']:.2f}
GST (18%)       : ₹{s['gst']:.2f}
Service (5%)    : ₹{s['svc']:.2f}
Delivery Fee    : ₹{s['del']:.2f}
Tip             : ₹{s['tip']:.2f}

TOTAL AMOUNT    : ₹{s['total']:.2f}
--------------------------------------
Thank you for ordering with TriServe!
"""
        st.text_area("📄 Final Invoice", value=invoice_text, height=300)
        st.download_button("📥 Download Invoice", data=invoice_text,
                           file_name="TriServe_Invoice.txt")

        if st.button("🏠 Return to Dashboard"):
            for k in ["cart","active_rest_id","active_rest_name","tracking_complete",
                      "delivered","summary","delivery_otp_sent"]:
                if k in st.session_state:
                    st.session_state[k] = [] if k == "cart" else None if k in ["active_rest_id","active_rest_name","summary","selected_rest"] else False
            st.session_state.cart = []
            st.session_state.page = "Dashboard"
            st.rerun()

# ============================================================
#  ADMIN PANEL
# ============================================================
def admin_panel():
    u = st.session_state.user

    # ── Admin Sidebar ──────────────────────────────────────────
    st.sidebar.markdown(f"""
        <div style='background:#e94560; padding:0.8rem; border-radius:8px; margin-bottom:1rem;'>
            <h4 style='color:white; margin:0;'>🛡️ Admin Panel</h4>
            <p style='color:#ffd; margin:0; font-size:0.85rem;'>{u['email']}</p>
        </div>
    """, unsafe_allow_html=True)

    admin_section = st.sidebar.radio(
        "Admin Sections",
        ["📊 Orders by Restaurant", "⭐ Customer Reviews",
         "📦 InstaMarket Orders", "➕ Add Restaurant & Menu"]
    )

    st.sidebar.divider()

    # ── Main Header ────────────────────────────────────────────
    st.markdown("""
        <div style='background: linear-gradient(135deg, #1a1a2e, #16213e);
                    border-left: 5px solid #e94560; border-radius: 8px;
                    padding: 1.2rem 1.5rem; margin-bottom: 1.5rem;'>
            <h1 style='color:white; margin:0; font-size:2rem;'>🛡️ TriServe Admin Dashboard</h1>
            <p style='color:#aaa; margin:0.3rem 0 0 0;'>System Management & Analytics</p>
        </div>
    """, unsafe_allow_html=True)

    # ── Section 1: Pie Chart — Orders per Restaurant ───────────
    if admin_section == "📊 Orders by Restaurant":
        st.subheader("📊 Food Orders by Restaurant")
        st.caption("Pie chart showing the distribution of food orders across all restaurants.")

        conn = get_db_connection()
        if not conn:
            return

        query = """
            SELECT r.name AS Restaurant, COUNT(o.order_id) AS Orders
            FROM orders o
            JOIN restaurants r ON o.restaurant_id = r.restaurant_id
            GROUP BY r.restaurant_id, r.name
            ORDER BY Orders DESC
        """
        df_orders = pd.read_sql(query, conn)
        conn.close()

        if df_orders.empty:
            st.warning("No orders found in the database.")
            return

        # Summary metrics
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Orders", int(df_orders["Orders"].sum()))
        col2.metric("Restaurants with Orders", len(df_orders))
        col3.metric("Most Popular", df_orders.iloc[0]["Restaurant"])

        st.divider()

        # Pie chart
        fig, ax = plt.subplots(figsize=(10, 7))
        colors = plt.cm.Set3.colors[:len(df_orders)]

        wedges, texts, autotexts = ax.pie(
            df_orders["Orders"],
            labels=None,
            autopct=lambda p: f'{p:.1f}%\n({int(round(p * df_orders["Orders"].sum() / 100))})',
            colors=colors,
            startangle=140,
            pctdistance=0.75,
            wedgeprops=dict(edgecolor='white', linewidth=1.5)
        )

        for autotext in autotexts:
            autotext.set_fontsize(8)

        ax.legend(wedges, df_orders["Restaurant"],
                  title="Restaurants", loc="center left",
                  bbox_to_anchor=(1, 0, 0.5, 1), fontsize=8)
        ax.set_title("Distribution of Food Orders by Restaurant", fontsize=14, fontweight='bold', pad=20)
        plt.tight_layout()
        st.pyplot(fig)

        st.divider()
        st.subheader("📋 Orders Table")
        df_display = df_orders.copy()
        df_display.index = range(1, len(df_display) + 1)
        st.dataframe(df_display, use_container_width=True)

    # ── Section 2: Reviews Table ───────────────────────────────
    elif admin_section == "⭐ Customer Reviews":
        st.subheader("⭐ Customer Reviews")
        st.caption("All customer reviews submitted after food deliveries.")

        conn = get_db_connection()
        if not conn:
            return

        query = """
            SELECT
                rv.review_id       AS `#`,
                u.name             AS `Customer`,
                u.city             AS `City`,
                r.name             AS `Restaurant`,
                rv.review_text     AS `Review`,
                rv.review_date     AS `Date`
            FROM reviews rv
            JOIN users u ON rv.user_id = u.user_id
            JOIN restaurants r ON rv.restaurant_id = r.restaurant_id
            ORDER BY rv.review_date DESC
        """
        df_reviews = pd.read_sql(query, conn)
        conn.close()

        if df_reviews.empty:
            st.info("No reviews yet.")
            return

        # Summary metrics
        col1, col2 = st.columns(2)
        col1.metric("Total Reviews", len(df_reviews))
        col2.metric("Unique Restaurants Reviewed", df_reviews["Restaurant"].nunique())

        st.divider()

        # City filter
        cities = ["All"] + sorted(df_reviews["City"].unique().tolist())
        sel_city = st.selectbox("Filter by City", cities)
        if sel_city != "All":
            df_reviews = df_reviews[df_reviews["City"] == sel_city]

        # Search
        search_term = st.text_input("🔍 Search in Reviews", placeholder="Type keyword...")
        if search_term:
            df_reviews = df_reviews[
                df_reviews["Review"].str.contains(search_term, case=False, na=False) |
                df_reviews["Customer"].str.contains(search_term, case=False, na=False) |
                df_reviews["Restaurant"].str.contains(search_term, case=False, na=False)
            ]

        st.write(f"Showing **{len(df_reviews)}** review(s)")

        # Styled card display
        for _, row in df_reviews.iterrows():
            with st.container(border=True):
                c1, c2 = st.columns([3, 1])
                with c1:
                    st.markdown(f"**⭐ {row['Customer']}** — *{row['Restaurant']}*")
                    st.write(f"💬 {row['Review']}")
                with c2:
                    st.caption(f"🗓️ {str(row['Date'])[:16]}")
                    st.caption(f"📍 {row['City']}")

    # ── Section 3: InstaMarket Orders Graph ───────────────────
    elif admin_section == "📦 InstaMarket Orders":
        st.subheader("📦 InstaMarket Orders Analytics")
        st.caption("Overview of grocery/market orders placed through InstaMarket.")

        conn = get_db_connection()
        if not conn:
            return

        query = """
            SELECT
                io.order_id,
                u.name         AS Customer,
                u.city         AS City,
                io.total_price AS `Total (₹)`,
                io.order_date  AS `Order Date`
            FROM instamarket_orders io
            JOIN users u ON io.customer_id = u.user_id
            ORDER BY io.order_date DESC
        """
        df_im = pd.read_sql(query, conn)
        conn.close()

        if df_im.empty:
            st.warning("No InstaMarket orders found.")
            return

        # Metrics
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Orders", len(df_im))
        col2.metric("Total Revenue", f"₹{df_im['Total (₹)'].sum():,.2f}")
        col3.metric("Average Order Value", f"₹{df_im['Total (₹)'].mean():,.2f}")

        st.divider()

        # Bar chart — revenue per order
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))

        # Chart 1: Revenue per order
        axes[0].bar(
            df_im["order_id"].astype(str),
            df_im["Total (₹)"],
            color="#2ecc71", alpha=0.85, edgecolor='white'
        )
        axes[0].set_title("Revenue per Order", fontweight='bold')
        axes[0].set_xlabel("Order ID")
        axes[0].set_ylabel("Amount (₹)")
        axes[0].tick_params(axis='x', rotation=45)

        # Chart 2: Orders by City (if multiple cities)
        city_counts = df_im["City"].value_counts()
        axes[1].pie(
            city_counts.values,
            labels=city_counts.index,
            autopct='%1.1f%%',
            colors=["#3498db", "#e74c3c", "#f39c12", "#9b59b6"],
            startangle=90,
            wedgeprops=dict(edgecolor='white', linewidth=1.5)
        )
        axes[1].set_title("Orders by City", fontweight='bold')

        plt.tight_layout()
        st.pyplot(fig)

        st.divider()
        st.subheader("📋 All InstaMarket Orders")
        df_display = df_im.copy()
        df_display.index = range(1, len(df_display) + 1)
        st.dataframe(df_display, use_container_width=True)

    # ── Section 4: Add Restaurant & Menu Items ─────────────────
    elif admin_section == "➕ Add Restaurant & Menu":
        st.subheader("➕ Add New Restaurant & Menu Items")

        tab_r, tab_m = st.tabs(["🏠 Add Restaurant", "🍽️ Add Menu Items"])

        # ── Add Restaurant ─────────────────────────────────────
        with tab_r:
            st.markdown("#### Restaurant Details")
            r_name     = st.text_input("Restaurant Name", placeholder="e.g. Spice Garden")
            r_city     = st.selectbox("City", ["Ahmedabad", "Mumbai", "Delhi"])
            r_cuisine  = st.text_input("Cuisine Type", placeholder="e.g. North Indian, Italian")
            r_category = st.selectbox("Category",
                                      ["Veg", "Non-Veg", "Veg-(Jain)", "Vegan",
                                       "Veg-Wine", "Non-Veg-Wine"])
            r_img      = st.text_input("Image URL",
                                       placeholder="https://images.unsplash.com/...",
                                       value="https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?auto=format&fit=crop&q=80&w=800")

            if r_img:
                st.image(r_img, caption="Preview", width=300)

            if st.button("✅ Add Restaurant", type="primary", use_container_width=True):
                if not r_name.strip():
                    st.error("Restaurant name cannot be empty.")
                elif not r_cuisine.strip():
                    st.error("Cuisine type cannot be empty.")
                else:
                    conn = get_db_connection()
                    if conn:
                        try:
                            cursor = conn.cursor()
                            cursor.execute(
                                "INSERT INTO restaurants (name, city, cuisine, category, image_url) "
                                "VALUES (%s, %s, %s, %s, %s)",
                                (r_name.strip(), r_city, r_cuisine.strip(), r_category, r_img.strip())
                            )
                            conn.commit()
                            new_id = cursor.lastrowid
                            conn.close()
                            st.success(f"✅ Restaurant **{r_name}** added successfully! (ID: {new_id})")
                            st.balloons()
                        except Error as e:
                            st.error(f"DB Error: {e}")
                            conn.close()

            st.divider()
            st.subheader("📋 Existing Restaurants")
            conn = get_db_connection()
            if conn:
                df_rest_all = pd.read_sql(
                    "SELECT restaurant_id AS ID, name AS Name, city AS City, "
                    "cuisine AS Cuisine, category AS Category FROM restaurants ORDER BY city, name",
                    conn
                )
                conn.close()
                df_rest_all.index = range(1, len(df_rest_all) + 1)
                st.dataframe(df_rest_all, use_container_width=True)

        # ── Add Menu Items ─────────────────────────────────────
        with tab_m:
            st.markdown("#### Add Menu Item to a Restaurant")

            conn = get_db_connection()
            if conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT restaurant_id, name, city FROM restaurants ORDER BY city, name")
                rest_list = cursor.fetchall()
                conn.close()
            else:
                rest_list = []

            if not rest_list:
                st.warning("No restaurants found. Add a restaurant first.")
            else:
                rest_options = {f"{r['name']} ({r['city']}) [ID:{r['restaurant_id']}]": r['restaurant_id']
                                for r in rest_list}
                sel_rest_label = st.selectbox("Select Restaurant", list(rest_options.keys()))
                sel_rest_id    = rest_options[sel_rest_label]

                st.markdown("---")

                m_name     = st.text_input("Item Name", placeholder="e.g. Paneer Tikka")
                m_category = st.selectbox("Category", ["Soup", "Starter", "Main Course", "Dessert", "Drink"])
                m_price    = st.number_input("Price (₹)", min_value=1, max_value=10000, value=200, step=10)
                m_is_veg   = st.radio("Type", ["Veg 🟢", "Non-Veg 🔴"], horizontal=True)
                m_allergy  = st.text_input("Allergy Info", placeholder="e.g. Dairy, Nuts (or leave blank)")

                is_veg_val = 1 if "Veg 🟢" in m_is_veg else 0
                allergy_val = m_allergy.strip() if m_allergy.strip() else "None"

                if st.button("✅ Add Menu Item", type="primary", use_container_width=True):
                    if not m_name.strip():
                        st.error("Item name cannot be empty.")
                    else:
                        conn = get_db_connection()
                        if conn:
                            try:
                                cursor = conn.cursor()
                                cursor.execute(
                                    "INSERT INTO menu_items (restaurant_id, item_name, category, "
                                    "price, is_veg, allergy_info) VALUES (%s, %s, %s, %s, %s, %s)",
                                    (sel_rest_id, m_name.strip(), m_category,
                                     float(m_price), is_veg_val, allergy_val)
                                )
                                conn.commit()
                                new_item_id = cursor.lastrowid
                                conn.close()
                                st.success(f"✅ **{m_name}** added to the menu! (Item ID: {new_item_id})")
                            except Error as e:
                                st.error(f"DB Error: {e}")
                                conn.close()

                st.divider()
                st.subheader("📋 Current Menu for Selected Restaurant")
                conn = get_db_connection()
                if conn:
                    df_menu_preview = pd.read_sql(
                        "SELECT item_id AS ID, item_name AS `Item`, category AS Category, "
                        "price AS `Price (₹)`, "
                        "CASE WHEN is_veg=1 THEN '🟢 Veg' ELSE '🔴 Non-Veg' END AS Type, "
                        "allergy_info AS `Allergy Info` "
                        "FROM menu_items WHERE restaurant_id=%s ORDER BY category",
                        conn, params=(sel_rest_id,)
                    )
                    conn.close()
                    if df_menu_preview.empty:
                        st.info("No menu items yet for this restaurant.")
                    else:
                        df_menu_preview.index = range(1, len(df_menu_preview)+1)
                        st.dataframe(df_menu_preview, use_container_width=True)

# ============================================================
#  DASHBOARD
# ============================================================
def dashboard():
    u = st.session_state.user

    st.sidebar.markdown(f"### 👤 Hello, {u['name']}")
    st.sidebar.caption(f"📍 {u['city']}")
    st.sidebar.divider()

    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM orders WHERE user_id=%s", (u["user_id"],))
        has_bookings = cursor.fetchone()[0] > 0
        conn.close()
        if has_bookings and st.sidebar.button("📜 My Food Orders"):
            st.session_state.page = "MyBookings"
            st.rerun()

    service = st.sidebar.radio(
        "🧭 Navigate to",
        ["🍴 Food Delivery", "🎟️ Entertainment", "🛒 InstaMarket"]
    )

    if st.session_state.cart:
        if st.sidebar.button("🛒 Go to Checkout"):
            st.session_state.page = "Cart"
            st.rerun()

    if st.session_state.zm_cart:
        if st.sidebar.button("🧺 Go to Basket"):
            st.session_state.zm_page = "cart"
            st.session_state.page    = "InstaMarket"
            st.rerun()

    if service == "🍴 Food Delivery":
        food_delivery_page()
    elif service == "🎟️ Entertainment":
        entertainment_hub()
    elif service == "🛒 InstaMarket":
        st.session_state.page = "InstaMarket"
        st.rerun()

# ============================================================
#  FOOD DELIVERY
# ============================================================
def food_delivery_page():
    u = st.session_state.user
    st.image(SECTION_IMAGES["restaurant"], use_container_width=True)
    st.title("🍴 Food Delivery")

    selected_categories = st.sidebar.multiselect(
        "Filter by Category",
        options=["Veg","Non-Veg","Veg-(Jain)","Vegan","Veg-Wine","Non-Veg-Wine"],
        default=[]
    )
    sort_choice = st.sidebar.selectbox("Sort Restaurants by", ["Name (A-Z)","Name (Z-A)"])

    search_cuisine = st.text_input("🔍 Search Cuisine (e.g. North Indian, Italian)")

    conn = get_db_connection()
    if not conn: return
    df_rest = pd.read_sql(
        f"SELECT * FROM restaurants WHERE city='{u['city']}'", conn
    )
    conn.close()

    if search_cuisine:
        df_rest = df_rest[df_rest["cuisine"].str.contains(search_cuisine, case=False)]
    if selected_categories:
        df_rest = df_rest[df_rest["category"].isin(selected_categories)]
    df_rest = df_rest.sort_values("name", ascending=(sort_choice == "Name (A-Z)"))

    if df_rest.empty:
        st.warning("No restaurants found matching your filters.")
        return

    for _, r in df_rest.iterrows():
        with st.container(border=True):
            c1, c2 = st.columns([1, 2])
            c1.image(r["image_url"])
            c2.subheader(r["name"])
            c2.write(f"**Cuisine:** {r['cuisine']} | **Category:** {r['category']}")
            if c2.button("View Menu 🍽️", key=f"btn_{r['restaurant_id']}"):
                st.session_state.selected_rest = r
                st.session_state.page          = "Menu"
                st.rerun()

def menu_page():
    u   = st.session_state.user
    res = st.session_state.selected_rest

    sort_order = st.sidebar.radio("Sort Prices", ["Low to High","High to Low"])

    if st.button("← Back to Restaurants"):
        st.session_state.page = "Dashboard"
        st.rerun()

    st.title(f"🍴 {res['name']}")
    st.caption(f"{res['cuisine']} | {res['category']} | {u['city']}")
    st.divider()

    conn = get_db_connection()
    if not conn: return

    m_query = f"SELECT * FROM menu_items WHERE restaurant_id={res['restaurant_id']}"
    if u["city"] == "Ahmedabad":
        m_query += " AND category != 'Drink'"
    df_menu = pd.read_sql(m_query, conn)
    conn.close()

    for cat in ["Soup","Starter","Main Course","Dessert","Drink"]:
        df_cat = df_menu[df_menu["category"] == cat]
        if df_cat.empty: continue
        df_cat = df_cat.sort_values("price", ascending=(sort_order == "Low to High"))
        st.markdown(f"### {cat}s")
        st.markdown("---")
        for _, item in df_cat.iterrows():
            with st.container():
                cols = st.columns([3, 1, 1])
                veg_icon = "🟢" if item["is_veg"] else "🔴"
                cols[0].write(f"{veg_icon} **{item['item_name']}**")
                cols[0].caption(f"Allergy: {item['allergy_info'] or 'None'}")
                cols[1].write(f"₹{item['price']}")
                qty = cols[2].number_input("Qty", 1, 10, key=f"qty_{item['item_id']}")
                if cols[2].button("Add", key=f"add_{item['item_id']}", use_container_width=True):
                    try:
                        if (st.session_state.active_rest_id and
                                st.session_state.active_rest_id != res["restaurant_id"]):
                            raise VendorMismatchError("Cannot mix items from different restaurants.")
                        st.session_state.cart.append({
                            "id": item["item_id"], "name": item["item_name"],
                            "price": float(item["price"]), "qty": qty,
                            "total": float(item["price"]) * qty
                        })
                        st.session_state.active_rest_id   = res["restaurant_id"]
                        st.session_state.active_rest_name = res["name"]
                        st.toast(f"Added {item['item_name']} to cart!")
                    except VendorMismatchError as e:
                        st.error(e)
        st.write("")

    if st.session_state.cart:
        if st.sidebar.button("🛒 Go to Checkout"):
            st.session_state.page = "Cart"
            st.rerun()

def cart_page():
    st.title("🛒 Checkout")
    u  = st.session_state.user
    df = pd.DataFrame(st.session_state.cart)

    subtotal     = df["total"].sum()
    gst          = subtotal * 0.18
    service_fee  = subtotal * 0.05
    delivery_fee = 50.0
    tip          = st.slider("Add a Tip (₹)", 0, 200, 20)

    pay_method, valid, raw_card, cvv, _ = payment_widget("food")

    cod_fee   = 100.0 if pay_method == "COD" else 0.0
    total_amt = subtotal + gst + service_fee + delivery_fee + tip + cod_fee

    st.table(df[["name","qty","price","total"]])

    st.markdown(f"""
    | Component | Amount |
    |---|---|
    | Subtotal | ₹{subtotal:.2f} |
    | GST 18% | ₹{gst:.2f} |
    | Service 5% | ₹{service_fee:.2f} |
    | Delivery Fee | ₹{delivery_fee:.2f} |
    | Tip | ₹{tip:.2f} |
    | COD Fee | ₹{cod_fee:.2f} |
    | **Grand Total** | **₹{total_amt:.2f}** |
    """)

    if st.button("✅ Finalize Order", type="primary", use_container_width=True):
        try:
            if pay_method == "CARD":
                if len(raw_card.replace(" ", "")) != 16: raise CardPaymentError("Card must be 16 digits.")
                if len(cvv) != 3:                        raise CardPaymentError("Invalid CVV.")

            conn = get_db_connection()
            if conn:
                cursor = conn.cursor()
                sql = ("INSERT INTO orders (user_id,restaurant_id,subtotal,gst_amt,service_charge,"
                       "platform_fee,tip_amt,final_price,payment_method,status,cod_fee) "
                       "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,'Order Received',%s)")
                cursor.execute(sql, (u["user_id"], st.session_state.active_rest_id,
                                     subtotal, gst, service_fee, delivery_fee, tip,
                                     total_amt, pay_method, cod_fee))
                conn.commit()
                conn.close()

            st.session_state.summary = {
                "rest": st.session_state.active_rest_name,
                "sub": subtotal, "gst": gst, "svc": service_fee,
                "del": delivery_fee, "tip": tip, "total": total_amt, "df": df
            }
            st.session_state.page = "Tracking"
            st.rerun()

        except (CardPaymentError, UPIPaymentError, CODPaymentError) as e:
            st.error(f"Payment Validation Failed: {e}")
        except Exception as e:
            st.error(f"Unexpected error: {e}")

def my_bookings():
    u = st.session_state.user
    st.title("📜 My Food Order History")
    if st.button("← Back to Dashboard"):
        st.session_state.page = "Dashboard"
        st.rerun()

    conn = get_db_connection()
    if not conn: return
    query = """SELECT o.order_id, r.restaurant_id, r.name as Restaurant,
                      o.final_price as `Total Paid`, o.status as Status, o.order_date
               FROM orders o JOIN restaurants r ON o.restaurant_id=r.restaurant_id
               WHERE o.user_id=%s ORDER BY o.order_date DESC"""
    df_bookings = pd.read_sql(query, conn, params=(u["user_id"],))
    conn.close()

    if not df_bookings.empty:
        for _, row in df_bookings.iterrows():
            with st.container(border=True):
                col1, col2, col3 = st.columns([2,1,1])
                col1.write(f"**{row['Restaurant']}**")
                col1.caption(f"Date: {row['order_date']} | Total: ₹{row['Total Paid']}")
                col2.write(f"Status: {row['Status']}")
                if col3.button("Re-order 🔄", key=f"reorder_{row['order_id']}"):
                    st.session_state.cart           = []
                    st.session_state.active_rest_id = None
                    conn2 = get_db_connection()
                    if conn2:
                        cursor = conn2.cursor(dictionary=True)
                        cursor.execute("SELECT * FROM restaurants WHERE restaurant_id=%s",
                                       (row["restaurant_id"],))
                        st.session_state.selected_rest = cursor.fetchone()
                        conn2.close()
                    st.session_state.page = "Menu"
                    st.rerun()
    else:
        st.info("No orders yet.")

# ============================================================
#  ENTERTAINMENT HUB
# ============================================================
def entertainment_hub():
    u = st.session_state.user
    city = u["city"]

    sub = st.radio("Choose Experience", ["🎬 Movies", "🎤 Concerts", "🍽️ Fine Dining Reserve"],
                   horizontal=True)
    st.divider()

    if sub == "🎬 Movies":
        _movie_section(city)
    elif sub == "🎤 Concerts":
        _concert_section(city)
    else:
        _dining_reserve_section(city)

def _movie_section(user_city):
    st.image(SECTION_IMAGES["movie"], use_container_width=True)
    st.title("🎬 Cinema Experience")

    col1, col2, col3 = st.columns(3)
    with col1:
        city = st.selectbox("City", list(MOVIES.keys()), index=list(MOVIES.keys()).index(user_city))
    with col2:
        theaters = MOVIES.get(city, {})
        theater  = st.selectbox("Theater", list(theaters.keys()))
    with col3:
        movie_list = theaters.get(theater, {})
        movie      = st.selectbox("Movie", list(movie_list.keys()))
        show_time  = st.selectbox("Time Slot", movie_list.get(movie, []))

    st.divider()
    st.subheader("🪑 Select Your Seats")
    st.caption("Row A = Back / Premium  |  Row E = Front / Value")

    for r in ["A","B","C","D","E"]:
        price = MOVIE_PRICES.get(r, 0)
        cols  = st.columns(10)
        for i in range(1, 11):
            seat_name = f"{r}{i}"
            seat_id   = f"{city}|{theater}|{movie}|{show_time}|{seat_name}"
            is_booked   = seat_id in st.session_state.booked_seats
            is_selected = seat_id in st.session_state.selected_seats
            if is_booked:
                cols[i-1].button("⛔", key=seat_id, disabled=True, help="Sold Out")
            elif is_selected:
                if cols[i-1].button(f"🟡 {seat_name}", key=seat_id, help=f"Your Pick - ₹{price}"):
                    st.session_state.selected_seats.remove(seat_id)
                    st.rerun()
            else:
                if cols[i-1].button(f"🟢 {seat_name}", key=seat_id, help=f"Available - ₹{price}"):
                    st.session_state.selected_seats.add(seat_id)
                    st.rerun()

    total_price = sum(
        MOVIE_PRICES.get(s.split("|")[-1][0], 0) for s in st.session_state.selected_seats
    )

    if st.session_state.selected_seats:
        st.success(f"💰 Seat Total: ₹{total_price}")
        st.markdown("---")
        st.subheader("💳 Pay for Tickets")

        pay_method, valid, raw_card, cvv, _ = payment_widget("movie")

        if pay_method == "COD":
            total_price += 100
            st.warning("COD Surcharge ₹100 added.")

        st.metric("Grand Total", f"₹{total_price}")

        if st.button("✅ Confirm Movie Tickets", use_container_width=True, type="primary"):
            if not valid:
                st.error("Please fill valid payment details.")
            else:
                try:
                    if pay_method == "CARD":
                        if len(raw_card.replace(" ","")) != 16: raise CardPaymentError("Card must be 16 digits.")
                        if len(cvv) != 3: raise CardPaymentError("Invalid CVV.")
                    st.session_state.booked_seats.update(st.session_state.selected_seats)
                    details = ", ".join([s.split("|")[-1] for s in st.session_state.selected_seats])
                    st.session_state.dis_history.append({
                        "type":   "🎬 Movie",
                        "detail": f"{movie} at {theater} ({show_time}) — Seats: {details}",
                        "cost":   f"₹{total_price}",
                        "date":   str(date.today())
                    })
                    st.session_state.selected_seats.clear()
                    st.balloons()
                    st.success("🎉 Booking Successful! Enjoy the movie!")
                    st.rerun()
                except (CardPaymentError, UPIPaymentError) as e:
                    st.error(f"Payment Error: {e}")

def _concert_section(user_city):
    st.image(SECTION_IMAGES["concert"], use_container_width=True)
    st.title("🎤 Live Events")

    col1, col2 = st.columns(2)
    with col1:
        city       = st.selectbox("City", list(CONCERTS.keys()), index=list(CONCERTS.keys()).index(user_city))
        venue      = st.selectbox("Venue", list(CONCERTS[city].keys()))
    with col2:
        concert    = st.selectbox("Event", CONCERTS[city][venue])
        event_date = st.date_input("Event Date", min_value=date.today())

    st.markdown("### 🎫 Choose Your Experience")
    total_concert_cost = 0
    selections         = []

    for stand, price in CONCERT_STANDS.items():
        c1, c2, c3 = st.columns([2, 1, 1])
        c1.markdown(f"**{stand}**")
        c2.write(f"₹{price}")
        qty = c3.number_input("Tickets", 0, 10, key=f"con_{stand}")
        if qty > 0:
            total_concert_cost += qty * price
            selections.append(f"{stand} x{qty}")

    if total_concert_cost > 0:
        st.metric("Ticket Total", f"₹{total_concert_cost}")
        st.markdown("---")
        st.subheader("💳 Pay for Tickets")

        pay_method, valid, raw_card, cvv, _ = payment_widget("concert")

        if pay_method == "COD":
            total_concert_cost += 100
            st.warning("COD Surcharge ₹100 added.")

        st.metric("Grand Total", f"₹{total_concert_cost}")

        if st.button("✅ Finalize Concert Booking", type="primary", use_container_width=True):
            if not valid:
                st.error("Please fill valid payment details.")
            else:
                try:
                    if pay_method == "CARD":
                        if len(raw_card.replace(" ","")) != 16: raise CardPaymentError("Card must be 16 digits.")
                        if len(cvv) != 3: raise CardPaymentError("Invalid CVV.")
                    st.session_state.dis_history.append({
                        "type":   "🎤 Concert",
                        "detail": f"{concert} at {venue} ({', '.join(selections)})",
                        "cost":   f"₹{total_concert_cost}",
                        "date":   str(event_date)
                    })
                    st.balloons()
                    st.success("🎉 Tickets confirmed! Sent to your registered email.")
                except (CardPaymentError, UPIPaymentError) as e:
                    st.error(f"Payment Error: {e}")

def _dining_reserve_section(user_city):
    st.image(SECTION_IMAGES["restaurant"], use_container_width=True)
    st.title("🍽️ Fine Dining Reservation")

    city = st.selectbox("City", ["Ahmedabad","Mumbai","Delhi"],
                        index=["Ahmedabad","Mumbai","Delhi"].index(user_city))

    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT name, cuisine, image_url FROM restaurants WHERE city=%s", (city,))
        db_data = cursor.fetchall()
        conn.close()
    else:
        db_data = []

    if not db_data:
        st.warning("No restaurants found for this city.")
        return

    rest_names  = [r["name"] for r in db_data]
    sel_name    = st.selectbox("Choose Restaurant", rest_names)
    sel_rest    = next((r for r in db_data if r["name"] == sel_name), None)

    if sel_rest:
        st.image(sel_rest["image_url"], use_container_width=True,
                 caption=f"{sel_rest['name']} — {sel_rest['cuisine']}")

        st.subheader(f"Reserve a Table at {sel_rest['name']}")
        c1, c2 = st.columns(2)
        d    = c1.date_input("Date", min_value=date.today())
        t    = c2.time_input("Time", value=dtime(20, 0))
        ppl  = st.slider("Guests", 1, 15, 2)
        g_name = st.text_input("Guest Name", st.session_state.user["name"])

        if st.button("✅ Confirm Reservation", use_container_width=True, type="primary"):
            st.session_state.dis_history.append({
                "type":       "🍽️ Dining",
                "detail":     sel_rest["name"],
                "guest_name": g_name,
                "people":     ppl,
                "cost":       "Pay at Venue",
                "date":       f"{d} at {t}"
            })
            st.success(f"Table for {ppl} reserved at {sel_rest['name']} on {d} at {t}! 🎉")

def entertainment_history():
    st.title("📜 My Entertainment Bookings")
    if st.button("← Back"):
        st.session_state.page = "Dashboard"
        st.rerun()

    if not st.session_state.dis_history:
        st.info("No entertainment bookings yet. Start exploring!")
        return

    for i, item in enumerate(reversed(st.session_state.dis_history)):
        with st.expander(f"{item['type']} — {item['detail']}"):
            st.write(f"📍 **Detail:** {item['detail']}")
            st.write(f"👤 **Guest:** {item.get('guest_name', 'N/A')}")
            st.write(f"📅 **Date:** {item['date']}")
            st.write(f"💰 **Amount:** {item['cost']}")
            invoice_text = f"""
========================================
TRISERVE - ENTERTAINMENT BOOKING INVOICE
========================================
Type     : {item['type']}
Detail   : {item['detail']}
Guest    : {item.get('guest_name','Valued Customer')}
Date     : {item['date']}
Amount   : {item['cost']}
========================================
Thank you for booking with TriServe!
"""
            st.download_button("📥 Download Invoice", data=invoice_text,
                               file_name=f"Invoice_Ent_{i}.txt",
                               mime="text/plain", key=f"dl_ent_{i}")

# ============================================================
#  INSTAMARKET
# ============================================================
def instamarket_page():
    u = st.session_state.user

    st.title("🛒 InstaMarket")
    h1, h2, h3 = st.columns([5, 1, 1])
    with h2:
        if st.button("🧺 Cart"):
            st.session_state.zm_page = "cart"
    with h3:
        if st.button("📜 History"):
            st.session_state.zm_page = "history"

    if st.button("← Back to Dashboard"):
        st.session_state.page = "Dashboard"
        st.rerun()

    st.subheader("Categories")
    cats      = ["All"] + list(PRODUCTS.keys())
    cat_cols  = st.columns(4)
    for i, cat in enumerate(cats):
        if cat_cols[i % 4].button(cat, key=f"zm_cat_{i}"):
            st.session_state.zm_selected_cat = cat
            st.session_state.zm_page         = "shop"

    st.divider()

    zm_pg = st.session_state.zm_page

    if zm_pg == "shop":
        show = (PRODUCTS if st.session_state.zm_selected_cat == "All"
                else {st.session_state.zm_selected_cat: PRODUCTS[st.session_state.zm_selected_cat]})

        for category, items in show.items():
            st.markdown(f"### {category}")
            for item, base_price in items.items():
                a_img, a, b, c, q, d = st.columns([1, 2, 1.5, 2, 1.5, 1.5])
                a_img.image(ITEM_IMGS.get(item, "https://via.placeholder.com/150"), width=60)
                a.write(item)
                key = f"{category}_{item}"

                if category in GROCERY_CATS:
                    w     = c.selectbox("Weight", ["250g","500g","1kg","2kg"], key=key+"w")
                    price = int(base_price * WEIGHT_MUL[w])
                    name  = f"{item} {w}"
                elif category == DRINK_CAT:
                    v     = c.selectbox("Volume", ["250ml","500ml","1L","2L"], key=key+"v")
                    price = int(base_price * DRINK_MUL[v])
                    name  = f"{item} {v}"
                elif category in CLOTHING_CATS:
                    s     = c.selectbox("Size", ["S","M","L","XL"], key=key+"s")
                    price = int(base_price * SIZE_MUL[s])
                    name  = f"{item} Size {s}"
                else:
                    price = base_price
                    name  = item
                    c.write("—")

                b.write(f"₹{price}")
                qty_val = q.number_input("Qty", min_value=1, max_value=10, step=1, key=key+"qty")

                if d.button("Add", key="add"+key):
                    if name in st.session_state.zm_cart:
                        st.session_state.zm_cart[name]["qty"] += qty_val
                    else:
                        st.session_state.zm_cart[name] = {"price": price, "qty": qty_val}
                    st.toast(f"Added {name} to basket!")

    elif zm_pg == "cart":
        st.header("🧺 Your Basket")
        if not st.session_state.zm_cart:
            st.warning("Basket is empty.")
        else:
            subtotal = sum(d["price"] * d["qty"] for d in st.session_state.zm_cart.values())
            st.divider()

            coupon = st.text_input("Coupon Code (Try: SAVE10)")
            if st.button("Apply Code"):
                code = coupon.upper()
                if code in ZIPMART_COUPON:
                    st.session_state.zm_discount_pct = ZIPMART_COUPON[code]
                    st.success(f"{ZIPMART_COUPON[code]}% Coupon Applied! ✨")
                else:
                    st.session_state.zm_discount_pct = 0
                    st.error("Invalid Coupon Code")

            discount_rupees = (subtotal * st.session_state.zm_discount_pct) // 100
            after_discount  = subtotal - discount_rupees
            shipping        = 0 if after_discount >= 199 else 30
            final_total     = after_discount + shipping

            for item, data in st.session_state.zm_cart.items():
                st.write(f"{item} → ₹{data['price']} × {data['qty']} = ₹{data['price']*data['qty']}")

            st.divider()
            st.write(f"Items Subtotal : ₹{subtotal}")
            if discount_rupees > 0:
                st.write(f"✨ **Coupon Discount: -₹{discount_rupees}**")
            st.write(f"Delivery Charge: ₹{shipping}")
            st.subheader(f"Total Payable: ₹{final_total}")

            if st.button("💳 Proceed to Payment"):
                st.session_state.zm_page = "payment"
        if st.button("← Back to Shop"):
            st.session_state.zm_page = "shop"

    elif zm_pg == "payment":
        st.header("💳 Payment")

        sub         = sum(v["price"]*v["qty"] for v in st.session_state.zm_cart.values())
        d_amt       = (sub * st.session_state.zm_discount_pct) // 100
        after_disc  = sub - d_amt
        shipping    = 0 if after_disc >= 199 else 30
        final_cost  = after_disc + shipping

        method, valid, raw_card, cvv, _ = payment_widget("market")

        if method == "COD":
            final_cost += 100
            st.warning("₹100 COD surcharge added.")

        st.metric("Order Total", f"₹{final_cost}")

        if st.button("✅ Confirm Order", type="primary", use_container_width=True):
            if not valid:
                st.error("Please fill valid payment details.")
            else:
                try:
                    if method == "CARD":
                        if len(raw_card.replace(" ","")) != 16: raise CardPaymentError("Card must be 16 digits.")
                        if len(cvv) != 3: raise CardPaymentError("Invalid CVV.")

                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO instamarket_orders (customer_id, total_price) VALUES (%s, %s)",
                        (u["user_id"], final_cost)
                    )
                    conn.commit()
                    conn.close()

                    st.session_state.zm_orders.append({
                        "id":    len(st.session_state.zm_orders) + 1,
                        "date":  datetime.now().strftime("%d %b, %H:%M"),
                        "total": final_cost,
                        "items": dict(st.session_state.zm_cart)
                    })
                    st.session_state.zm_cart.clear()
                    st.session_state.zm_discount_pct = 0
                    st.session_state.zm_page         = "confirmed"
                    st.rerun()

                except (CardPaymentError, UPIPaymentError) as e:
                    st.error(f"Payment Error: {e}")

    elif zm_pg == "confirmed":
        st.success("🎉 Order Placed Successfully!")
        st.balloons()
        if st.session_state.zm_delivery_time is None:
            st.session_state.zm_delivery_time = random.randint(5, 15)

        timer_ui = st.empty()
        secs     = st.session_state.zm_delivery_time * 60
        while secs > 0:
            m, s = divmod(secs, 60)
            timer_ui.info(f"🚴 Delivery Arriving in: {m:02d}:{s:02d}")
            time.sleep(1)
            secs -= 1
            if st.session_state.zm_page != "confirmed":
                break

        if st.button("🛒 Shop Again"):
            st.session_state.zm_delivery_time = None
            st.session_state.zm_page          = "shop"
            st.rerun()

    elif zm_pg == "history":
        st.header("📜 Market Order History")
        conn = get_db_connection()
        if not conn:
            st.error("Could not connect to database.")
        else:
            query = """
                    SELECT order_id    AS `Order ID`, 
                           total_price AS `Total (₹)`, 
                           order_date  AS `Date`
                    FROM instamarket_orders
                    WHERE customer_id = %s
                    ORDER BY order_date DESC 
                    """
            df_db = pd.read_sql(query, conn, params=(u["user_id"],))
            conn.close()
            # Combine DB orders + current session orders (avoid duplicates)
            # Session orders won't have order_id from DB so we show DB as source of truth
            if df_db.empty and not st.session_state.zm_orders:
                st.info("No market orders yet.")
            else:
                # ── Metrics ───────────────────────────────────────────
                total_orders = len(df_db)
                total_spent = df_db["Total (₹)"].sum() if not df_db.empty else 0
                avg_order = df_db["Total (₹)"].mean() if not df_db.empty else 0
                col1, col2, col3 = st.columns(3)
                col1.metric("Total Orders", total_orders)
                col2.metric("Total Spent", f"₹{total_spent:,.2f}")
                col3.metric("Average Order Value", f"₹{avg_order:,.2f}")
                st.divider()
                # ── Bar Chart ─────────────────────────────────────────
                if not df_db.empty:
                    st.subheader("📊 Spending Per Order")
                    fig, ax = plt.subplots(figsize=(8, 4))
                    ax.bar(
                        df_db["Order ID"].astype(str),
                        df_db["Total (₹)"],
                        color="teal",
                        alpha=0.85,
                        edgecolor="white"
                    )
                    ax.set_ylabel("Order Cost (₹)")
                    ax.set_xlabel("Order ID")
                    ax.set_title(f"InstaMarket — Spending History for {u['name']}")
                    ax.tick_params(axis='x', rotation=45)
                    plt.tight_layout()
                    st.pyplot(fig)
                    st.divider()

                    # ── Order Cards from DB ───────────────────────────

                    st.subheader("🧾 Past Orders")

                    for _, row in df_db.iterrows():
                        with st.container(border=True):
                            c1, c2 = st.columns([3, 1])
                            c1.write(f"🛒 **Order #{int(row['Order ID'])}**")
                            c1.caption(f"🗓️ {str(row['Date'])[:16]}")
                            c2.metric("Amount", f"₹{row['Total (₹)']:,.2f}")
                else:
                    st.info("No past orders found in database.")

        if st.button("← Back"):
            st.session_state.zm_page = "shop"

# ============================================================
#  LOGOUT
# ============================================================
def logout():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# ============================================================
#  APP ENTRY POINT + PAGE ROUTING
# ============================================================
st.set_page_config(
    page_title="TriServe",
    page_icon="🎯",
    layout="wide"
)

init_session()

# ── Sidebar: Logout button ─────────────────────────────────
if st.session_state.page != "Login":
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Logout", use_container_width=True):
        logout()

# ── Sidebar: entertainment history shortcut ────────────────
if (st.session_state.page not in ["Login", "AdminPanel"]
        and st.session_state.dis_history):
    if st.sidebar.button("🎟️ Entertainment History"):
        st.session_state.page = "EntHistory"
        st.rerun()

# ── Router ─────────────────────────────────────────────────
page = st.session_state.page

if page == "Login":
    auth_page()

elif page == "AdminPanel":
    admin_panel()

elif page == "Dashboard":
    dashboard()

elif page == "Menu":
    menu_page()

elif page == "Cart":
    cart_page()

elif page == "Tracking":
    tracking_page()

elif page == "MyBookings":
    my_bookings()

elif page == "InstaMarket":
    instamarket_page()

elif page == "EntHistory":
    entertainment_history()
