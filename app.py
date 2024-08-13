import streamlit as st
import requests
from lxml import etree
from datetime import datetime, timedelta
import time
import xml.etree.ElementTree as ET
import numpy as np
import pytz
import base64

# Set the page title
st.set_page_config(page_title="Client Web Service Damas", layout="wide")

# Fetching credentials from Streamlit secrets
ACCESS_CODE_1 = st.secrets["ACCESS_CODE_1"]
ACCESS_CODE_2 = st.secrets["ACCESS_CODE_2"]

def autoplay_audio(file_path: str):
    try:
        with open(file_path, "rb") as f:
            data = f.read()
            b64 = base64.b64encode(data).decode()
            md = f"""
                <audio autoplay="true">
                <source src="data:audio/wav;base64,{b64}" type="audio/wav">
                </audio>
                """
            st.markdown(md, unsafe_allow_html=True)
    except FileNotFoundError:
        print("Audio file not found. Please ensure the file exists.")

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
        try:
            utc_time = datetime.strptime(utc_time_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            utc_time = datetime.strptime(utc_time_str, "%Y-%m-%dT%H:%M")
    # Convert to EET (UTC+2) and account for daylight saving (UTC+3 during summer)
    eet_time = utc_time + timedelta(hours=3 if (utc_time.month >= 4 and utc_time.month < 10) else 2)
    return eet_time.strftime("%Y-%m-%d %H:%M:%S")

# Function to simulate generation schedule response
def get_generation_schedule():
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
                                        <end>2024-06-26T23:45Z</end>
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
    """.format(points="".join([f"<Point><position>{i+1}</position><quantity>4.3</quantity></Point>" for i in range(96)]))

# Function to convert a time to UTC string format
def to_utc_string(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

# Function to simulate generation schedule response
def get_generation_schedule_manually():
    eet_timezone = pytz.timezone('Europe/Bucharest')
    # Get current date in EET and adjust times to EET
    base_time = datetime.now(eet_timezone).replace(hour=0, minute=0, second=0, microsecond=0)

    points = []
    for i in range(96):
        point_time = base_time + timedelta(minutes=15 * i)
        point_time_utc = point_time.astimezone(pytz.utc)
        points.append(f"<Point><position>{i+1}</position><quantity>4.3</quantity><time>{to_utc_string(point_time_utc)}</time></Point>")
    
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
                                        <start>{start}</start>
                                        <end>{end}</end>
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
    """.format(
        start=to_utc_string(base_time.astimezone(pytz.utc)),
        end=to_utc_string((base_time + timedelta(hours=24) - timedelta(minutes=15)).astimezone(pytz.utc)),
        points="".join(points)
    )

def create_tomorrows_generation_schedule():
    intervals = []
    base_time = datetime.strptime("2024-08-12T21:00:00Z", "%Y-%m-%dT%H:%M:%SZ")
    for i in range(96):
        start_time = base_time + timedelta(minutes=15 * i)
        end_time = start_time + timedelta(minutes=15)
        hour = (start_time.hour + 3) % 24  # Adjust for EET (UTC+3 in summer)
        
        if 6 <= hour <=24:
            power = 4.3
        # elif 17 <= hour <= 24:
        #     power = 4.3
        # elif 16 <= hour < 19:
        #     power = 8.6
        else:
            power = 0
        
        intervals.append({
            "Ora de Inceput": convert_utc_to_eet(start_time.strftime("%Y-%m-%dT%H:%M:%SZ")),
            "Ora de Sfarsit": convert_utc_to_eet(end_time.strftime("%Y-%m-%dT%H:%M:%SZ")),
            "Punct de bază [MW]": power,
            "Bandă reglare [MW]": 0
        })
    return intervals

# def create_2days_ahead_generation_schedule():
#     intervals = []
#     base_time = datetime.strptime("2024-07-03T21:00:00Z", "%Y-%m-%dT%H:%M:%SZ")
#     for i in range(96):
#         start_time = base_time + timedelta(minutes=15 * i)
#         end_time = start_time + timedelta(minutes=15)
#         power = 4.3 if start_time >= datetime.strptime("2024-08-04T16:00:00Z", "%Y-%m-%dT%H:%M:%SZ") else 0.0
#         intervals.append({
#             "Ora de Inceput": convert_utc_to_eet(start_time.strftime("%Y-%m-%dT%H:%M:%SZ")),
#             "Ora de Sfarsit": convert_utc_to_eet(end_time.strftime("%Y-%m-%dT%H:%M:%SZ")),
#             "Punct de bază [MW]": power,
#             "Bandă reglare [MW]": 0
#         })
#     return intervals

def create_2days_ahead_generation_schedule():
    intervals = []
    base_time = datetime.strptime("2024-08-13T21:00:00Z", "%Y-%m-%dT%H:%M:%SZ")
    for i in range(96):
        start_time = base_time + timedelta(minutes=15 * i)
        end_time = start_time + timedelta(minutes=15)
        hour = (start_time.hour + 3) % 24  # Adjust for EET (UTC+3 in summer)
        
        if 6 <= hour <= 24:
            power = 4.3
        # elif 10 <= hour < 16:
        #     power = 4.3
        # elif 16 <= hour < 19:
        #     power = 8.6
        else:
            power = 0
        
        intervals.append({
            "Ora de Inceput": convert_utc_to_eet(start_time.strftime("%Y-%m-%dT%H:%M:%SZ")),
            "Ora de Sfarsit": convert_utc_to_eet(end_time.strftime("%Y-%m-%dT%H:%M:%SZ")),
            "Punct de bază [MW]": power,
            "Bandă reglare [MW]": 0
        })
    return intervals

def create_standard_generation_schedule(date_from):
    intervals = []
    base_time = datetime.combine(date_from, datetime.min.time())
    for i in range(96):
        start_time = base_time + timedelta(minutes=15 * i)
        end_time = start_time + timedelta(minutes=15)
        power = 4.3  # Standard power output for the entire day
        
        intervals.append({
            "Ora de Inceput": convert_utc_to_eet(start_time.strftime("%Y-%m-%dT%H:%M:%S")),
            "Ora de Sfarsit": convert_utc_to_eet(end_time.strftime("%Y-%m-%dT%H:%M:%S")),
            "Punct de bază [MW]": power,
            "Bandă reglare [MW]": 0
        })
    return intervals

# Function to send SOAP request for dispatch orders
def get_dispatch_orders(date_from, date_to):
    created, expires = get_current_timestamp()
    date_to = date_to - timedelta(days=1)
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

def process_orders_and_calculate_schedule(generation_schedule, orders):
    live_schedule = []
    current_power = float(generation_schedule[0]["Punct de bază [MW]"])
    current_start = generation_schedule[0]["Ora de Inceput"]
    schedule_changed = False

    for interval in generation_schedule:
        start_time = interval["Ora de Inceput"]
        end_time = interval["Ora de Sfarsit"]
        power = float(interval["Punct de bază [MW]"])

        # Apply orders
        for order in orders:
            order_start = order["Ora de Start"]
            order_end = order["Ora de Sfarsit"]
            order_power = float(order["Cantitatea"])
            if order_start <= start_time < order_end:
                if order["Directia"] == "Crestere":
                    power += order_power
                elif order["Directia"] == "Scadere":
                    power -= order_power

        # If power changes, update live schedule
        if power != current_power:
            live_schedule.append({
                "Ora de Inceput": current_start,
                "Ora de Sfarsit": start_time,
                "Punct de bază [MW]": max(0, current_power),
                "Bandă reglare [MW]": 0
            })
            current_start = start_time
            current_power = power
            schedule_changed = True

    # Append the last interval
    live_schedule.append({
        "Ora de Inceput": current_start,
        "Ora de Sfarsit": generation_schedule[-1]["Ora de Sfarsit"],
        "Punct de bază [MW]": max(0, current_power),
        "Bandă reglare [MW]": 0
    })

    return live_schedule, schedule_changed

# Function to handle auto-update and date setting
def handle_dates():
    if st.session_state.auto_update:
        eet_timezone = pytz.timezone('Europe/Bucharest')
        st.session_state.date_from = datetime.now(eet_timezone).date()
        st.session_state.date_to = (datetime.now(eet_timezone) + timedelta(days=1)).date()
    else:
        if 'date_from' not in st.session_state:
            st.session_state.date_from = None
        if 'date_to' not in st.session_state:
            st.session_state.date_to = None
    return st.session_state.date_from, st.session_state.date_to

# Function to update the clock
def update_clock():
    eet_timezone = pytz.timezone('Europe/Bucharest')
    current_time = datetime.now(eet_timezone).strftime("%Y-%m-%d %H:%M:%S")
    clock_placeholder.markdown(f"<h1 style='text-align: right;'>{current_time}</h1>", unsafe_allow_html=True)

# Main section
st.title("Client Web Service Damas")
st.write("Aplicația permite interacțiunea cu Web Service-ul Damas pentru a obține ordine de dispecer.")
# Add a checkbox for auto-update
if 'auto_update' not in st.session_state:
    st.session_state.auto_update = True
auto_update = st.sidebar.checkbox("Auto-Update Dates", value=True)

# Sidebar inputs for date range
st.sidebar.header("Selectați Intervalul de Date")
date_from_user = st.sidebar.date_input("Data de început", value=datetime.now().date())
date_to_user = st.sidebar.date_input("Data de sfârșit", value = (datetime.now() + timedelta(days=1)).date())
dispatch_orders_placeholder = st.empty()

# Use a different audio file URL
audio_file = "./mixkit-classic-alarm-995.wav"

# Placeholder for the clock
clock_placeholder = st.empty()

# Initialize order count variables if not already set
if 'previous_order_count' not in st.session_state:
    st.session_state.previous_order_count = 0
# st.write(st.session_state)
def refresh_data(date_from, date_to, previous_order_count):
    print("The numbers of orders when the function is called: {}".format(previous_order_count))
    orders = []

    response = get_dispatch_orders(date_from, date_to)
    
    # Fetch generation schedule
    response_schedule = get_generation_schedule_manually()
    current_date = datetime.now().date()
    if current_date == datetime(2024, 8, 13).date():
        generation_schedule = create_tomorrows_generation_schedule()
    elif current_date == datetime(2024, 8, 14).date():
        generation_schedule = create_2days_ahead_generation_schedule()
    else:
        generation_schedule = []  # Replace with your usual generation schedule fetching logic

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
                "Cantitatea": bid_time_series.find(".//{urn:iec62325.351:tc57wg16:451-7:reservebiddocument:7:2}quantity.quantity").text,
            })
        if orders:
            # Sort orders by 'Ora de Start'
            orders = sorted(orders, key=lambda x: x['Ora de Start'])
    else:
        dispatch_orders_placeholder.error("Nu exista ordine pentru perioada selectata.")

    if len(generation_schedule) > 0:
        generation_schedule = sorted(generation_schedule, key=lambda x: x['Ora de Inceput'])

        # Process orders and calculate live schedule
        live_schedule, schedule_changed = process_orders_and_calculate_schedule(generation_schedule, orders)
        st.write("Program de Generare Live:")
        st.table(live_schedule)
        
        # Check if the order count has changed
        if len(orders) != previous_order_count:
            previous_order_count = len(orders)
            with open(audio_file, "rb") as f:
                audio_bytes = f.read()
            st.audio(audio_bytes, format="audio/wav", autoplay=True)

    elif response_schedule:
        root_schedule = ET.fromstring(response_schedule)
        for point in root_schedule.findall(".//{urn:iec62325.351:tc57wg16:451-7:generationdocument:7:2}Point"):
            position = point.find(".//{urn:iec62325.351:tc57wg16:451-7:generationdocument:7:2}position").text
            quantity = point.find(".//{urn:iec62325.351:tc57wg16:451-7:generationdocument:7:2}quantity").text
            start_time_input = date_from  # Use the user input date directly as a date object
            initial_start_time = datetime.combine(start_time_input, datetime.min.time()) - timedelta(hours=3)  # Subtract 3 hours to get the initial start time

            initial_start_time_str = initial_start_time.strftime("%Y-%m-%dT%H:%MZ")
            start_time = datetime.strptime(initial_start_time_str, "%Y-%m-%dT%H:%MZ") + timedelta(minutes=15 * (int(position) - 1))
            end_time = start_time + timedelta(minutes=15)
            generation_schedule.append({
                "Ora de Inceput": convert_utc_to_eet(start_time.strftime("%Y-%m-%dT%H:%M:%S")),
                "Ora de Sfarsit": convert_utc_to_eet(end_time.strftime("%Y-%m-%dT%H:%M:%S")),
                "Punct de bază [MW]": quantity,
                "Bandă reglare [MW]": 0
            })
        if generation_schedule:
            generation_schedule = sorted(generation_schedule, key=lambda x: x['Ora de Inceput'])

            # Process orders and calculate live schedule
            live_schedule, schedule_changed = process_orders_and_calculate_schedule(generation_schedule, orders)
            st.header("Program de Generare Live:", divider="gray")
            st.table(live_schedule)
            print(len(orders), previous_order_count)
            # Check if the order count has changed
            if len(orders) != previous_order_count:
                print("The alarm must be triggered!")
                previous_order_count = len(orders)
                # st.audio("./mixkit-classic-alarm-995.wav", format="audio/wav", loop=False, autoplay=True)
                # autoplay_audio(audio_file)
                with open(audio_file, "rb") as f:
                    audio_bytes = f.read()
                st.audio(audio_bytes, format="audio/wav", autoplay=True)
    # Filter orders for the current day
    current_day_orders = [order for order in orders if datetime.strptime(order["Ora de Start"], '%Y-%m-%d %H:%M:%S').date() == date_from]

    if current_day_orders:
        st.subheader("Ordine de Dispecer:", divider="gray")
        st.table(current_day_orders)
    else:
        dispatch_orders_placeholder.error("Nu exista ordine pentru ziua curentă.")
    return previous_order_count

manual_selection = False
if st.sidebar.button("Obține Ordine de Dispecer"):
    refresh_data(date_from_user, date_to_user, st.session_state.previous_order_count)
    manual_selection = True
if auto_update:
    st.session_state.auto_update = True
else:
    st.session_state.auto_update = False

while True:
    if auto_update and not manual_selection:
        date_from, date_to = handle_dates()
        st.session_state.previous_order_count = refresh_data(date_from, date_to, st.session_state.previous_order_count)
        # st.write(st.session_state)
    for _ in range(30):
        update_clock()
        time.sleep(1)
    st.rerun()
