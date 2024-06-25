import streamlit as st
import requests
from lxml import etree
from datetime import datetime, timedelta

# Set the page title
st.title("Get Current Date and Time from Damas Web Service")

# Hardcoded credentials
ACCESS_CODE_1 = "electro1"
ACCESS_CODE_2 = "giurgiu2012"

# Function to get the current timestamp
def get_current_timestamp():
    now = datetime.utcnow()
    expires = now + timedelta(days=1)
    return now.strftime("%Y-%m-%dT%H:%M:%SZ"), expires.strftime("%Y-%m-%dT%H:%M:%SZ")

# Function to send SOAP request
def get_current_datetime():
    created, expires = get_current_timestamp()
    
    # SOAP request XML
    soap_request = f"""
    <soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:wse="http://markets.transelectrica.ro/wse">
      <soap:Header>
        <wsse:Security soap:mustUnderstand="true" xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">
          <wsse:UsernameToken wsu:Id="UsernameToken-1">
            <wsse:Username>{ACCESS_CODE_1}</wsse:Username>
            <wsse:Password Type="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-username-token-profile-1.0#PasswordText">{ACCESS_CODE_2}</wsse:Password>
          </wsse:UsernameToken>
          <wsu:Timestamp wsu:Id="Timestamp-1">
            <wsu:Created>{created}</wsu:Created> 
            <wsu:Expires>{expires}</wsu:Expires> 
          </wsu:Timestamp>
        </wsse:Security>
      </soap:Header>
      <soap:Body>
        <wse:GetActualDateTime/>
      </soap:Body>
    </soap:Envelope>
    """

    headers = {
        'Content-Type': 'application/soap+xml;charset=UTF-8;action="http://markets.transelectrica.ro/wse/GetActualDateTime"',
    }

    # Send the SOAP request
    response = requests.post("https://newmarkets.transelectrica.ro/usy-durom-wsendpointg01/00121002300000000000000000000100/ws", data=soap_request, headers=headers)

    if response.status_code == 200:
        return response.content
    else:
        return None

# Button to trigger the SOAP request
if st.button("Get Current Date and Time"):
    response = get_current_datetime()
    if response:
        # Parse the XML response
        tree = etree.fromstring(response)
        date_time = tree.find('.//{http://markets.transelectrica.ro/wse}DateTime')
        if date_time is not None:
            st.success(f"Current Date and Time: {date_time.text}")
        else:
            st.error("Failed to retrieve the date and time from the response.")
    else:
        st.error("Failed to get a response from the server.")

# Run the Streamlit app with:
# streamlit run streamlit_app.py

