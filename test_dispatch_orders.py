import streamlit as st
import requests
from lxml import etree
from datetime import datetime, timedelta
import time

# Set the page title
st.set_page_config(page_title="Client Web Service Damas", layout="wide")

# Hardcoded credentials
ACCESS_CODE_1 = "electro1"
ACCESS_CODE_2 = "giurgiu2012"

# Function to get the current timestamp
def get_current_timestamp():
    now = datetime.utcnow()
    expires = now + timedelta(hours=1)
    return now.strftime("%Y-%m-%dT%H:%M:%SZ"), expires.strftime("%Y-%m-%dT%H:%M:%SZ")

# Function to send SOAP request for dispatch orders
def get_dispatch_orders(date_from, date_to):
    created, expires = get_current_timestamp()
    
    # SOAP request XML
    soap_request = f"""
    <soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:wse="http://markets.transelectrica.ro/wse">
        <soap:Header>
            <wsse:Security soap:mustUnderstand="true" xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">
                <wsse:UsernameToken wsu:Id="username_token_id">
                    <wsse:Username>{ACCESS_CODE_1}</wsse:Username>
                    <wsse:Password Type="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-username-token-profile-1.0#PasswordText">{ACCESS_CODE_2}</wsse:Password>
                </wsse:UsernameToken>
                <wsu:Timestamp wsu:Id="timestamp_id">
                    <wsu:Created>{created}</wsu:Created>
                    <wsu:Expires>{expires}</wsu:Expires>
                </wsu:Timestamp>
            </wsse:Security>
        </soap:Header>
        <soap:Body>
            <wse:RunSynchronous>
                <wse:Input>
                    <wse:FID>DISPATCH_ORDERS_MANUAL_DOWNLOAD_XML_OUT</wse:FID>
                    <wse:Parameters>
                        <wse:DateParam Name="DateFrom">{date_from}</wse:DateParam>
                        <wse:DateParam Name="DateTo">{date_to}</wse:DateParam>
                    </wse:Parameters>
                </wse:Input>
            </wse:RunSynchronous>
        </soap:Body>
    </soap:Envelope>
    """

    headers = {
        'Content-Type': 'application/soap+xml;charset=UTF-8;action="http://markets.transelectrica.ro/wse/RunSynchronous"',
    }

    # Send the SOAP request
    response = requests.post("https://newmarkets.transelectrica.ro/usy-durom-wsendpointg01/00121002300000000000000000000100/ws", data=soap_request, headers=headers)

    if response.status_code == 200:
        return response.content
    else:
        return None

# Main section
st.title("Client Web Service Damas")
st.write("Aplicația permite interacțiunea cu Web Service-ul Damas pentru a obține ordine de dispecer.")

# Sidebar inputs for date range
st.sidebar.header("Selectați Intervalul de Date")
date_from = st.sidebar.date_input("Data de început", value=datetime.utcnow() - timedelta(days=1))
date_to = st.sidebar.date_input("Data de sfârșit", value=datetime.utcnow())

# Placeholder for dispatch orders
dispatch_orders_placeholder = st.empty()

def refresh_data():
    response = get_dispatch_orders(date_from, date_to)
    if response:
        # Parse the XML response
        tree = etree.fromstring(response)
        dispatch_orders = etree.tostring(tree, pretty_print=True).decode("utf-8")
        dispatch_orders_placeholder.success("Ordinele de Dispecer au fost obținute cu succes!")
        dispatch_orders_placeholder.code(dispatch_orders, language="xml")
    else:
        dispatch_orders_placeholder.error("Nu exista ordine de dispecer pentru intervalul selectat.")

# Button to trigger the SOAP request manually
if st.sidebar.button("Obține Ordine de Dispecer"):
    refresh_data()

# Auto-refresh every 30 seconds
while True:
    refresh_data()
    time.sleep(30)
    st.experimental_rerun()


