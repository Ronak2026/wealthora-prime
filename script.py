import streamlit as st
import requests
import pandas as pd
import time
import re
from datetime import date

# --- PAGE CONFIG ---
st.set_page_config(page_title="WealthoraPrime Pannel", layout="wide", page_icon="💎")

# --- SECRETS & HEADERS ---
MAUTH_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1aWQiOiJNX0xWTkJVS0xTMyIsInJvbGUiOiJ1c2VyIiwiYWNjZXNzX3BhdGgiOlsiL2Rhc2hib2FyZCJdLCJleHBpcnkiOjE3Nzg0MDI2MTAsImNyZWF0ZWQiOjE3NzgzMTYyMTAsIjJvbzkiOiJNc0giLCJleHAiOjE3Nzg0MDI2MTAsImlhdCI6MTc3ODMxNjIxMCwic3ViIjoiTV9MVk5CVUtMUzMifQ.apTv8gomx7SX_A4x2k-NrYQyOSn7GdHXTzWLCJGTXL4"
CF_CLEARANCE = "kpdd3VEcmRrgm805_u0Ask4SBMCcM5Z2aGxvHbgEgfA-1778391243-1.2.1.1-16bL27.bZdY3ubAt3xboxUDGtPNuRy8aaRhD87O2V1sQTeTs6kQb8zDYva.teu8fZ8Te.H6heSa6P_6_.o7yBcz9qFLbJHnfxRoOiaOja5FIB8m5JPCBOBhqd4M2DqkzBhC7ARbOgt0_oYHw_d1NNEQQqkFOIn3w1_sYtmJru4Ko4oMpMk9vQMS.pY4wZ8WsHMQbG3x5tbXXTdra4tUpgX1t0.kQ8IAaUDlYdv4RdlwJi2VTBwjN1HuMKMm_NbtGMv9qFsXRhhyQfawly6b9pHO1Hoziq533TXmFGOTzSH3FX_jWDZVvri_pbF8tFySGxagHqbH0NOYo6MvMptFSSA"

API_BASE = "https://x.mnitnetwork.com/mapi/v1/mdashboard"

HEADERS = {
    "accept": "application/json, text/plain, */*",
    "content-type": "application/json",
    "mauthtoken": MAUTH_TOKEN,
    "cf_clearance": CF_CLEARANCE,
    "cookie": f"mauthtoken={MAUTH_TOKEN}; cf_clearance={CF_CLEARANCE}",
    "origin": "https://x.mnitnetwork.com",
    "referer": "https://x.mnitnetwork.com/mdashboard/getnum"
}

# --- SESSION STATE ---
if 'last_search_result' not in st.session_state:
    st.session_state.last_search_result = None
if 'search_msg' not in st.session_state:
    st.session_state.search_msg = ""

# --- HELPERS ---

def safe_fetch(url, method="GET", json_body=None):
    try:
        if method == "POST":
            res = requests.post(url, headers=HEADERS, json=json_body, timeout=10)
        else:
            res = requests.get(url, headers=HEADERS, timeout=10)
        return res.json() if res.status_code == 200 else None
    except:
        return None

def extract_otp(text):
    """Extracts OTP patterns (digits or digit-digit)"""
    if not text: return ""
    match = re.search(r'(\d{3,6}[-\s]?\d{0,3})', str(text))
    return match.group(1) if match else ""

def get_range_id(num_str):
    """23276573851 -> 23276573XXX"""
    if not num_str: return "Unknown"
    clean = re.sub(r'\D', '', str(num_str))
    return (clean[:-3] + "XXX") if len(clean) > 3 else clean

def safe_df(data, cols):
    if not data: return pd.DataFrame(columns=cols.values())
    df = pd.DataFrame(data)
    valid = [k for k in cols if k in df.columns]
    return df[valid].rename(columns=cols)

# --- UI HEADER ---
st.title("💎 WealthoraPrime Pannel")
st.markdown("### Real-time SMS & OTP Monitor")

# SEARCH SECTION
with st.container():
    c1, c2, c3 = st.columns([6, 2, 4])
    with c1:
        range_input = st.text_input("Enter Range ID", placeholder="e.g., 23762195xxxxxx")
    with c2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔍 Get Number", type="primary", use_container_width=True):
            if range_input:
                res = safe_fetch(f"{API_BASE}/getnum/number", "POST", {"range": range_input, "is_national": False, "remove_plus": False})
                if res and res.get('meta',{}).get('code') == 200:
                    d = res['data']
                    st.session_state.last_search_result = [d]
                    st.session_state.search_msg = f"✅ {res.get('message')}: {d.get('number','')}"
                    st.rerun()
                else:
                    st.session_state.search_msg = f"❌ Error: {res.get('message', 'Fail') if res else 'Timeout'}"
                    st.session_state.last_search_result = None
                    st.rerun()
            else:
                st.warning("Input Range ID")
    
    with c3:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.session_state.search_msg:
            st.success(st.session_state.search_msg) if "success" in st.session_state.search_msg.lower() or "allocated" in st.session_state.search_msg.lower() else st.error(st.session_state.search_msg)

st.markdown("---")

# --- DATA FETCHING ---
console_data = safe_fetch(f"{API_BASE}/console/info")
numbers_data = safe_fetch(f"{API_BASE}/getnum/info?date=2026-05-10&page=1&search=&status=")

