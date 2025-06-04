import requests
import pytz
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
import streamlit as st
import pandas as pd

# Function to get the current timestamp
def get_current_timestamp():
    now = datetime.utcnow()
    expires = now + timedelta(hours=1)
    return now.strftime("%Y-%m-%dT%H:%M:%SZ"), expires.strftime("%Y-%m-%dT%H:%M:%SZ")

# Function to convert UTC time to EET
def convert_utc_to_eet(utc_time_str):
    if utc_time_str.endswith('Z'):
        utc_time_str = utc_time_str[:-1]
    try:
        utc_time = datetime.strptime(utc_time_str, "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        try:
            utc_time = datetime.strptime(utc_time_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            utc_time = datetime.strptime(utc_time_str, "%Y-%m-%dT%H:%M")
    eet_time = utc_time + timedelta(hours=3 if (utc_time.month >= 4 and utc_time.month < 10) else 2)
    return eet_time.strftime("%Y-%m-%d %H:%M:%S")

# Function to fetch dispatch orders for a given date range
def get_dispatch_orders(date_from, date_to):
    ACCESS_CODE_1 = st.secrets["ACCESS_CODE_1"]
    ACCESS_CODE_2 = st.secrets["ACCESS_CODE_2"]
    created, expires = get_current_timestamp()
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
    response = requests.post("https://newmarkets.transelectrica.ro/usy-durom-wsendpointg01/00121002300000000000000000000100/ws", data=soap_request, headers=headers)
    if response.status_code == 200:
        return response.content
    else:
        return None

# Function to fetch orders for the entire month of July
def fetch_july_orders(year=2024, month=7):
    eet_timezone = pytz.timezone('Europe/Bucharest')
    all_orders = []

    for day in range(1, 32):
        date_from = datetime(year, month, day, 0, 0, 0, tzinfo=eet_timezone).strftime("%Y-%m-%d")
        date_to = datetime(year, month, day, 23, 59, 59, tzinfo=eet_timezone).strftime("%Y-%m-%d")
        response = get_dispatch_orders(date_from, date_to)

        if response:
            root = ET.fromstring(response)
            for bid_time_series in root.findall(".//{urn:iec62325.351:tc57wg16:451-7:reservebiddocument:7:2}Bid_TimeSeries"):
                direction_code = bid_time_series.find(".//{urn:iec62325.351:tc57wg16:451-7:reservebiddocument:7:2}flowDirection.direction").text
                direction = "Crestere" if direction_code == "A01" else "Scadere" if direction_code == "A02" else direction_code
                period = bid_time_series.find(".//{urn:iec62325.351:tc57wg16:451-7:reservebiddocument:7:2}Period")
                start_time = period.find(".//{urn:iec62325.351:tc57wg16:451-7:reservebiddocument:7:2}start").text
                end_time = period.find(".//{urn:iec62325.351:tc57wg16:451-7:reservebiddocument:7:2}end").text
                all_orders.append({
                    "Ora de Start": convert_utc_to_eet(start_time),
                    "Ora de Sfarsit": convert_utc_to_eet(end_time),
                    "Directia": direction,
                    "Cantitatea": bid_time_series.find(".//{urn:iec62325.351:tc57wg16:451-7:reservebiddocument:7:2}quantity.quantity").text,
                })

    return all_orders

# Function to create initial generation schedule for the entire month
def create_initial_schedule(year=2024, month=7):
    eet_timezone = pytz.timezone('Europe/Bucharest')
    schedule = []
    base_time = datetime(year, month, 1, 0, 0, 0, tzinfo=eet_timezone)

    for day in range(1, 32):
        for i in range(96):  # 96 intervals per day
            start_time = base_time + timedelta(days=day-1, minutes=15 * i)
            end_time = start_time + timedelta(minutes=15)
            hour = start_time.hour
            
            if day == 17:
                if 0 <= hour < 7:
                    power = 4.3
                elif 7 <= hour < 10:
                    power = 8.6
                elif 10 <= hour < 16:
                    power = 4.3
                else:
                    power = 8.6
            elif day == 18:
                if 0 <= hour < 10:
                    power = 8.6
                elif 10 <= hour < 16:
                    power = 4.3
                elif 16 <= hour < 19:
                    power = 8.6
                else:
                    power = 4.3
            else:
                power = 4.3

            schedule.append({
                "Ora de Inceput": start_time.strftime("%Y-%m-%d %H:%M:%S"),
                "Ora de Sfarsit": end_time.strftime("%Y-%m-%d %H:%M:%S"),
                "Punct de bază [MW]": power,
                "Bandă reglare [MW]": 0
            })

    return schedule

# Function to apply dispatch orders to the initial schedule and create live schedule
def apply_orders_to_schedule(initial_schedule, orders):
    live_schedule = [interval.copy() for interval in initial_schedule]

    for order in orders:
        order_start = datetime.strptime(order["Ora de Start"], "%Y-%m-%d %H:%M:%S")
        order_end = datetime.strptime(order["Ora de Sfarsit"], "%Y-%m-%d %H:%M:%S")
        order_power = float(order["Cantitatea"])
        direction = order["Directia"]

        for interval in live_schedule:
            interval_start = datetime.strptime(interval["Ora de Inceput"], "%Y-%m-%d %H:%M:%S")
            interval_end = datetime.strptime(interval["Ora de Sfarsit"], "%Y-%m-%d %H:%M:%S")

            if order_start <= interval_start < order_end:
                if direction == "Crestere":
                    interval["Punct de bază [MW]"] += order_power
                elif direction == "Scadere":
                    interval["Punct de bază [MW]"] -= order_power
                interval["Punct de bază [MW]"] = max(0, interval["Punct de bază [MW]"])  # Ensure no negative values

    return live_schedule

# Fetch orders for July
july_orders = fetch_july_orders()
# st.table(july_orders)
# Create initial generation schedule for July
initial_schedule = create_initial_schedule()
# st.table(initial_schedule)
# Apply orders to the initial schedule to create live schedule
live_schedule = apply_orders_to_schedule(initial_schedule, july_orders)

# # Display live schedule
df_live_schedule = pd.DataFrame(live_schedule)
st.write("Program de Generare Live pentru Iulie:")
st.dataframe(df_live_schedule)
df_live_schedule.to_excel("./Generation_Schedule_July.xlsx")