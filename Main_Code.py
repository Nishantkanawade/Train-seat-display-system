import urequests as requests
import ujson as json
import time
import machine    
import network
import utime
import ntptime
from machine import Pin, SoftI2C
from lcd_api import LcdApi
from i2c_lcd import I2cLcd

#created a list to hold the coverd or crossed station
covered_list = []

#initializing the I2C  LCD display 
i2c = SoftI2C(scl=Pin(22), sda=Pin(21), freq=10000)
lcd = I2cLcd(i2c,0x27,2,16)

# Define your Firebase project URL

# URL of the database where the passenger data is stored
FIREBASE_URL = "https://passengerdatabase-89f94-default-rtdb.firebaseio.com/" 

# URL of the database where the station list of route of the train is stored
firebase_url = "https://wificonnectingproject-default-rtdb.firebaseio.com/"
seatno = "seatno 2"

ssid= "OPPO A15s" # set your own wifi ssid
password = "15253545" #set your own wifi password

#switch is connected to pin 13 and 12 to collect the information of station has been reached
pin_number1 = 13
pin_number2 = 12
pinin = machine.Pin(pin_number1, Pin.IN)
pinout= machine.Pin(pin_number2, Pin.OUT)
pinout.value(1)


# Function to push data to Firebase
def push_to_firebase( URL,loc,data):
    url = URL + loc+ ".json"
    headers = {"Content-Type": "application/json"}
    response = requests.patch(url, data=json.dumps(data))
    print("Response:", response.text)

#getting real time date
def get_current_date():
    while(1):
        try:
            ntptime.settime()  # Synchronize time with NTP server
            current_time = utime.localtime()  # Get current time
            year, month, day = current_time[0:3]  # Extract year, month, and day
            return "{}-{}-{}".format(day,month,year)  # Format date string
        except OSError as e:
            print("Error retrieving current date:", e)
            return None



#fetching from google firebase
def fetch_from_firebase(URL,path):
    url = URL +path+ ".json"
    response = requests.get(url)
    data = response.json()
    return data

# Displaying the name,source and destination of the passenger
def display_data(pname,psource,pdest):
    lcd.clear()
    a="Name = {}".format(pname)
    b="S={}".format(psource)
    c="D={}".format(pdest)
    lcd.putstr(a)
    lcd.move_to(0,1)
    lcd.putstr(b)
    lcd.move_to(8,1)
    lcd.putstr(c)
    
#calculating no of paccenger for a parrticular seat no at a currrent date
def find_length_of_passenger():
    n=1
    while True:
        path ="passengers data/{}/{}/{}".format(seatno,get_current_date(), n)
        holding = fetch_from_firebase(FIREBASE_URL,path)
        if not holding :
            break
        n=n+1
    return n

#calculating the no  of total station 
def find_no_station():
    m = 1
    while True:
        path = "station_list/{}".format(m)
        holding = fetch_from_firebase(firebase_url,path)
        if not holding:
            break
        m =m+1
    return m

# Function to get the current station from the google firebase when train is reached to the station
def get_current_station(a,b):
    i=2
    while(i<a):
        path2 = "station_list/{}".format(i)
        fdata=fetch_from_firebase(firebase_url,path2)
        if(fdata["status"]=="Done"):
            i = i+1
            b.append(fdata["stname"])
        else:
            while(pinin.value() == 0):
                time.sleep(1)
            time.sleep(1)
            value = fdata["stname"]
            ust={"status":"Done"}
            push_to_firebase(firebase_url,path2,ust)
            if(value not in b):
                b.append(value)
            return value
  
#main code
def connect_to_wifi(ssid, password):
    wlan = network.WLAN(network.STA_IF)  # Initialize WLAN interface in station mode
    wlan.active(True)  # Activate the WLAN interface
   
    while True:  # Keep trying indefinitely
        try:
            print("Checking for WiFi network...")
            wlan.connect(ssid, password)  # Connect to the WiFi network
            while not wlan.isconnected():  # Wait until connected
                time.sleep(1)
            print("Connected to WiFi:", ssid)
            lcd.putstr("connected")
            time.sleep(2)
            lcd.clear()
            first = fetch_from_firebase(firebase_url,"station_list/1/stname")
            total_station = find_no_station()
            covered_list.append(first)
            print(covered_list)

            while True:  # Monitor the connection status continuously
                if not wlan.isconnected():  # If connection lost, attempt to reconnect
                    print("WiFi connection lost. Reconnecting...")
                    wlan.connect(ssid, password)
                    while not wlan.isconnected():  # Wait until reconnected
                        time.sleep(0.5)
                    print("Reconnected to WiFi:", ssid)
                no_of_passenger =  find_length_of_passenger()
                k = 1
                while(k < no_of_passenger):
                    path1 ="passengers data/{}/{}/{}".format(seatno,get_current_date(), k)
                    holding = fetch_from_firebase(FIREBASE_URL,path1)
                    if(holding["Status"]=="Done"):  #cheaking the status to skip the data acccording to status
                        k=k+1
                    else:
                        pname=holding["Name"]
                        psource=holding["Source"]
                        pdest=holding["Destination"]
                        print(pname)
                        if(psource in covered_list):
                            display_data(pname,psource,pdest)
                            while True:
                                current_station = get_current_station(total_station,covered_list)
                                print(covered_list)
                                print(current_station)
                                if(current_station == pdest):
                                    update_status={"Status":"Done"}
                                    push_to_firebase(FIREBASE_URL,path1,update_status)
                                    lcd.clear()
                                    break
                        else:
                            lcd.clear()
                            lcd.putstr("No Passenger At This Time")                            
                            get_current_station(total_station,covered_list)
                            print(covered_list)
                            k=k-1
                        
                    if(k == no_of_passenger):
                        lcd.clear()
                        lcd.putstr("No Passenger At This Time")
                time.sleep(1)
                k = k+1
        except Exception as e:
            print("Error occurred:", e)
            time.sleep(1)  # Wait before retrying


connect_to_wifi(ssid,password)