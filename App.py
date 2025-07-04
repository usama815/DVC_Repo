import streamlit as st
import pandas as pd
import requests
import json
import streamlit as st
import requests
import webbrowser
from urllib.parse import urlencode, parse_qs
import http.server
import socketserver
import threading

CLIENT_ID = "ABFzT3cgHtHGFkE73WqW2Q3mX73o1NUtj9CgB5ugokhkFIGqDp"
CLIENT_SECRET = "XdQbFkKnSM1SKylRlKBURO6pD99DSd5ry6ePl79l"
REDIRECT_URI = "http://localhost:8000/callback"
SCOPE = "com.intuit.quickbooks.accounting"

AUTH_URL = "https://appcenter.intuit.com/connect/oauth2"
TOKEN_URL = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"

# Step 1: User clicks to connect
st.title("Intuit OAuth2.0 with Streamlit")
if "access_token" not in st.session_state:
    
    if st.button("Connect with QuickBooks"):
        query_params = {
            "client_id": CLIENT_ID,
            "redirect_uri": REDIRECT_URI,
            "response_type": "code",
            "scope": SCOPE,
            "state": "9iAu5cC8PHlZRGax2v8fMUjHIbr0sl"
            
        }
        auth_redirect_url = f"{AUTH_URL}?{urlencode(query_params)}"
        webbrowser.open(auth_redirect_url)

    # Step 2: Local server handles callback
    class Handler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            code = parse_qs(self.path.split("?")[1]).get("code", [None])[0]
            if code:
                st.session_state["auth_code"] = code
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"Authorization complete. Go back to Streamlit app.")
            else:
                self.send_response(400)
                self.end_headers()

    def run_server():
        with socketserver.TCPServer(("", 8000), Handler) as httpd:
            httpd.handle_request()

    threading.Thread(target=run_server).start()

# Step 3: Exchange code for token
if "auth_code" in st.session_state and "access_token" not in st.session_state:
    data = {
        "grant_type": "authorization_code",
        "code": st.session_state["auth_code"],
        "redirect_uri": REDIRECT_URI
    }
    headers = {
        "Authorization": f"Basic {requests.auth._basic_auth_str(CLIENT_ID, CLIENT_SECRET)}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    response = requests.post(TOKEN_URL, headers=headers, data=data)
    if response.status_code == 200:
        tokens = response.json()
        st.session_state["access_token"] = tokens["access_token"]
        st.success("Authorization successful!")
    else:
        st.error("Failed to get access token.")
    if "access_token" in st.session_state:
        st.write("Access Token:", st.session_state["access_token"])
        st.title("📤 Upload Journal Excel File")
def generate_payload(df):
    journal_lines = []
    for _, row in df.iterrows():
        if pd.notna(row.get("Account")) and pd.notna(row.get("amount")):
            journal_lines.append({
                "DetailType": "JournalEntryLineDetail",
                "Amount": abs(float(row["amount"])),
                "JournalEntryLineDetail": {
                    "PostingType": "Debit" if row["amount"] >= 0 else "Credit",
                    "AccountRef": {
                        "name": row["Account"],
                        "value": "1"
                        }
                        },
                        "Description": row.get("Description", "")
                        })
            payload = {
                "Line": journal_lines,
                "TxnDate": "2025-03-31",
                "PrivateNote": "Posted via Streamlit App"
                }
            return payload
uploaded_file = st.file_uploader("Upload Excel (.xlsx)", type=["xlsx"])
if uploaded_file:
    df = pd.read_excel(uploaded_file)
    st.success("✅ File uploaded successfully!")
    st.subheader("📊 Data Preview")
    st.dataframe(df)
def loadpayloadsilently():
    try:
        with open("payload.json", "r") as file:
            return json.load(file)
    except Exception as e:
        return None
    payload = load_payload_silently()
    if payload:
        if st.button("Send to QuickBooks"):
            st.success("✅ Sent silently!")
        else:
            st.warning("📂 payload.json file not found.")
def save_payload_to_file(payload, filename="payload.json"):
    try:
        with open(filename, "w") as f:
            json.dump(payload, f, indent=4)
        print(f"✅ Payload saved to {filename}")
    except Exception as e:
        print(f"❌ Error saving payload: {e}")
        save_payload_to_file(payload)
        df = pd.read_excel(uploaded_file)
        payload = generate_payload(df)
        save_payload_to_file(payload, "payload.json")
# QuickBooks API endpoint for company info
REALM_ID = "9341454878247158"  # Sandbox ya production account ka
API_URL = f"https://sandbox-quickbooks.api.intuit.com/v3/company/{REALM_ID}/companyinfo/{REALM_ID}"

if "access_token" in st.session_state:
    headers = {
        "Authorization": f"Bearer {st.session_state['access_token']}",
        "Accept": "application/json"
    }

    response = requests.get(API_URL, headers=headers)

    if response.status_code == 200:
        company_data = response.json()
        st.write("Company Information:")
        st.json(company_data)
    else:
        st.error("QuickBooks API call failed")


# 🔹 Step 4: Send to QuickBooks
if st.button("🚀 Push to QuickBooks"):
    try:
        access_token = st.secrets["ACCESS_TOKEN"]
        realm_id = st.secrets["Realm_ID"]

        url = f"https://sandbox-quickbooks.api.intuit.com/v3/company/{realm_id}/journalentry"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        response = requests.post(url, json=payload, headers=headers)

        if response.status_code in [200, 201]:
            st.success("🎉 Successfully posted to QuickBooks!")
            st.json(response.json())
        else:
            st.error(f"❌ Failed to post! Status: {response.status_code}")
            st.json(response.json())

    except Exception as e:
        st.error(f"🔐 Error sending to QBO: {e}")
url = f"https://sandbox-quickbooks.api.intuit.com/v3/company/{REALM_ID}/query"