all_nums = numbers_data.get('data', {}).get('numbers', []) if numbers_data else []
pending_raw = [x for x in all_nums if str(x.get('status','')).lower() == 'pending']
success_raw = [x for x in all_nums if str(x.get('status','')).lower() == 'success']

# Inject Search Result to Pending
if st.session_state.last_search_result:
    new_n = st.session_state.last_search_result[0].get('number')
    if not any(x.get('number') == new_n for x in pending_raw):
        pending_raw = st.session_state.last_search_result + pending_raw

# --- STATS LOGIC ---

# 1. Top Ranges Stats (From Number Field)
stats_range_list = []
for item in success_raw:
    stats_range_list.append({
        "Range ID": get_range_id(item.get('number')),
        "Country": item.get('country', 'Unknown'),
        "Total Count": 1,
        "Last OTP": extract_otp(item.get('message'))
    })
df_stats_range = pd.DataFrame(stats_range_list)
top_ranges = pd.DataFrame()
if not df_stats_range.empty:
    top_ranges = df_stats_range.groupby(["Range ID", "Country"]).agg(
        Total_Success=('Total Count', 'sum'),
        Sample_OTP=('Last OTP', 'last')
    ).reset_index().sort_values("Total_Success", ascending=False).head(10)

# 2. High Traffic By App (From full_number / App Name Field)
# We assume full_number or a specific app field contains the App Name (e.g., "Facebook")
app_traffic_list = []
for item in success_raw:
    # Try to get app name. In your JSON example, 'full_number' was "Facebook". 
    # If API returns actual number there, we might need to rely on message parsing or another field.
    # Based on your request: "app {full_number}"
    app_name = item.get('full_number') 
    if not app_name or app_name.replace(" ","").isdigit(): # If it's actually a number, mark as Unknown/Other
        # Fallback: Try to guess from message if possible, otherwise "Detected"
        app_name = item.get('message', '').split()[0] if item.get('message') else "Unknown App"
    
    app_traffic_list.append({
        "App Name": app_name,
        "Target Range": get_range_id(item.get('number')),
        "Count": 1,
        "Last Message": item.get('message', "")[:50] + "..." # Truncate long messages
    })

df_app_raw = pd.DataFrame(app_traffic_list)
top_apps = pd.DataFrame()
if not df_app_raw.empty:
    top_apps = df_app_raw.groupby(["App Name", "Target Range"]).agg(
        Total_Hits=('Count', 'sum'),
        Last_SMS_Sample=('Last Message', 'last')
    ).reset_index().sort_values("Total_Hits", ascending=False).head(15) # Top 15 Apps


# --- RENDER UI ---

# COL MAPS
map_pen = {"number":"📱 Number","country":"🌍 Country","operator":"📡 Operator","status":"📌 Status","last_activity":"⏰ Activity"}
map_con = {"time":"⏰ Time","app_name":"📱 App","number":"☎️ Num","range":"📍 Range","country":"🌍 Country","sms":"💬 SMS"}

# 1. PENDING TABLE
st.subheader("🟡 Pending Allocation")
st.dataframe(safe_df(pending_raw, map_pen), use_container_width=True)

# 2. SUCCESS TABLE WITH OTP
st.subheader("🟢 Success & Live OTP")
if success_raw:
    df_s = pd.DataFrame(success_raw)
    df_s['otp_code'] = df_s['message'].apply(extract_otp)
    # Reorder
    disp = ["number","country","operator","otp_code","message","last_activity"]
    df_s = df_s[[c for c in disp if c in df_s.columns]].rename(columns={
        "number":"📱 Number","country":"🌍 Country","operator":"📡 Operator",
        "otp_code":"🔐 Code","message":"💬 Full Message","last_activity":"⏰ Time"
    })
    st.dataframe(df_s, use_container_width=True)
else:
    st.info("No success records.")

# 3. STATISTICS GRID (Responsive Columns)
st.subheader("📊 Analytics Dashboard")
col_stat1, col_stat2 = st.columns(2)

with col_stat1:
    st.markdown("**🏆 Top 10 High Traffic Ranges**")
    if not top_ranges.empty:
        st.dataframe(top_ranges, use_container_width=True)
    else:
        st.info("No range data.")

with col_stat2:
    st.markdown("**📱 High Traffic by App**")
    if not top_apps.empty:
        st.dataframe(top_apps, use_container_width=True)
    else:
        st.info("No app data.")

# 4. CONSOLE
st.subheader("🖥️ System Console Logs")
logs = console_data.get('data', {}).get('logs', [])[:50] if console_data else []
st.dataframe(safe_df(logs, map_con), use_container_width=True)

# --- FOOTER ---
yr = date.today().year
st.markdown("---")
st.markdown(f"""
<div style='text-align:center; padding:20px; color:#888; font-size:14px; border-top:1px solid #eee'>
    <strong>© {yr} WealthoraPrime Pannel</strong><br>
    Developed with ❤️ by <strong>Aryan Rathod 🇮🇳</strong><br>
    Join Channel: <a href='https://t.me/filesbykaiiddo' target='_blank'>filesbykaiiddo.t.me</a>
</div>
""", unsafe_allow_html=True)

# AUTO REFRESH
time.sleep(2)
st.rerun()