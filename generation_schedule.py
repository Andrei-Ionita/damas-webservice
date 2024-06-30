import streamlit as st
import requests
from lxml import etree
from datetime import datetime, timedelta
import time
import xml.etree.ElementTree as ET

# Set the page title
st.set_page_config(page_title="Client Web Service Damas", layout="wide")

# Fetching credentials from Streamlit secrets
ACCESS_CODE_1 = st.secrets["ACCESS_CODE_1"]
ACCESS_CODE_2 = st.secrets["ACCESS_CODE_2"]

# Function to get the current timestamp
def get_current_timestamp():
    now = datetime.utcnow()
    expires = now + timedelta(hours=1)
    return now.strftime("%Y-%m-%dT%H:%M:%SZ"), expires.strftime("%Y-%m-%dT%H:%M:%SZ")

def convert_utc_to_eet(utc_time_str):
    # Remove the 'Z' if present
    if utc_time_str.endswith('Z'):
        utc_time_str = utc_time_str[:-1]
    # Try parsing with both possible formats
    try:
        utc_time = datetime.strptime(utc_time_str, "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        utc_time = datetime.strptime(utc_time_str, "%Y-%m-%dT%H:%M")
    # Convert to EET (UTC+2) and account for daylight saving (UTC+3 during summer)
    eet_time = utc_time + timedelta(hours=3)  # Assuming daylight saving time
    return eet_time.strftime("%Y-%m-%d %H:%M:%S")

# Function to simulate generation schedule response
def get_generation_schedule(date_from, date_to):
    points = "".join([f"<Point><position>{i+1}</position><quantity>4.3</quantity></Point>" for i in range(96)])
    return """
    <env:Envelope xmlns:env="http://www.w3.org/2003/05/soap-envelope">
        <env:Header/>
        <env:Body>
            <ns2:RunSynchronousResponse xmlns:ns2="http://markets.transelectrica.ro/wse">
                <ns2:Output>
                    <ns2:RQID>-1</ns2:RQID>
                    <ns2:Result>
                        <GenerationSchedule_MarketDocument xmlns="urn:iec62325.351:tc57wg16:451-7:generationdocument:7:2">
                            <TimeSeries>
                                <Period>
                                    <timeInterval>
                                        <start>2024-06-26T00:00Z</start>
                                        <end>2024-06-27T00:00Z</end>
                                    </timeInterval>
                                    <Resolution>PT15M</Resolution>
                                    {points}
                                </Period>
                            </TimeSeries>
                        </GenerationSchedule_MarketDocument>
                    </ns2:Result>
                    <ns2:RQState>
                        <ns2:Code>COMPLETED</ns2:Code>
                        <ns2:Description>The request is completed.</ns2:Description>
                    </ns2:RQState>
                </ns2:Output>
            </ns2:RunSynchronousResponse>
        </env:Body>
    </env:Envelope>
    """.format(points=points)



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
                    <wsu:Expires>{expires}</wsu:Expires}
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
    response = requests.post("https://test.newmarkets.transelectrica.ro/usy-durom-wsendpointg01/00127002300000000000000000000100/ws", data=soap_request, headers=headers)

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
    orders = []
    response = get_dispatch_orders(date_from, date_to)
    # Fetch generation schedule
    response_schedule = get_generation_schedule(date_from, date_to)
    generation_schedule = []

    # Calculate the dynamic start time
    dynamic_start_time = (datetime.combine(date_from, datetime.min.time()) - timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M:%SZ")

    if response:
        # Parse the XML response
        root = ET.fromstring(response)
        for bid_time_series in root.findall(".//{urn:iec62325.351:tc57wg16:451-7:reservebiddocument:7:2}Bid_TimeSeries"):
            direction_code = bid_time_series.find(".//{urn:iec62325.351:tc57wg16:451-7:reservebiddocument:7:2}flowDirection.direction").text
            direction = "Crestere" if direction_code == "A01" else "Scadere" if direction_code == "A02" else direction_code
            # Extract start and end times from the Period
            period = bid_time_series.find(".//{urn:iec62325.351:tc57wg16:451-7:reservebiddocument:7:2}Period")
            start_time = period.find(".//{urn:iec62325.351:tc57wg16:451-7:reservebiddocument:7:2}start").text
            end_time = period.find(".//{urn:iec62325.351:tc57wg16:451-7:reservebiddocument:7:2}end").text
            orders.append({
                "Ora de Start": convert_utc_to_eet(start_time),
                "Ora de Sfarsit": convert_utc_to_eet(end_time),
                "Directia": direction,
                "Cantitatea": float(bid_time_series.find(".//{urn:iec62325.351:tc57wg16:451-7:reservebiddocument:7:2}quantity.quantity").text),
            })
        if orders:
            # Sort orders by 'Ora de Start'
            orders = sorted(orders, key=lambda x: x['Ora de Start'])
            st.header("Ordine de Dispecer:")
            st.table(orders)
    else:
        dispatch_orders_placeholder.error("Nu exista ordine pentru perioada selectata.")

    if response_schedule:
        root_schedule = ET.fromstring(response_schedule)
        for point in root_schedule.findall(".//{urn:iec62325.351:tc57wg16:451-7:generationdocument:7:2}Point"):
            position = point.find(".//{urn:iec62325.351:tc57wg16:451-7:generationdocument:7:2}position").text
            quantity = float(point.find(".//{urn:iec62325.351:tc57wg16:451-7:generationdocument:7:2}quantity").text)
            start_time = datetime.strptime(dynamic_start_time, "%Y-%m-%dT%H:%M:%SZ") + timedelta(minutes=15 * (int(position) - 1))
            end_time = start_time + timedelta(minutes=15)
            generation_schedule.append({
                "Ora de Inceput": convert_utc_to_eet(start_time.strftime("%Y-%m-%dT%H:%M:%SZ")),
                "Ora de Sfarsit": convert_utc_to_eet(end_time.strftime("%Y-%m-%dT%H:%M:%SZ")),
                "Punct de bază [MW]": quantity,
                "Bandă reglare [MW]": 0  # Assuming this remains 0 as per the example
            })
        if generation_schedule:
            generation_schedule = sorted(generation_schedule, key=lambda x: x['Ora de Inceput'])
            st.write("Program de Generare:")
            st.table(generation_schedule)

def process_orders_and_calculate_schedule(generation_schedule, orders):
    live_schedule = []
    for interval in generation_schedule:
        start_time = interval["Ora de Inceput"]
        end_time = interval["Ora de Sfarsit"]
        current_power = float(interval["Punct de bază [MW]"])
        for order in orders:
            order_start = order["Ora de Start"]
            order_end = order["Ora de Sfarsit"]
            order_power = order["Cantitatea"]
            if order_start <= start_time < order_end:
                if order["Directia"] == "Crestere":
                    current_power += order_power
                elif order["Directia"] == "Scadere":
                    current_power -= order_power
        live_schedule.append({
            "Ora de Inceput": start_time,
            "Ora de Sfarsit": end_time,
            "Punct de bază [MW]": max(0, current_power),
            "Bandă reglare [MW]": 0  # Assuming this remains 0 as per the example
        })
    return live_schedule

def display_live_schedule():
    st.write("Program de Generare Live:")
    live_schedule = process_orders_and_calculate_schedule(generation_schedule, orders)
    simplified_schedule = []
    for i, row in enumerate(live_schedule):
        if i == 0 or row["Punct de bază [MW]"] != live_schedule[i-1]["Punct de bază [MW]"]:
            simplified_schedule.append(row)
    st.table(simplified_schedule)

# Button to trigger the SOAP request manually
if st.sidebar.button("Obține Ordine de Dispecer"):
    refresh_data()

# Auto-refresh every 30 seconds
while True:
    refresh_data()
    display_live_schedule()
    time.sleep(30)
    st.experimental_rerun()
