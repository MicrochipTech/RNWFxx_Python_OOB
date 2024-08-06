#!/usr/bin/python3

# © 2024 Microchip Technology Inc. and its subsidiaries
# Subject to your compliance with these terms, you may use this Microchip software
# and any derivatives exclusively with Microchip products. You are responsible for 
# complying with third party license terms applicable to your use of third party 
# software (including open source software) that may accompany this Microchip 
# software.
# Redistribution of this Microchip software in source or binary form is allowed and
# must include the above terms of use and the following disclaimer with the 
# distribution and accompanying materials.
# SOFTWARE IS “AS IS.” NO WARRANTIES, WHETHER EXPRESS, IMPLIED OR STATUTORY, APPLY 
# TO THIS SOFTWARE, INCLUDING ANY IMPLIED WARRANTIES OF NON-INFRINGEMENT, 
# MERCHANTABILITY, OR FITNESS FOR A PARTICULAR PURPOSE. IN NO EVENT WILL MICROCHIP BE
# LIABLE FOR ANY INDIRECT, SPECIAL, PUNITIVE, INCIDENTAL OR CONSEQUENTIAL LOSS, 
# DAMAGE, COST OR EXPENSE OF ANY KIND WHATSOEVER RELATED TO THE SOFTWARE, HOWEVER 
# CAUSED, EVEN IF MICROCHIP HAS BEEN ADVISED OF THE POSSIBILITY OR THE DAMAGES ARE 
# FORESEEABLE. TO THE FULLEST EXTENT ALLOWED BY LAW, MICROCHIP’S TOTAL LIABILITY ON 
# ALL CLAIMS RELATED TO THE SOFTWARE WILL NOT EXCEED AMOUNT OF FEES, IF ANY, YOU 
# PAID DIRECTLY TO MICROCHIP FOR THIS SOFTWARE.

import pathlib

try:
    import serial  
    import serial.tools.list_ports  
    import time
    from datetime import datetime
    import kbhit
    import os
    from cloud_config import iot_parameters
    from print_utils import *
    import re  
    from time import sleep
    import argparse
    import pathlib
    import random
    from argparse import ArgumentParser
    from pathvalidate.argparse import validate_filename_arg, validate_filepath_arg
    # import atexit
    # import json
    

except ModuleNotFoundError:
    print(f'\n\n----------------------------------------------')
    print(f' Error! Python module not found.')
    print(f'   Please run "pip install -r requirements.txt"')
    print(f'   from the command line. Then try again.')
    print(f'----------------------------------------------\n\n')
    user_in = input(f'Install required Python modules now? [Y|n] ')
    if user_in.upper() == 'Y' or user_in == '':
        import os 
        os.system("pip install -r requirements.txt")
        print(f'\n  Rerun the demo now...\n\n')
    else:
        print(f'\n   Please manually run "pip install -r requirements.txt" from the command line')
    exit(1)


APP_REL_VERSION = "2.5.0"   # Application/Demo Version
APP_BUILD = ""              # Application/Demo Build version (Git Hash)

#APP Control Constants
EN_LOCAL_TELEMETRY = True   # Enables local updates instead of using subscription telemetry
EN_CERT_SUPPORT = True      # Set to True to enable cert listing & deletion
                            #   Setting False -> True requires uncommenting the 2 
                            #   fields 'device_cert_filename' & 'device_key_filename'
                            #   in the script 'cloud_config.py'
WIFI_TIMEOUT_S = 20         # AT+WSTA=1 command, Wi-Fi connection timeout in seconds
WIFI_TIMEOUT_TLS_S = 45     # AT+WSTA=1 command, TLS broker Wi-Fi connection timeout in seconds
MQTT_TIMEOUT_S = 60         # MQTT server login timeout in seconds

# LOCAL_ECHO - Set to True to display each command char
LOCAL_ECHO = True
BLOCK_PERIODIC_TIME_RESP = True
BANNER_BORDER_LEV_1 = '■'   # "─ ━  ═  ■  "
BANNER_BORDER_LEV_2 = '━'   # "─ ━  ═  ■  "
BANNER_BORDER_LEV_3 = '─'   # "─ ━  ═  ■  "

# Single character keyboard codes for CLI commands
# Always use the UPPERCASE version as the code changes everything to upper case
EN_RAW_CODE_DISPLAY: bool = False   # Display new RAW codes by setting bool to True

COUNT_KEY = 67              # 'C'       Increment count, one time
BUTTON_KEY = 66             # 'B'       Toggle button state 1->0->1, etc 1 time
TEMP_KEY = 84               # 'T'       Update temperature by a random temperature delta 1 time
REPORT_RATE_KEY = 73        # 'I'       Update telemetry: button, count & temp 10 times (every 2s)
                            #             Each 'I' press changes rate: 2s -> 5s -> 10s ->0s (stopped)

REPORT_RATE_INF_KEY = 9     # 'CTRL+I'  All of these keys act just the 'I' key except the updates
                            # 'CTRL+i'    continue forever (not 10 times). Like the 'I' key, each
                            # 'Tab'       key press cycles the rate: 2s -> 5s -> 10s ->0s (stopped)

RESUME_KEY = 82             # 'R'       Reconnect Wi-Fi, broker (from the Demo) or RESET & Run (from the CLI)
DISCONN_KEY = 88            # 'X'       Disconnect MQTT broker / Wi-Fi key
HELP_KEY = 72               # 'H'       Display Help screen for the App or CLI

# Application Configuration File
APP_CONFIG_FILE = "app.cfg"         # Default file name for application configuration settings
APP_CMD_LOG_PATH = "logs"           # Hardcoded relative log file path


def val_args(args, parser) -> tuple:
    """ Validates command line argument(s)
    """
    if args.cfg == None:
        args.cfg =  globals()["APP_CONFIG_FILE"]
    else:
        try:
            file = pathlib.Path(args.cfg)
            path = str(file.parent)
            if not os.path.exists(path):
                os.makedirs(path)  
            validate_filepath_arg(args.cfg) #, platform="auto")                          
        except OSError as e:
            banner(f'ERROR:  {e}')
            exit()
        APP_CONFIG_FILE = args.cfg
    return args

def get_args() -> tuple:
    """ Retrieves command line arguements and returns the result as a tuple.
    """
    # os.system('cls')  # Clear terminal screen
    description='\n\nPython OOB Demo for "test.mosquitto.org'
    script_usage='\n    python oobdemo.py [-c <cfg_file>]\n'
    parser = argparse.ArgumentParser(description=description, usage=script_usage)
    
    parser.add_argument("-c", "--cfg", metavar='<Path\Filename>', required = False, help="Set an alternate configuration file path/name")
    args = parser.parse_args()
    args = val_args(args, parser)
    return args


# Object read/write configuration json file
ARGS = get_args()                                           # Put command line args into global space
iotp = iot_parameters(ARGS.cfg, False)                      # Puts config files values into global space var 'iotp'

cert_support = globals()["EN_CERT_SUPPORT"]
print(f'CERT SUPPORT: {cert_support}')
        

try:
    APP_CMD_LOG_FILE = iotp.params["log_filename"]

    # Supported part numbers are in a dictionary of tuples.
    # The device is the key and the tuple contains all the possible
    # device names returned by the AT+GMM command. The identified
    # device determines how the script will run.
    SUPPORTED_RNS_DICT = {"RNWF02": ("PIC32MZW2", "RNWF02"),
                          "RNWF11": ("PIC32MZW1", "RNWF11")
                          }
    APP_DISPLAY_LEVEL = int(iotp.params["display_level"])
    AT_COMMAND_TIMEOUT = int(iotp.params["at_command_timeout"])  # AT cmds timeout in seconds

except KeyError as e:
    banner(f' Error: Configuration parameter {e} missing \n\n'
            f'Verify the parameter {e} in "{APP_CONFIG_FILE}"\n'
            f'  Manually add/edit the parameter OR\n'
           
            f'  Delete "{APP_CONFIG_FILE}" to recreate it on the next run', BANNER_BORDER_LEV_3)
    exit(1)

TLS_CFG_INDEX = 1   # All AT+TLSC commands can be programmed into 1 of 2 banks, 1 or 2.
                    # Then AT+MQTT=7,x will set which bank is used for the TLSC commands.
                    # Use 1 or 2, not 0(AT Spec RNWF11 doc is incorrect)

TLS_CERT_BUILDS = "./Tools/CertificateTool/CertBuilds"

#
# Display states can be set in the configuration file; eg "display_level": "3",
APP_DISPLAY_OFF = 0                         # Extra displays off...cleanest output
APP_DISPLAY_STATES = 1                      # Display State Banners & lower
APP_DISPLAY_INFO = 2                        # Display info and events & lower
APP_DISPLAY_DEMO = 3                        # Display 'Demo' IOTC data and lower
APP_DISPLAY_DECODES = 4                     # Display Decodes like JSON, CRx & lower

DEMO_LOOP_COUNT = 10                        # Number of times to send Telemetry data

#
# Application States
APP_STATE_CLI = 0                           # CLI state occurs on fatal error, user 'ESC' OR after the DEMO
APP_STATE_INIT = 1                          # Bare minimum commands required to start; RESET, NETIFC, etc
APP_STATE_WIFI_CONNECT = 2                  # Connect to Wi-Fi
APP_STATE_MQTT_SETTINGS = 3                 # Setup MQTT
APP_STATE_MQTT_CONNECT_BROKER = 4           # Connects to broker
APP_STATE_DEMO = 5                          # Demo state application
APP_STATE_NEXT_STATE = 999                  # Very high state value will cause jump to next state

APP_STATE_START = APP_STATE_WIFI_CONNECT    # Sets the beginning STATE (after APP_STATE_INIT)

APP_SUB_STATE_DEMO_LOOP = 1

# Special states or state value indicating the beginning or completion of a state
APP_STATE_BEGIN = 0                         
APP_STATE_COMPLETE = 65535

if EN_CERT_SUPPORT:
    help_str_cli = f' {APP_STATE_CLI} - APP_STATE_CLI Help\n' \
    '  H    - This help screen\n' \
    '  X    - Disconnect broker or Wi-Fi\n' \
    '  R    - Resume Demo (Full Reset & Run)\n' \
    '  AT+  - AT command with or w/o the \'AT\' eg: \'AT+GMM\' or \'+GMM\'\n' \
    '  DIR  - List certs & keys. eg: dir [c | k] \n' \
    '  DEL  - Delete certs & keys. eg: del [c | k] <FILENAME>\n' \
    '  SCAN - Scan & displays Wi-Fi information\n' \
    '  SYS  - Displays network, system, and module info\n' \
    '  ESC  - [ESC] key quit application\n'
    help_str_demo = f' {APP_STATE_DEMO} - APP_STATE_IOTC_DEMO\n' \
    '  H    - This help screen\n' \
    '  B    - Toggles Button state \'Button\'(0,1)\n' \
    '  C    - Increment \'Count\'(0->N)\n' \
    '  T    - Update \'Temp\' value (random -5.0 to +5.0 degrees)\n' \
    '  I    - Increment \'Report Rate\' (0s, 2s, 5s, 10s) then...\n' \
    '         updates all telemetry at the \'reportRate\' 10 times\n' \
    '  TAB  - Same as \'I\' except updates all telemetry FOREVER \n' \
    '  R    - Resume Demo (Wi-Fi, Broker Reconnect)\n' \
    '  AT+  - AT command with or w/o the \'AT\' eg: \'AT+GMM\' or \'+GMM\'\n' \
    '  DIR  - List certs & keys. eg: dir [c | k] \n' \
    '  DEL  - Delete certs & keys. eg: del [c | k] <FILENAME>\n' \
    '  SCAN - Scan & displays Wi-Fi information\n' \
    '  SYS  - SYS  - Displays network, system, and module info\n' \
    '  ESC  - [ESC] key exit to CLI. [ESC][ESC] exits application\n'    
else:
    help_str_cli = f' {APP_STATE_CLI} - APP_STATE_CLI Help\n' \
    '  H    - This help screen\n' \
    '  X    - Disconnect broker or Wi-Fi\n' \
    '  R    - Resume Demo (Full Reset & Run)\n' \
    '  AT+  - AT command with or w/o the \'AT\' eg: \'AT+GMM\' or \'+GMM\'\n' \
    '  SCAN - Scan & displays Wi-Fi information\n' \
    '  SYS  - Displays network, system, and module info\n' \
    '  ESC  - [ESC] key. Exits application\n'
    help_str_demo = f' {APP_STATE_DEMO} - APP_STATE_IOTC_DEMO\n' \
    '  H    - This help screen\n' \
    '  B    - Toggles Button state \'Button\'(0,1)\n' \
    '  C    - Increment \'Count\'(0->N)\n' \
    '  T    - Update \'Temp\' value (random -5.0 to +5.0 degrees)\n' \
    '  I    - Increment \'Report Rate\' (0s, 2s, 5s, 10s) then...\n' \
    '         updates all telemetry at the \'reportRate\' 10 times\n' \
    '  TAB  - Same as \'I\' except updates all telemetry FOREVER \n' \
    '  R    - Resume Demo (Wi-Fi, Broker Reconnect)\n' \
    '  AT+  - AT command with or w/o the \'AT\' eg: \'AT+GMM\' or \'+GMM\'\n' \
    '  SCAN - Scan & displays Wi-Fi information\n' \
    '  SYS  - SYS  - Displays network, system, and module info\n' \
    '  ESC  - [ESC] key exits to CLI. [ESC][ESC] exits application\n'



MQTT_MINIMUM_READ_THRESHOLD_SZ = 300
MQTT_FIELDS = ["button", "temp", "count"]
MQTT_IQOS = 0                               # IQOS: 0: Message deleted, does not survive failures, no duplicates
                                            # IQOS: 1: Message stored, survives connection loss, duplicates possible
                                            # IQOS: 2: Message stored, survives connection loss, no duplicates
MQTT_IRETAIN = 0                            # Keep this as 0 to not retain message on server

WIFI_MAX_SSID_LEN = 32                      # RNWF02 v1/2 & RNWF11 max SSID length
WIFI_MAX_PW_LEN = 128                       # RNWF02 v1/2 & RNWF11 max passphrase length
WIFI_SECURITY_LIST = [0, *range(2, 9, 1)]   # RNWF02 v1/2 & RNWF11 security options 0, 2-9 (1 not supported)
WIFI_SHOW_BLANK_SSID = False                # Set to False for release. Blocks reported blank SSID's. Set to True for debug.

# # -----------------------------------------------------------------------------

# APP OS Return/Error codes
APP_RET_OK = 0
APP_RET_COM_NOT_FOUND = 1
APP_RET_COM_BUSY = 2


def detect_port(com_ports: list, supported_pn: dict) -> tuple:
    """ Detect the connected COM port by sending +GMM command to each
        USB UART port and testing against the supported dict devices.
    """
    # Loop through supported part numbers to find the connected device
    # supported_pn: type 'SUPPORTED_RNS_DICT' = {"RNWF02": ("PIC32MZW2", "RNWF02"), next device...
    for device, val in supported_pn.items():
        for signature in val:
            #print(f'Signature:{sig} is a {device} device')
            for port in com_ports:
                rx_data = []
                try:
                    s = serial.Serial(port=port, baudrate=230400, bytesize=serial.EIGHTBITS, 
                                      parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, 
                                      timeout=4.0, write_timeout=4.0, inter_byte_timeout=0.5)
                    try:
                        sleep(0.2)
                        s.write(f'AT+GMM\r\n'.encode('UTF-8'))
                        sleep(0.2)
                        while s.in_waiting:
                            if s.in_waiting == 1:
                                break
                            c = s.readline()
                            c = c.decode('UTF-8').strip('\r\n').replace('"', '').replace('+GMM:', '')
                            rx_data.append(c)
                    except UnicodeDecodeError:
                        pass
                    try:
                        if len(rx_data) != 0:
                            if rx_data[1] == signature and rx_data[2] == 'OK':
                                s.close()
                                return device, port
                    except IndexError:
                        pass
                    s.close()

                except serial.SerialException:
                    pass
    return "", ""

def find_com_port() -> tuple:
    """ Attempts to find a COM port. If found returns a Windows
        compatible "COMx" string in a tuple. If not found the 
        returned string is empty.
    """
    ports = serial.tools.list_ports.comports()
    usb_com_ports = []

    if APP_DISPLAY_LEVEL >= APP_DISPLAY_DECODES:
        print('  USB COM Ports Detected\n  ----------------------')
    for port, desc, hwid in sorted(ports):
        if hwid.find("USB ") != -1 and APP_DISPLAY_LEVEL >= APP_DISPLAY_DECODES:
            print("    {}: [{}]".format(port, hwid))
        # Check for the USB com ports, i.e. not Bluetooth, etc
        if hwid.find("USB") != -1:
            # Save USB ports in a list so we can find
            usb_com_ports.append(port)

    for i in range(3):
        os.system('cls')  # Clear terminal screen
        print(f'\n\nDetecting COM ports...({i+1} of 3)')
        port, device = detect_port(usb_com_ports, SUPPORTED_RNS_DICT)
        if port:
            os.system('cls')  # Clear terminal screen
            break
    return port, device


class Polling_KB_CMD_Input:
    """ Class is used to poll the keyboard for character and word commands from the user.
    """
    def __init__(self) -> None:
        self.kb = kbhit.KBHit()
        self.input_buf = ""
        self.cmd = ""               # Word commands
        self.key_cmd = ""           # Single key commands
        # Single key commands from the CLI
        self.EXIT_KEY = 27          # ESC

        self.key_commands = [COUNT_KEY, BUTTON_KEY, TEMP_KEY, REPORT_RATE_KEY, REPORT_RATE_INF_KEY, RESUME_KEY, DISCONN_KEY, HELP_KEY]

    def poll_keyboard(self, enable_key_cmds: bool) -> bool:
        """ Routine polls the keyboard for both single key commands and word commands. The parameter 'enable_key_cmds' 
            is set to 'True' to support both. When passed a 'False', key commands, except for 'ESC', are ignored for 
            full CLI word commands or text input.
        """
        if self.kb.kbhit():
            c = self.kb.getch()
            # RAW_CODE
            # Need the raw code to detect CTRL or SHIFT modifiers
            if EN_RAW_CODE_DISPLAY:
                print(f'Raw KeyCmd: {str(ord(c))}\n')                   # Set to string because CTRL+I displays as a Tab!

            if c == REPORT_RATE_INF_KEY:
                c_upper = REPORT_RATE_INF_KEY
            else:
                c_upper = c.upper()
            if len(c) == 0:
                return True
            
            if ord(c) == self.EXIT_KEY:                                 # Single key 'ESC' is always supported
                return False

            # Limit key_cmd registration to 1st buffer char only
            if enable_key_cmds == True:                                 # Single key commands SUPPORTED
                if len(self.input_buf) == 0:
                    for self.key_cmd in self.key_commands:
                        if self.key_cmd == c_upper or self.key_cmd == ord(c_upper):
                            break
                        else:
                            self.key_cmd = ''

                if self.key_cmd:
                    # print(f'KeyCmd: {self.key_cmd} ')
                    self.cmd = ''
                    self.input_buf = ''
                    return True                                         # Return immediately for processing

            if LOCAL_ECHO:
                # Handle backspace for end user
                if c == '\b':
                    print(f'\b \b', end='', flush=True)
                    if len(self.input_buf) > 0:
                        self.input_buf = self.input_buf.rstrip(self.input_buf[-1])
                else:
                    print(c, end='', flush=True)
                    self.input_buf += c
            if ord(c) == 13:  # Carriage Return (CR)
                self.cmd = self.input_buf
                self.key_cmd = ""
                self.input_buf = ""
        return True

    def cmd_get(self) -> str:
        return self.cmd

    def cmd_received(self) -> bool:
        if self.cmd != "":
            return True
        else:
            return False

    def cmd_clear(self) -> None:
        self.cmd = ""

    def __del__(self) -> None:
        self.kb.set_normal_term()

class Delay_Non_Blocking:
    def __init__(self) -> None:
        self.isStarted = False
        self.time_start = 0

    def start(self) -> bool:
        """ Called to start a non-blocking delay. Time is only reset or started if the timer is currently NOT runnning
            :return: isStarted
        """
        if self.isStarted == False:
            self.time_start = time.time()
            self.isStarted = True
        return self.isStarted

    def stop(self) -> None:
        """ Stops the non-blocking delay clock.
        """
        self.isStarted = False
        self.time_start = 0

    def delay_sec_poll(self, delay_sec: int) -> bool:
        """ Non-blocking delay class returns True if the passed time (Sec) is exceeded. On a
              True return the timer is cancelled.
              :param delay_sec: Seconds of delay
              :return: True - Time exceeded.
             False - Time was NOT exceeded OR timer was NOT started
        """
        if time.time() - self.time_start > delay_sec:
            self.stop()  # self.isStarted = False
            return True
        else:
            return False


class IotCloud:
    def __init__(self, port: str, baud: int, model: str) -> None:
        """ Primary class to handle the app including Wi-Fi, MQTT,
            user interface, etc        
        """
        self.__version__ = APP_REL_VERSION

        # initialize class variables
        self.ser_buf = ""  # serial buffer for processing messages

        # main application state
        self.app_state = APP_STATE_INIT         # INIT must be first to initialize key variables
        self.app_state_prev = -1
        self.app_sub_state = 0
        self.app_sub_state_check = 0
        self.app_check = 0
        self.app_wait = False
        self.next_sub_state_offset = 1

        # firmware Syntax for parse RNFW02v1: '+GMR:"1.0.0 0 630f6fcf [13:57:15 Jun 27 2023]"'
        # firmware Syntax for parse RNFW02v2: '+GMR:"2.0.0 0 e41f977cb [16:31:26 Apr 12 2024]"'
        # firmware Syntax for parse RNFW11v1: '+GMR:"78de24c4 [09:48:06 Nov  2 2023]"'
        self.fw_version = "Not Reported"
        self.fw_sec_version = "Not Reported"
        self.fw_hash = "Not Reported"
        self.fw_datestamp = "Not Reported"

        self.dev_model = model
        self.dev_com_port = port

        self.log_file_handle = ""       # Log file handle if created

        self.pub_topic = ""
        self.pub_payload = ""

        # wifi connection related variables
        self.wifi_connected = False     # Set to True when WiFi connected
        self.wifi_ap_sta = '???'                # AT+ASSOC; 0=AP, 1=Station
        self.wifi_assoc_id = '?'                # ASSOC ID 
        self.wifi_bssid = '00:00:00:00:00:00'   # AT+ASSOC; MAC of AP connected to
        self.wifi_rssi = '???'                  # AT+ASSOC; RSSI of AP in dbm  
        self.wifi_reg_domain = ""               # Wi-Fi regulatory domain; eg: 'GEN', 'USA' or 'EMEA'
        self.wifi_reg_domain_available = ""     # Wi-Fi regulatory domains available in flash 'GEN','USA','EMEA'
        

        # DPS connection variables
        self.broker_connected = False  # set to True when connected to DPS broker

        # IOTC connection variables
        self.iotc_topic_index = 1  # tracks how many topics have been subscribed to for
        # iotc event call back to adjust the state variable.

        # IOTC Demo variables
        self.iotc_button = True                 # Telemetry: "button" toggle reported to cloud initial value
        self.iotc_count = 0                     # Telemetry: "count" reported to cloud initial value
        self.iotc_temp = 78.0                   # Telemetry: "temp" reported to cloud initial value

        self.telemetry_interval = 0             # Property: Telemetry interval
        self.ip_addr_ipv4 = 'n/a'               # Property: IP Address reported to cloud
        self.ip_addr_ipv6 = 'n/a'               # IP Address returned from router
        self.mac = ''                           # MAC address of the module "AT+NETIFC=0, 2" (with colons)
        self.telemetry_ints = [0, 1, 2, 5, 10]  # Demo state supported telemetry intervals in seconds
        self.telemetry_index = 0                # Demo state index to current telemetry interval
        self.demo_loops = 0                     # Max number of telemetry updates in Demo state

        self.last_utc_update = 0            # Update this each time the time signal come in
        self.resp_dict = {"button":" ",
                          "count": " ",
                          "temp": " "
                          }
        self.reboot_timer = Delay_Non_Blocking()

        self.at_quiet_command = False       # Disable CLI command output for 1 cmd before reset
        self.at_command = ""                # The AT command currently being executed
        self.at_command_prev = ""           # Previously executed AT command
        self.at_command_resp = ""           # Alt 'response' to use if the command itself isn't the desired response

        self.at_command_timer = Delay_Non_Blocking()
        self.at_command_timer.stop()
        self.at_command_timeout = AT_COMMAND_TIMEOUT  # AT command timeout. Commands must complete within this many seconds

        self.mqtt_client_id = ""            # Client ID = MODEL + last 4 MAC Address bytes. eg: "RNWF02_0D-AA-EF"
                                            # Size of the MQTT Read Threshold buffer if needed "AT+MQTTC=9, 700"
        self.mqtt_read_sz = MQTT_MINIMUM_READ_THRESHOLD_SZ                

        # Read these params from the configuration.cfg file
        self.ca_cert_name = iotp.params["ca_cert_name"]             # Certificate Authority certificate name
        self.mqtt_root_topic = iotp.params["mqtt_root_topic"]       # Decoded MQTT root topic taking into account %M, %N variables [Automatic]
        self.mqtt_sub_topic = iotp.params["mqtt_sub_topic"]         # Decoded MQTT sub-topic taking into account %M, %N variables [OPTIONAL]
        self.mqtt_subscription = iotp.params["mqtt_subscription"]   # Subscription string read from config. Default is '#' for all sub fields

        self.mqtt_field_list = MQTT_FIELDS                          # Hard coded MQTT fields to use from the constant MQTT_FIELDS above

        self.evt_handler = None

        self.SER_TIMEOUT = 0.1  # sets how long pySerial will delay waiting for a character
        #   reading a character a time, no need to wait for long messages

        try:
            self.ser = serial.Serial(self.dev_com_port, baud, timeout=self.SER_TIMEOUT)
        except:
            print(f'  Serial port open FAILED. Is {self.dev_com_port} in use?')
            exit(APP_RET_COM_BUSY)
        self.delay = Delay_Non_Blocking()
        self.kb = Polling_KB_CMD_Input()

        self.open_log()                             # Start the log file

    def get_topic(self, data_field: str = '') -> str:
        """ Constructs a MQTT topic path string and returns the result. Supports passing
            in the requested data field, or not and supports a blank sub-topic too.        
        """
        if self.mqtt_sub_topic == '':     # If the sub topic path is blank...
            if data_field == '':
                return f'{self.mqtt_root_topic}'
            else:
                return f'{self.mqtt_root_topic}/{data_field}'
        else:                                       # Else include the sub-topic path too...
            if data_field == '':
                return f'{self.mqtt_root_topic}/{self.mqtt_root_topic}'
            else:
                return f'{self.mqtt_root_topic}/{self.mqtt_root_topic}/{data_field}'

    def chk_ss(self, set_check = 1) -> bool:
        """ Resets and/or returns the internal 'check' variable used by the state machine
            as the sub-state value. This replaced all constant value checks in if-else's.
        """
        if set_check == APP_STATE_BEGIN:
            self.app_sub_state_check = 0
        elif set_check == APP_STATE_COMPLETE:
            self.app_state += 1
            self.app_sub_state = self.app_sub_state_check = APP_STATE_BEGIN
        else:
            self.app_sub_state_check += set_check

        return bool(self.app_sub_state_check == self.app_sub_state)

     
    def get_topic_name(self, topic: str) -> str:
        """ Decodes topic string from the config file, encodes the requested 
            fields and returns the string.
        """
        topic = topic.replace("%m", "%M").replace("%M", self.dev_model)
        topic = topic.replace("%n", "%N").replace("%N", self.mac.replace(":", "-"))
        return topic

    def get_topic_path(self) -> str:
        """ Returns the correct topic path based on the class variables
            'mqtt_root_topic' and 'mqtt_sub_topic'.        
        """
        if len(self.mqtt_sub_topic):
            topic = f'{self.mqtt_root_topic}/{self.mqtt_sub_topic}'
        else:
            topic = f'{self.mqtt_root_topic}'
        return self.get_topic_name(topic)

    def set_log_file_name(self) -> tuple:
        """ Decodes and sets the global APP_CMD_LOG_FILE
            and returns the constructed log 'filename' and the
            datetime object for its creation.
        """
        file_name = globals()["APP_CMD_LOG_FILE"]

        now = datetime.now()
        t: str = now.strftime("%H-%M-%S")                           # Get the Time string
        d: str = now.strftime("%b_%d_%Y")                           # Get the Date string
        c: str = str(pathlib.Path(iotp.filename)).split('.')[0]     # Get the config filename w/o extension
        
        dir, c = os.path.split(c)
        file_name = file_name.replace("%m", "%M").replace("%M", self.dev_model)     # Add Module name to log filename
        file_name = file_name.replace("%d", "%D").replace("%D", d)                  # Add Date to log filename
        file_name = file_name.replace("%t", "%T").replace("%T", t)                  # Add Time to log filename
        file_name = file_name.replace("%c", "%C").replace("%C", c)                  # Add Config filename to log filename

        globals()["APP_CMD_LOG_FILE"] = file_name
        return file_name, now

    def open_log(self) -> None:
        """ Sets the logfile handle, if applicable and opens the log file for writing 
        """
        file_name, now = self.set_log_file_name()

        if file_name:
            try:
                logfile = f'{globals()["APP_CMD_LOG_PATH"]}/{file_name}'
                directory = os.path.dirname(logfile)
                if not os.path.exists(directory):
                    os.makedirs(directory)
                self.log_file_handle = open(f'{logfile}', "w+")
            except:
                banner(f' ERROR: Log file could not be created or written\n'
                       f'           Verify {APP_CONFIG_FILE} \'log\' syntax\n',
                       BANNER_BORDER_LEV_1)
                # print("\n")
                self.log_file_handle = None
                pass
            else:
                self.log_file_handle.write(f'Out-Of-Box MQTT Demonstration Command Log v{self.__version__}\n')
                self.log_file_handle.write(f'{"-" * 46}\n')
                self.log_file_handle.write(f'Filename:  {file_name}\n')
                self.log_file_handle.write(f'Config:    {ARGS.cfg}\n')
                self.log_file_handle.write(f'Created:   {now.strftime("%b %d, %Y")} {now.strftime("%H:%M:%S")}\n')
                self.log_file_handle.write(f'Model:     {self.dev_model}\n')
                self.log_file_handle.write(f'COM Port:  {self.dev_com_port}\n')
                self.log_file_handle.write(f'{"-" * 46}\n\n')
        else:
            self.log_file_handle = None

    def log_state(self, msg: str, border_char: str = '#', single_line: bool = False) -> None:
        """ Adds a banner in the log if log is used
        """
        if self.log_file_handle:
            str_caps = f'{border_char * 4}'
            min_msg_len = 34
            msg = f' {msg:^{min_msg_len}} '
            msg = f'{str_caps} {msg} {str_caps}'
            if single_line is True:
                self.log_file_handle.write(f'{msg}\n')
            else:
                self.log_file_handle.write(f'{border_char * len(msg)}\n{msg}\n{border_char * len(msg)}\n')
            self.log_file_handle.flush()

    def cmd_log(self, msg: str) -> None:
        """ Outputs the CMD/RSP strings to the CLI and optional log file.
            If the 'self.at_quiet_command' bool is True, screen output is suppressed. Log 
            output is never suppressed.
        """

        # Remove any NULL's returned by the device such as during AT+RST
        msg = ''.join(msg.split('\x00'))
        # msg = msg.strip('\n')
        if "CMD[" in msg or "CRx[" in msg:
            if self.at_quiet_command is False:
                print(f'{msg}\n', flush=True, end='')
            if self.log_file_handle:  # Print to LOG file if enabled
                self.log_file_handle.write(f'{msg}\n')
                self.log_file_handle.flush()

        elif "RSP[" in msg:         # Print to CLI
            if self.at_quiet_command is False:
                print(f'{msg}\n', flush=True, end='')
            if self.log_file_handle:  # Print to LOG file if enabled
                self.log_file_handle.write(f'{msg}\n\n')
                self.log_file_handle.flush()
        else:
            if self.at_quiet_command is False:
                print(f'{msg}', flush=True, end='')
            if self.log_file_handle:                       # Print to LOG file if enabled
                self.log_file_handle.write(f'{msg}\n')
                self.log_file_handle.flush()

    def wifi_validate(self) -> bool:
        """ Tests the 3 Wi-Fi parameters for correctness and returns True if ok, False otherwise.
            If this test fails, wifi_ssid, wifi_passphrase & wifi_security are set to an empty strings.

            wifi_ssid: < 32 bytes long, spaces allowed
            wifi_passphrase: < 128 bytes long, NO spaces. Blank only if security == 0.
            wifi_security: Numeric containing 0, 2-9
        """
        ret_val = True
        # Blank check
        if iotp.params["wifi_ssid"] == "" or iotp.params["wifi_security"] == "":
            ret_val = False
        # Security value check
        elif iotp.params["wifi_security"].isnumeric() == False or (int(iotp.params["wifi_security"]) in WIFI_SECURITY_LIST) == False:
            ret_val = False
        # Passphrase 'blank space' with security set to non-zero        
        elif (iotp.params["wifi_passphrase"] == '') and int(iotp.params["wifi_security"]) != 0:
            ret_val = False
        # Passphrase is set but security is non-zero        
        elif (len(iotp.params["wifi_passphrase"])) and (iotp.params["wifi_security"] == '0' ):
            ret_val = False
        # Wi-Fi SSID max length check
        elif len(iotp.params["wifi_ssid"]) > WIFI_MAX_SSID_LEN:
            ret_val = False
        # Wi-Fi Passphrase length check
        elif len(iotp.params["wifi_passphrase"]) > WIFI_MAX_PW_LEN:
            ret_val = False

        if ret_val:
            return True
        iotp.params["wifi_ssid"] = ""
        iotp.params["wifi_security"] = ""
        iotp.params["wifi_passphrase"] = ""
        return False

    def is_subscribed_mqtt(self, val_true: any = True, val_false: any =False) -> any:
        """ Checks if the 'app.cfg' has a 'mqtt_subscription' has a subscription string set.
            If so, it returns 'val_true' otherwise 'val_false' is returned.        
        """
        if self.mqtt_subscription != '':
            return val_true
        return val_false

    def is_primary_mqtt(self, val_true: any = True, val_false: any =False) -> any:
        """ Checks to see if 'this' module is the primary by comparing the 'mqtt_root_topic'
            string and 'self.mqtt_client_id'. If they are the same 'val_true' is returned, otherwise val_false
        """
        if iotp.params["mqtt_root_topic"] == self.mqtt_client_id:
            return val_true
        return val_false    
    
    def is_tls(self, val_true: any = True, val_false: any = False) -> any:
        """ Checks if the connection is to be TLS encrypted. This controls sending TLS and SNTP commands. 
            Since SNTP is only needed for TLS it grouped with the TLS check. If this test true the 'val_true'
            parameter is returned. Otherwise the 'val_false' parameter is returned.
        """
        if int(iotp.params["mqtt_broker_port"]) > 7999:
            return val_true
        return val_false

    def is_model(self, model: str, fw_ver: str = "*", val_true: any = True, val_false: any = False) -> any:
        """ Verifies device MODEL & Firmware version and returns the value passed as param 3 if true,
            or param 4 if false. Parameters 3 & 4 default to boolean, but can be overridden if passed in.
        """
        if model == self.dev_model and (fw_ver == "*" or self.fw_version == fw_ver):
            return val_true
        return val_false
    
    def is_state_demo(self, val_true: any = True, val_false: any = False) -> any:
        """ Verifies state machine's state is in the demo. Parameters 2 & 3 default to boolean, but can be overridden if passed in.
        """
        if self.app_state == APP_STATE_DEMO:
            return val_true
        return val_false

    def random_delta_temp(self) -> float:
        """ Returns a random temperature delta that is guaranteed to be a non-zero value.
        """
        delta_temp: float = 0.0
        while (delta_temp == 0.0):
            delta_temp = round((random.randrange(-50, +50) / 10), 1)
        return float(delta_temp)
    
    def hex_rid(self, rid: int = -1) -> str:
        """ Converts class 'self.rid' into a hex string w/o '0x' prefix for some MQTT commands.
            If passed an int, will set self.rid prior to string conversion
        """
        if rid != -1:
            self.rid = rid
        return f'{self.rid:x}'  # Converts dec value passed to a hex w/o '0x'

    def set_rid_from_string(self, rid_str: str) -> None:
        """ Sets the class 'rid' if found in passed in string. If not found class rid remains unchanged.
            The 'rid' value is hex without the prefix '0x' and must increment as such."""
        #rid_str = '+MQTTSUBRX:0,0,0,"$iothub/methods/POST/echo/?$rid=1","{\\"echoString\\":\\"hello\\"}"'
        if rid_str.find('rid=') != -1:
            try:
                rid_str = self.substr_swap(rid_str, {'"': ''})
                tmp_list = rid_str.split('rid=')
                tmp_list = str(tmp_list[1]).split(',')
                self.rid = int(tmp_list[0], 16)
            except:
                # self.cmd_log(f'\nWarning: Invalid "{self.rid = }" detected in "set_rid_from_string()"\n')
                pass

    # keyboard processing
    def kb_data_process(self, received: str) -> bool:
        """ Process a passed in str and returns True if an AT+
            command or False if its a FS (File System) command.
            If a FS command that command is saved in the class.
        """
        if received.startswith("AT"):
            self.pub_topic = ""
            self.sub_topic = ""
            return True
        return False

    def set_sub_state(self, sub_state_offset: int) -> None:
        """ Updates the current sub-state by the offset passed.
        """
        self.app_sub_state += sub_state_offset

    def set_state_direct(self, new_state: int, new_sub_state: int = 0) -> None:
        """ Sets the state and optional sub-state directly (not an offset).  If the sub_state
            is not passed, the default 0 is used showing the state banner.
        """
        if APP_STATE_CLI <= new_state <= APP_STATE_DEMO:
            self.app_state_prev = self.app_state
            self.app_state = new_state
            self.app_sub_state = new_sub_state

    def cmd_kill(self, exit_to_cli: bool = False) -> None:
        """ Called to terminate an outstanding AT+ command and reset
            variable to an all a new command execution.
            If 'exit_to_cli' is set to 'True', the state machine is directed
            to exit to the CLI. If set to 'False', the state machine is not redirected
            and allowed to continue execution.       
        """
        if self.at_command_timer.isStarted:
            self.at_command_timer.stop()
            self.at_command_prev = self.at_command
            self.at_command = ""
            self.at_command_resp = ""
            self.at_command_timeout = 0
            self.app_wait = False
            self.at_quiet_command = False
        if exit_to_cli:
            self.set_state_direct(APP_STATE_CLI, APP_STATE_BEGIN) 

    def cmd_check(self, terminate: bool = False) -> None:
        """ Checks running AT commands against time out period. If timeout is
            exceeded, the command is cancelled. To force a command to stop,
            pass 'True'. Returns True if command was not terminated and
            'False' if it was".
        """
        # kill_cmd = terminate
        if self.at_command_timer.isStarted and self.at_command == "":
            # dbg_banner(f'Command Timer AutoKill - No command outstanding')
            self.at_command_timer.stop()
        if self.at_command_timer.isStarted and self.at_command:
            run_time = time.time() - self.at_command_timer.time_start
            if run_time > self.at_command_timeout:
                # banner(f' Command "{self.at_command}" timed out after {run_time:.2f}s', "▫")
                # print(f'\n')
                self.cmd_log(f'Command "{self.at_command}" timed OUT after {run_time:.2f}s')
                print(f'\n')
                self.cmd_kill(self.is_state_demo(False, True))              # Only exit to CLI if NOT in demo state
                err_sig = f'{self.app_state:0>2}:{self.app_sub_state:0>2}'

                # Special handling of time critical command calls
                if err_sig == '02:12':
                    self.err_handler(run_time, f'AT+SNTPC=3,"{iotp.params["ntp_server_ip_addr"]}" [ER]:NTP server did not respond @ [{err_sig}]', '01:09')
                # other elif go here
                else:
                    pass
                # Make sure this is last
                # self.set_state_direct(APP_STATE_CLI)
            elif terminate:
                banner(f' Command \'{self.at_command}\' terminated at {run_time:.2f}s', '▫')
                self.cmd_kill(self.is_state_demo(False, True))              # Only exit to CLI if NOT in demo state

    def cmd_issue_quiet(self,
                  command: str,
                  next_sub_state_offset: int = 0,
                  alt_resp: str = "",
                  timeout: int = AT_COMMAND_TIMEOUT) -> None:
        self.at_quiet_command = True
        self.cmd_issue(command, next_sub_state_offset, alt_resp, timeout)
        """ This is an alternate function to submit AT+ commands but blocks CLI screen output.
            If a log file is used the command will appear in the logs.
            Also the defaults 'next_sub_state_offset' is set to '0' so that it can be used
            during startup and not increment the programmed sub-state.
        """

    def cmd_issue(self,
                  command: str,
                  next_sub_state_offset: int = 1,
                  alt_resp: str = "OK",
                  timeout: int = AT_COMMAND_TIMEOUT) -> None:
        command = self.substr_swap(command, {'\r': '', '\n': ''})
        """ Primary method of sending a 'AT+ command with its command and return displayed and logged."""

        # Debug support for NOOP command without any processing
        if command == "NOOP":
            # self.cmd_log(f'CMD[{self.app_state:0>2}.{self.app_sub_state:0>2}]: NOOP - Internal "No Operation" command')
            # self.cmd_log(f'RSP[{self.app_state:0>2}.{self.app_sub_state:0>2}]: NOOP - Complete')
            # print("\r")
            self.app_sub_state += next_sub_state_offset
            return
        if self.at_command == "":  # If empty, it means no AT commands are 'pending'
            self.at_command = command
            self.at_command_timeout = timeout
            if alt_resp == "":
                self.at_command_resp = command  # Save cmd to verify returned response
            else:
                self.at_command_resp = alt_resp  # Save the alternate, passed in response instead
            self.next_sub_state_offset = next_sub_state_offset
        else:
            banner(f' AT Command still processing:\n  Command Pending:  {self.at_command}\n' f'  Command Not Sent: {command}')
            return

        self.cmd_log(f'CMD[{self.app_state:0>2}.{self.app_sub_state:0>2}]: {command.lstrip().strip()}')

        # Send the AT command and add required '\r\n'
        self.at_command_timer.stop()  # Reset the command timer
        self.ser.write(bytearray(self.at_command + '\r\n', 'utf-8'))
        self.at_command_timer.start()  # Start command timer
        self.app_wait = True  # Enable command wait for completion

    def serial_receive(self) -> str:
        """ Polled serial receive function. Reads until the prompt is found '>'.
            Reads entire message.
        """
        read_val = self.ser.read(1)
        if read_val != b'':
            self.ser_buf = self.ser_buf + read_val.decode('utf8', errors='backslashreplace')
            if read_val == b'>':
                ret_val = self.ser_buf
                self.ser_buf = ""
                return ret_val
        return ""

    # subscribe to MQTT topic
    def mqtt_subscribe(self,
                       topic: str,
                       iQOS: int,
                       next_step: int = 1,
                       alt_resp: str = "",
                       timeout: int = AT_COMMAND_TIMEOUT):
        """ MQTT Subscription function used to construct the subscription string before
            sending it to the module for execution.
        """
        cmd = "AT+MQTTSUB=" + '\"' + topic + '\",' + str(iQOS)
        return self.cmd_issue(cmd, next_step, alt_resp, timeout)

    # publish to MQTT topic
    def mqtt_publish(self,
                     iQoS: int,
                     iRetain: int,
                     strTopic: str,
                     strPayload: str,
                     next_step: int = 1,
                     alt_resp: str = "",
                     timeout: int = AT_COMMAND_TIMEOUT):
        """ Publishes a MQTT payload to a topic passed in. First parameter is hard coded to '0'
            for Duplicate Message == New Message.
        """
        try:  # try block looks for CR, and removes it if present before joining CMD
            loc = strPayload.index('\r')
        except ValueError:
            pass
        else:
            strPayload = strPayload[0:loc]
        cmd = "AT+MQTTPUB=0," + str(iQoS) + ',' + str(iRetain) + ',\"' + strTopic + '\",\"' + strPayload + '\"'

        # dbg_banner(f' MQTTPUB Command:\n  {cmd}', '=')
        return self.cmd_issue(cmd, next_step, alt_resp, timeout)

    def evt_init_error(self) -> None:
        self.app_sub_state = APP_STATE_COMPLETE
        banner( f' Error: Initialization failure\n'
                          f'Verify AT commands:\n'
                          f'  \'+ATE1\'  - Set local echo\n'
                          f'  \'+WSTAC\' - Wi-Fi config', BANNER_BORDER_LEV_1)

    def evt_ntp_received(self, rx_data: str) -> None:
        """ Decodes and stores NTP (time) string in class """
        # Get the returned UCT(s) from the returned string
        # i.e. "+TIME:3896263328\r\n>"
        try:
            self.last_utc_update = int("".join(filter(str.isdigit, rx_data)))
        except:
            self.last_utc_update = 1

    def user_prompt_int(self, int_min: int, int_max: int, prompt_str: str) -> bool | int:
        """ Very simple user input prompt for an integer within a known range        
        """
        user_int: int = 0

        print (f'{prompt_str}', end='', flush=True)
        while 1:
            poll = self.kb.poll_keyboard(False)         # Pass False to disable single char command support

            if poll == False:                           # ESC pressed to EXIT
                return False, 0
            else:
                if self.kb.cmd_received():
                    try:
                        user_int = int(self.kb.cmd_get().rstrip())
                        if user_int >= int_min and user_int <= int_max:
                            return True, user_int
                        else:
                            print (f'{prompt_str}', end='')
                    except:
                        print (f'{prompt_str}', end='')
                    finally:
                        self.kb.cmd_clear()


    def user_prompt_pw(self, pw_min_len: int, pw_max_len: int, prompt_str: str) -> bool | str:
            """ Simple user password prompt that checks for min, max length and no spaces.
                Returns 2 variables, bool status & str password entered.
            """
            user_pw: str = 0

            print (f'{prompt_str}', end='')
            while 1:
                poll = self.kb.poll_keyboard(False)     # Pass False to disable single char command support

                if poll == False:                       # ESC pressed to EXIT
                    return False, 0
                else:
                    if self.kb.cmd_received():
                        try:
                            user_pw = self.kb.cmd_get().rstrip()
                            if bool(re.search(r"\s", user_pw)) == False and len(user_pw)>= pw_min_len and len(user_pw) <= pw_max_len:
                                return True, user_pw
                            else:
                                print (f'{prompt_str}', end='')  
                        except:
                            print (f'{prompt_str}', end='')
                        finally:
                            self.kb.cmd_clear()

    def evt_wifi_prompt_user(self, wifi_list: list, max_ssid_length) -> bool:
        """ Generates the user menu selection for Wi-Fi SSID & Passphrase"""    
        if self.app_state == APP_STATE_WIFI_CONNECT:        # Just display Wi-Fi scan results
            # row: int = 0
            row_select: int = 0
            # Prompt the user to select SSID from the menu
            passphrase: str = ''

            menu_num_len = 4                                    # Set the width of menu numbers. eg: "999." is 4
            col_space = f' '                                    # String used between columns
            banner(f'{"   Wi-Fi SSID Selection": ^{((max_ssid_length + menu_num_len + len(col_space)) * 2) - 8}}')

            if (len(wifi_list) % 2):                            # If list length is ODD, extend rows by 1
                max_row: int = int((len(wifi_list) / 2) + 1)
            else:                                               # Else list length is EVEN so equal length
                max_row: int = int((len(wifi_list) / 2))

            while 1:
                for row in range(0, max_row):                # Loop on the list
                    wifi_1 = wifi_list[row].split(',')
                    col2_index = int(row + (max_row))
                    print(f'{str(row):>{menu_num_len}}.{col_space}{wifi_1[4]:<{max_ssid_length}}', end='')         # Wi-Fi SSID col 1
                    
                    if col2_index < len(wifi_list): 
                        wifi_2 = wifi_list[col2_index].split(',')
                        print(f'{str(row + max_row):>{menu_num_len}}.{col_space}{wifi_2[4]:<{max_ssid_length}}', flush = True)
                    else:
                        print(f'', flush = True)
                            # These are all the fields we can show in the menu
                            # wifi[4]           # Wi-Fi SSID
                            # wifi[3]           # MAC address
                            # wifi[1]           # Wi-Fi Security type
                            # wifi[2]           # Wi-Fi Channel
                            # wifi[0]           # Signal strength in -dbm

                # User selection of a Wi-Fi AP to connect to
                result, row_select = self.user_prompt_int(0, len(wifi_list) - 1, f'\n  Select a Wi-Fi AP [ 0 ][ 1 - {len(wifi_list) - 1} ]: ')

                # User selected Wi-Fi rescan
                if row_select == 0 and result == True:
                    print (f'\n\n  Wi-Fi Re-scan Requested...')
                    self.set_state_direct(APP_STATE_WIFI_CONNECT, 0)
                    return result
                
                # User pressed ESC to leave to the CLI
                if result == False:
                    print (f' ESC\n')
                    self.set_state_direct(APP_STATE_CLI, 0)
                    return result 
                else:                           # User selected an AP index 1 to N or 0 for a Wi-Fi re-scan
                    wifi_select = list(wifi_list[row_select].split(","))
                    if wifi_select[1] == '0':                           # AP selection has no security
                        iotp.params["wifi_passphrase"] = ""             # Passphrase is empty
                    else: 
                        # Secure SSID so prompt for a passphrase                                              
                        result, passphrase = self.user_prompt_pw(1, WIFI_MAX_PW_LEN, f'\n  Enter the passphrase for \'{wifi_select[4]}\': ')
                        if result:
                            iotp.params["wifi_passphrase"] = passphrase # Passphrase set by the user
                        else:
                            print (f' ESC\n')
                            self.set_state_direct(APP_STATE_CLI, 0)
                            return result
                    iotp.params["wifi_ssid"] = wifi_select[4]           # SSID selected has no security
                    iotp.params["wifi_security"] = wifi_select[1]       # Security is '0'                    
                    iotp.write()                                        # Re-write config file with the Wi-Fi info
                    return result

    def evt_wifi_scan_result(self, rx: str) -> list | int | int:
        """ Outputs the Wi-Fi scan results and returns:
            1: wifi_list =          Wi-Fi list itself
            2: ssid_max_len =       Maximum length of SSID's
            3: ssid_skipped_count = SSID's name '[]' skipped and not shown
        """
        if len(rx):
            ssid_max_len: int = 0
            ssid_skipped_count: int = 0
            # Clean up the Rx string...simplifies parsing the string result
            rx = self.substr_swap(rx, {"\r": "","\n": "", "\0": "", '"': "", "+WSCNDONE:": "\n"})
            wifi_list = list(rx.split("+WSCNIND:"))                     # Split Rx & use '+WSCNIND:' as delimiters
            wifi_list[0] = '-0,0,1,FF:FF:FF:FF:FF:FF,RE-SCAN Wi-Fi'     # [0] Dummy entry for the Re-scan option

            for i in reversed(range(len(wifi_list))):
                try:
                    list_element = list(wifi_list[i].split(','))
                    if len(list_element[-1]) > ssid_max_len:
                        ssid_max_len = len(list_element[-1])

                    # Sometimes the module reports a SSID as '[]' so we remove those here because
                    # they won't work if the user selects them...Better to do a re-scan with the '0'
                    # menu option.
                    if (str(list_element[-1]).find("[]") != -1 and WIFI_SHOW_BLANK_SSID == False):
                        # print (f'Removed \'{list_element[-1]}\' @ wifi_list Index({i})')
                        del wifi_list[i]
                        ssid_skipped_count += 1
                except:
                    dbg_banner(f'Index warning in \'evt_wifi_scan_result(i = {i}\'')

            # Remove the SSID count from the last entry. eg: "SSID_NAME\n15>"
            last_ssid = wifi_list[-1].split("\n")       # Get the last SSID name from the full list & split at the '\n'
            
            # Uncomment the next 2 lines to see how many SSID's were encoded in the Wi-Fi list returned
            # reported_count = self.substr_swap(last_ssid[1], {">": ""})
            # dbg_banner(f'Module Reported SSID Count: {reported_count}')                 
            
            wifi_list[-1] = last_ssid[0]                # Replace the encoded SSID count from the list

            # If we want the reported SSID count, we can decode it from the last SSID name. eg: "SSID_NAME\n15>" -> Count = 15
            # if len(last_ssid) > 0:                      # Remove the '>' and convert to an integer
            #     ssid_count = int(self.substr_swap(str(last_ssid[1]), {">": ""}))

            return wifi_list, ssid_max_len, ssid_skipped_count

    def evt_fs_data_result(self, rx: str) -> None:
        """ Outputs file system (FS) results for DIR, DEL and SYS commands """
        if len(rx):
            create_file_list = lambda str_data: re.findall(r'"([^"]*)"', str_data)
            # Use regX to convert the rx string into a python 'list' of file names
            #      file_list = re.findall(r'"([^"]*)"', rx)
            file_list = create_file_list(rx)
            # Create single line response line
            resp_list = rx.split('\r\n', -1)
            # file_list.clear()
            if "+FS=4" in rx:  # File SYStem info
                rx = self.substr_swap(rx, {">": "", "OK": "", "\r": "", "\n": ""})
                fs_status_list = rx.split(',', 3)
                reg_dom_str: str = ""

                if self.wifi_reg_domain != "":
                    reg_dom_str = f'\nWi-Fi Configuration (AT+WIFIC)\n' \
                       f'  Regulatory Domain:   {self.wifi_reg_domain}\n'
                    
                banner(
                       f'  Model Info (AT+GMM)\n'
                       f'  Model:               {self.dev_model}\n\n'
                       f'Firmware Info (AT+GMR)\n'
                       f'  Version:             {self.fw_version}\n'
                       f'  Security:            {self.fw_sec_version}\n'
                       f'  Date:                {self.fw_datestamp}\n'
                       f'  Hash ID:             {self.fw_hash}\n\n'
                       f'Network Interface Info (AT+NETIFC)\n'
                       f'  MAC Address:         {self.mac}\n\n'
                       f'Wi-Fi Station Mode Configuration (AT+WSTA=1)\n'
                       f'  IP Address IPv4:     {self.ip_addr_ipv4}\n'
                       f'  IP Address IPv6:     {self.ip_addr_ipv6}\n'
                       f'  Wi-Fi Connected:     {self.wifi_connected}\n'
                       f'  Broker Connected:    {self.broker_connected}\n\n'
                       f'File System Info (AT+FS=4)\n'
                       f'  Free Space:          {fs_status_list[1]} bytes\n'
                       f'  File Handles:        {fs_status_list[2]}\n\n'
                       f'Wi-Fi Association Report (AT+ASSOC)\n'
                       f'  AP/STA:              {self.wifi_ap_sta}\n'
                       f'  BSSID:               {self.wifi_bssid}\n'
                       f'  RSSI:                {self.wifi_rssi}dBm\n'
                       f'{reg_dom_str}'
                       )
            elif "+FS=2" in rx and EN_CERT_SUPPORT:  # File system DIR (List)
                if "+FS=2,1" in rx:
                    cert_type = f' Dir Certificates ({len(file_list)}) '
                else:
                    cert_type = f' Dir Keys ({len(file_list)}) '
                #self.cmd_log(f'RSP[{self.app_state:0>2}.{self.app_sub_state:0>2}]: {resp_list[1]}') #, flush=True)
                banner(cert_type)
                cnt = 1
                for files in file_list:
                    print(f'{cnt:<5}"{files}"')
                    cnt += 1
                print("\n\r")
            elif "+FS=3" in rx:  # File system DEL
                pass
                # print(f'RSP[{self.app_state:0>2}.{self.app_sub_state:0>2}]: {resp_list[0]}', flush=True)
                # print(f'            {resp_list[1]}\r\n', flush=True)
            else:
                print(rx)
            self.at_command_prev = self.at_command
            self.at_command = ""

    def evt_gmr_data_result(self, rx: str) -> None:
        """ Stores AT+GMR command results """

        if (len(rx)):
            rep_str = 'Not Reported'
            self.fw_version = self.fw_hash = self.fw_datestamp = rep_str
            try:
                # +GMR:"1.0.0 0 7797bc1b4 [14:57:25 Jan 18 2024]" [OK]  <-Rio-0 v2 Alpha (extra hash char)
                # +GMR:"1.0.0 0 28265450 [15:43:24 Jul 25 2023]"        <-Rio-0 v1 Release (previous support)
                # +GMR:"78de24c4 [09:48:06 Nov  2 2023]"                <-Rio-2 v1 Release (missing version & '0')
                to_remove = {'"': '', '[': '', ']': '', '>': '','0x': '', '0X': '',
                             '\r\n': '', 'AT+GMR': '', '+GMR:': '', 'OK': ''}
                parsed = self.substr_swap(rx, to_remove)
                parsed = ' '.join(parsed.split())
                parsed = parsed.split(' ')

                for item in parsed:
                    if len(item) < 1 or item == '0':
                        continue
                    # Only check for '.' as the FW version is the only item containing periods
                    elif item.__contains__('.') and self.fw_version == rep_str:
                        self.fw_version = f'{item}'
                        self.fw_sec_version = f'{parsed[1]}'
                        continue
                    # Use RegX on item; if it is a hex then it must be the hash
                    # Also add on the lone '0' char; Assuming this is a build number??
                    elif len(item) > 5 and re.match("^[0-9A-Fa-f]+$", str(item)):
                        self.fw_hash = item
                    # If a ':' is present we must be at the start of the time stamp
                    elif item.__contains__(':') and self.fw_datestamp == rep_str:
                        self.fw_datestamp = f'{item}'
                    else:
                        # Final else completes the time stamp with Mon, Day and Year
                        self.fw_datestamp += f' {item}'
            except:
                self.fw_version = "???"
                self.fw_sec_version = "?"
                self.fw_hash = "???"
                self.fw_datestamp = "???"

            if APP_DISPLAY_LEVEL >= APP_DISPLAY_INFO:
                banner_str = (f' Firmware Info:\n'
                              f'  Version:     {self.fw_version}\n'
                              f'  Security:    {self.fw_sec_version}\n'
                              f'  Date:        {self.fw_datestamp}\n'
                              f'  Hash ID:     {self.fw_hash}')
                banner(banner_str)

    def evt_wifi_connected(self) -> None:
        """ Outputs Wi-Fi status on change """
        if APP_DISPLAY_LEVEL >= APP_DISPLAY_INFO:
            # Create the Wi-Fi data from the +ASSOC command
            wifi_info: str = f'\n' \
                             f'  SSID:          \'{iotp.params["wifi_ssid"]}\'\n' \
                             f'  RSSI:          {self.wifi_rssi}dBm\n' \
                             f'  BSSID:         {self.wifi_bssid}\n' \
                             f'  AP/STA:        {self.wifi_ap_sta}\n'

            if self.wifi_connected == True and self.is_tls():
                banner(f' Event: Wi-Fi Connected...(NTP time received)' \
                       f'\n  NTP Svr:       {iotp.params["ntp_server_ip_addr"]}'
                       f'{wifi_info}'
                       )
            elif self.wifi_connected == True:
                banner(f' Event: Wi-Fi Connected{wifi_info}')
            else:
                banner(f' Event: Wi-Fi Disconnected')

    def evt_cert_received(self, rsp) -> None:
        """ RNWF11 specific function. Handles the Certificate response from the device
            by formatting the data and saving it to a proper certificate file for later
            upload to the cloud.
        """
        fmt: int = 0
        cert_start = cert_end = ""
        result_list: list = []
        file_name_list: list = ["na", "device.crt", "signer.crt", "root.der"]
        # Get certificate type from rsp "AT+ECCRDCERT=1,1500, AT+ECCRDCERT=2,1500, or AT+ECCRDCERT=2,1500
        try:
            if "AT+ECCRDCERT=" in rsp and "OK" in rsp:
                fmt = int((rsp.split("=", 1)[1]).split(",", 1)[0])
                # 3082 07fd 3082 05e5 a003 0201 0202 1068
                # 1604 dff3 34f1 71d8 0a73 5599 c141 7230
                if fmt == 3:
                    cert_start = rsp.find("[") + 1
                    cert_end = rsp.find("]")
                    cert = rsp[cert_start:cert_end]

                    # Split the input_digits into sets of 4 with line break every 8 sets
                    result_list = [cert[i:i + 4] for i in range(0, len(cert), 4)]
                    cert = '\n'.join([' '.join(result_list[i:i + 8]) for i in range(0, len(result_list), 8)])
                else:
                    cert_start = rsp.find("-----BEGIN CERTIFICATE-----")
                    cert_end = rsp.find("-----END CERTIFICATE-----") + len("-----END CERTIFICATE-----")
                    cert = rsp[cert_start:cert_end]
                    result_list = cert.rsplit("\\n")
                    cert = ""
                    for i in result_list:
                        cert = cert + i + '\n'

                try:    # Create the certificate build folder structure
                    os.makedirs(f'{globals()["TLS_CERT_BUILDS"]}/{iotp.params["mqtt_username"]}')
                except FileExistsError:
                    # directory already exists
                    pass
                if fmt > 0 and fmt < 4:
                    f = open(f'{globals()["TLS_CERT_BUILDS"]}/{iotp.params["mqtt_username"]}/{file_name_list[fmt]}', "w")
                    f.write(cert)
                    f.close()
            if APP_DISPLAY_LEVEL >= globals()["APP_DISPLAY_INFO"]:

                banner(f' Certificate Written:\n  File Name:  "{file_name_list[fmt]}"\n'
                       f'  Path:       "{globals()["TLS_CERT_BUILDS"]}/{iotp.params["mqtt_username"]}/\"')
            if APP_DISPLAY_LEVEL >= globals()["APP_DISPLAY_DECODES"]:
                print(cert)
        except Exception as e:
            banner(f' Certificate Write FAILED:\n  File Name:  "{file_name_list[fmt]}"\n'
                   f'  Path:       "{globals()["TLS_CERT_BUILDS"]}/{iotp.params["mqtt_username"]}/\"', "■")
        return

    ##################################
    ### 0 - APP_STATE_CLI
    ##################################
    def sm_cli(self) -> int:
        """ CLI State machine entry point. This is NOT the first state. This state 
            is entered when the user presses 'ESC' one time during execution.
        """
        connections : str = (
            f'  Wi-Fi Connected: {self.wifi_connected} | Broker Connected: {self.broker_connected}'            
        )        
        if self.chk_ss(APP_STATE_BEGIN):
            banner(f' Command Line Interface \n', BANNER_BORDER_LEV_3)
            self.set_state_direct(APP_STATE_CLI, 1)
            self.at_command = self.at_command_resp = ""
            self.at_command_timeout = 0
            self.app_wait = False
        else:
            if self.app_wait:
                return self.app_state
            elif self.kb.key_cmd == DISCONN_KEY: 
                if self.broker_connected:
                    self.cmd_issue("AT+MQTTDISCONN=152")
                elif self.wifi_connected:
                    self.cmd_issue("AT+WSTA=0")
                else:
                    banner(f' Wi-Fi/Broker not connected. ')
                self.set_state_direct(APP_STATE_CLI, 2)
                self.kb.key_cmd = ''
            elif self.kb.key_cmd == RESUME_KEY:                     # From the CLI, 'R' does a full RESET and RUN
                banner(" RESUME Demo (Reset & Run)", BANNER_BORDER_LEV_2)
                self.set_state_direct(APP_STATE_INIT)
                self.kb.key_cmd = ''
            elif self.kb.key_cmd == HELP_KEY:                       # CLI help display on command 'H'
                banner(help_str_cli, BANNER_BORDER_LEV_2)
                banner(f'{connections}', BANNER_BORDER_LEV_3)
                self.kb.key_cmd = ''
            elif self.chk_ss():                                     # CLI Help Display on CLI entry
                banner(f'{help_str_cli}', BANNER_BORDER_LEV_3)
                banner(f'{connections}', BANNER_BORDER_LEV_3)
                self.set_state_direct(APP_STATE_CLI, 2)
            elif self.chk_ss(): self.set_state_direct(APP_STATE_CLI, 2)     # In the CLI we stay in this state until we are done
            elif self.app_sub_state < APP_STATE_COMPLETE: self.set_state_direct(APP_STATE_CLI, 2)# Bounce back to sub state 2
            else:
                self.chk_ss(APP_STATE_COMPLETE)
        return self.app_state

    ##########################################
    ### 1 - APP_STATE_INIT
    ##########################################
    def sm_init(self) -> int:
        """Start initialization with an AT-RST (reset). 
           This must always be called. 
        """
        if self.chk_ss(APP_STATE_BEGIN):
            banner_txt = f' {APP_STATE_INIT} - APP_STATE_INIT'
            if APP_DISPLAY_LEVEL >= APP_DISPLAY_STATES:
                banner(f'{banner_txt}', BANNER_BORDER_LEV_1)
                self.log_state(banner_txt)
            self.cmd_issue('NOOP', 1)   # Use the No Operation(NOOP) command to increment the sub-state                                           
        else:
            if self.app_wait:  # Wait here until last command completes
                pass
            elif self.chk_ss(): self.cmd_issue('AT+WSTA')
            elif self.chk_ss():
                if self.wifi_connected:
                    self.cmd_issue('AT+WSTA=0')
                else: self.cmd_issue('NOOP', 1)
            # Reset the chip on every execution (erases previous Wi-Fi, etc settings)
            elif self.chk_ss():                                                              # Device reset command first
                if APP_DISPLAY_LEVEL >= APP_DISPLAY_INFO:
                    banner(' Event: Device Reset ')  # Reset chip parameters
                self.cmd_issue('AT+RST', 1, "RNWF - AT Command Interface", 60)
            # Send these commands first because we need some of the info provided to correctly
            # identify the module (RNWF02 vs RNWF11). We also need the MAC address to create
            # a unique MQTT ID value.
            elif self.chk_ss(): self.cmd_issue('ATE1')                                       # Set local echo
            elif self.chk_ss(): self.cmd_issue('AT+GMR')                                     # Get chip, software revision
            elif self.chk_ss(): self.cmd_issue('AT+CFG',self.is_model("RNWF02","2.0.0",1 ,2))# Only RNWF02v2 supports AT+WIFIC
            elif self.chk_ss(): self.cmd_issue('AT+WIFIC')                                   # Get Wi-Fi config; Regulatory domain, 
                                                                                             #   BT/Wi-Fi co-exist, etc

            elif self.chk_ss(): self.cmd_issue(f'AT+NETIFC=0,2')                             # Get ethernet MAC address 
            else:
                self.chk_ss(APP_STATE_COMPLETE)
        return self.app_sub_state
    
    ##########################################
    ### 2 - APP_STATE_WIFI_CONNECT
    ##########################################
    def sm_wifi_init(self) -> int:
        """Setup and connect to Wi-Fi initialization after the AT+RST (reset) """

        do_wifi_menu: bool = not(self.wifi_validate())
        banner_txt = f' {APP_STATE_WIFI_CONNECT} - APP_STATE_WIFI_CONNECT'

        if self.chk_ss(APP_STATE_BEGIN):
            # We need to prompt user for Wi-Fi creds
            if do_wifi_menu:    
                banner(f'{banner_txt}\n\n'
                    f' Wi-Fi Credentials Required\n'
                    # f'     SECURITY: \'{iotp.params["wifi_security"]}\'\n'
                    , BANNER_BORDER_LEV_1
                    )
            else:
                if APP_DISPLAY_LEVEL >= APP_DISPLAY_STATES:
                    banner(f'{banner_txt}\n'
                        f'     SSID:     \'{iotp.params["wifi_ssid"]}\'\n'
                        f'     SECURITY: \'{iotp.params["wifi_security"]}\'\n'
                        , BANNER_BORDER_LEV_1)
                    self.log_state(banner_txt)
            self.cmd_issue('NOOP', 1)   # Use the No Operation(NOOP) command to increment the sub-state                                           
        else:
            if self.app_wait:  # Wait here until last command completes
                pass

            # Prompt the user for Wi-Fi info if SSID, Security or Passphrase are empty
            elif self.chk_ss():
                if do_wifi_menu:
                    # Quiet command because we don't want to show the SSID list as the menu 
                    #   of the SSID's will show that anyway.
                    self.cmd_issue_quiet("AT+WSCN=0", 0, "+WSCNIND:")       # SSID menu displayed from 
                else:
                    self.cmd_issue('NOOP', 1)   # Use the No Operation(NOOP) command to increment the sub-state
            elif self.chk_ss(): self.set_sub_state(self.is_model("RNWF11", "*", 1, 1))       # Next cmds RNWF11 with any FW version only

            # Internal Certificate commands only supported by RNFW11 only and not needed in this demo
            # elif self.chk_ss(): self.cmd_issue('AT+ECCRDSER')                               # Get RNWF11's serial number name for the certs
            # elif self.chk_ss(): self.cmd_issue('AT+ECCRDCERT=1,1500')                       # Get DEVICE(1) certificate
            # elif self.chk_ss(): self.cmd_issue('AT+ECCRDCERT=2,1500', 2)                    # Get SIGNER(2) certificate status  and Skip the root cert
            # elif self.chk_ss(): self.cmd_issue('AT+ECCRDCERT=3,1500')                       # Get ROOT(3) certificate
            # elif self.chk_ss(): self.cmd_issue('AT+ECCWRDEVTYPE=1')                         # 6: RNWF11 set ECC device type to 'TrustNGo' connection status
    
            
            # Set basic Wi-Fi parameters: SSID, Security, Passphrase and Channel
            elif self.chk_ss(): self.cmd_issue(f'AT+WSTAC=1,"{iotp.params["wifi_ssid"]}"')  # Set Wi-Fi parameters
            elif self.chk_ss(): self.cmd_issue(f'AT+WSTAC=2,{iotp.params["wifi_security"]}')
            elif self.chk_ss(): self.cmd_issue(f'AT+WSTAC=3,"{iotp.params["wifi_passphrase"]}"')
            elif self.chk_ss(): self.cmd_issue(f'AT+WSTAC=4,0', self.is_tls(1, 18))         # Set Wi-Fi to "any" channel
            ######################
            # TLS Settings:
            #######################
            elif self.chk_ss(): self.cmd_issue(f'AT+SNTPC=2,1')                             # NTP cannot be set by DHCP 
            elif self.chk_ss(): self.cmd_issue(f'AT+SNTPC=3,"{iotp.params["ntp_server_ip_addr"]}"') 
            elif self.chk_ss(): self.cmd_issue(f'AT+SNTPC=1,1')                             # SNTP Enable from server
            #
            # Wi-Fi Connect for TLS
            #
            elif self.chk_ss():                                                             # Wi-Fi connect for TLS
                self.cmd_issue(f'AT+WSTA=1', 1, "+TIME:", WIFI_TIMEOUT_TLS_S)               # Wait for SNTP time, then skip 4 states
                self.log_state('Wait for NTP...')
                if APP_DISPLAY_LEVEL >= APP_DISPLAY_STATES:
                    banner(f'Wait for NTP...')            
            elif self.chk_ss(): self.cmd_issue(f'AT+ASSOC', 1, "+ASSOC:") 
            elif self.chk_ss(): self.cmd_issue(f'AT+TLSC={TLS_CFG_INDEX},1,"{iotp.params["ca_cert_name"]}"')   # 
            elif self.chk_ss(): self.cmd_issue(f'AT+TLSC={TLS_CFG_INDEX},2,"{iotp.params["device_cert_filename"]}"')
            elif self.chk_ss(): self.cmd_issue(f'AT+TLSC={TLS_CFG_INDEX},3,"{iotp.params["device_key_filename"]}"') 

            # Have to use NOOP commands to check for both RNWF02v1 and RNWF11 to skip unsupported 3 TLS commands below
            # RNWF02v1 does not support any of the remaining TLS commands
            elif self.chk_ss(): self.cmd_issue(f'NOOP', self.is_model("RNWF02","1.0.0", APP_STATE_NEXT_STATE, 1))

            elif self.chk_ss(): self.cmd_issue(f'NOOP', self.is_model("RNWF11","*", 1, 2))      # Only RNWF11 supports TLS cmd
            # elif self.chk_ss(): self.cmd_issue(f'AT+TLSC={TLS_CFG_INDEX},8,0', APP_STATE_NEXT_STATE)
            elif self.chk_ss(): self.cmd_issue(f'AT+TLSC={TLS_CFG_INDEX},8,0')              # RNWF11 only. Use ECC608 True(1), False(0)
            
            elif self.chk_ss(): self.cmd_issue(f'NOOP', self.is_model("RNWF02","*", 1, APP_STATE_NEXT_STATE))
            ## Note: Params 5 & 6 are on by default and should NOT be turned off or else authentication does not happen but it still
            #        still connects
            # RNWF02 v2 ONLY
            elif self.chk_ss(): self.cmd_issue(f'AT+TLSC={TLS_CFG_INDEX},40,1')             # Peer authentication. Enable(1)[DEF], Disable(0)
            elif self.chk_ss(): self.cmd_issue(f'AT+TLSC={TLS_CFG_INDEX},5,"{iotp.params["mqtt_broker_url"]}"')
            elif self.chk_ss(): self.cmd_issue(f'AT+TLSC={TLS_CFG_INDEX},41,1')             # Peer domain verification: Enable(1)[DEF], Disable(0)
            elif self.chk_ss(): self.cmd_issue(f'AT+TLSC={TLS_CFG_INDEX},6,"{iotp.params["mqtt_broker_url"]}"')

            #RNF02 v2 specific AT+ commands for TLS (Not Supported by RNWF02v1 or RNWF11)
            # elif self.chk_ss(): self.cmd_issue(f'NOOP', self.is_model("RNWF02","2.0.0", 1, APP_STATE_NEXT_STATE))
            # elif self.chk_ss(): self.cmd_issue(f'AT+TLSC={TLS_CFG_INDEX},20,0')                 # Crypto ops done externally; None

            elif self.chk_ss(): self.cmd_issue(f'NOOP', APP_STATE_NEXT_STATE)

            ######################
            # Non-TLS Settings:
            #######################
            elif self.chk_ss(): self.cmd_issue(f'AT+SNTPC=2,0')                              # NTP can be set by DHCP
            elif self.chk_ss(): self.cmd_issue(f'AT+SNTPC=1,0')                              # NTP Disable
            elif self.chk_ss(): self.cmd_issue(f'AT+WSTA=1', 1, "+WSTAAIP:", WIFI_TIMEOUT_S) # Else Wait for Wi-Fi IP address message

            elif self.chk_ss(): self.cmd_issue(f'AT+ASSOC', 1, "+ASSOC:")                    # Called to get AP's MAC address  
            else:
                self.chk_ss(APP_STATE_COMPLETE)
        return self.app_sub_state

    ##########################################
    ### 3 - APP_STATE_MQTT_SETTINGS
    ##########################################
    def sm_mqtt_settings(self) -> int:
        """ Set MQTT module settings"""

        if self.chk_ss(APP_STATE_BEGIN):
            banner_txt = f' {APP_STATE_MQTT_SETTINGS} - APP_STATE_MQTT_SETTINGS '
            if APP_DISPLAY_LEVEL >= APP_DISPLAY_STATES:
                banner(f'{banner_txt}', BANNER_BORDER_LEV_1)
                self.log_state(banner_txt)
            self.cmd_issue('NOOP', 1)   # Use the No Operation(NOOP) command to increment the sub-state                                           
        else:
            if self.app_wait:  # Wait here until last command completes
                pass
            elif self.chk_ss(): self.cmd_issue(f'NOOP', self.is_tls(1, 2))                          # Skip next cmd if not TLS I/O
            elif self.chk_ss(): self.cmd_issue(f'AT+MQTTC=7, {TLS_CFG_INDEX}')                      # Set TLS configuration index see "AT+sysTLSC"
            elif self.chk_ss(): self.cmd_issue(f'AT+MQTTC=8, {iotp.params["mqtt_version"]}')        # Set MQTT version 3 or 5
            elif self.chk_ss(): self.cmd_issue(f'AT+MQTTC=1,"{iotp.params["mqtt_broker_url"]}"')    # 1: Set MQTT version 3 or 5
            elif self.chk_ss(): self.cmd_issue(f'AT+MQTTC=2, {iotp.params["mqtt_broker_port"]}')    # DPS broker port
            elif self.chk_ss(): self.cmd_issue(f'AT+MQTTC=6, {iotp.params["mqtt_keep_alive"]}')     # Set MQTT Keep Alive

            elif self.chk_ss(): self.cmd_issue(f'AT+MQTTC=3,"{self.mqtt_client_id}"')               # MQTT Client ID
            elif self.chk_ss(): self.cmd_issue(f'AT+MQTTC=4,"{iotp.params["mqtt_username"]}"')      # MQTT Username
            elif self.chk_ss(): self.cmd_issue(f'AT+MQTTC=5,"{iotp.params["mqtt_password"]}"')      # MQTT Password
                
            # elif self.chk_ss(): self.cmd_issue(f'AT+MQTTC=9, {self.mqtt_read_sz}')                  # Read buffer size. Only for RNWF02 v2 & RNWF11 v1
            else:
                self.chk_ss(APP_STATE_COMPLETE)
        return self.app_sub_state

    ##########################################
    ### 4 - APP_STATE_MQTT_CONNECT_BROKER
    ##########################################
    def sm_mqtt_connect(self) -> int:
        """Connect & Subscribe to MQTT topics count, button, and temp """

        if self.chk_ss(0):
            if APP_DISPLAY_LEVEL >= APP_DISPLAY_STATES:
                banner_txt = f' {APP_STATE_MQTT_CONNECT_BROKER} - APP_STATE_MQTT_CONNECT_BROKER '
                banner(f'{banner_txt}', BANNER_BORDER_LEV_1)
                self.log_state(banner_txt)
            self.cmd_issue('NOOP', 1)   # Use the No Operation(NOOP) command to increment the sub-state
        else:
            topic = self.get_topic_path()
            subscription = f'{self.get_topic_path()}'
            if self.is_subscribed_mqtt():
                subscription = f'{subscription}/{self.mqtt_subscription}'
            if self.app_wait:  # Wait here until last command completes
                pass
            
            # elif self.chk_ss(): self.cmd_issue(f'AT+MQTTDISCONN=0')()# 1: Disconnect first. Not sure this is needed. Done in state 1

            elif self.chk_ss(): self.cmd_issue(f'AT+MQTTCONN=1', 1, "+MQTTCONNACK", WIFI_TIMEOUT_TLS_S)     # 1: CRITICAL Wait
            elif self.chk_ss(): self.cmd_issue(f'AT+MQTTC', self.is_subscribed_mqtt(1,2))                               

            # Subscribe to topic(s) 
            elif self.chk_ss(): self.mqtt_subscribe(f'{subscription}', MQTT_IQOS, 1, "+MQTTSUB:0")   
            
            # Topics are initialized in the cloud, but only when this is the 'primary' module. Primary module
            # is when the MQTT_ID is the same as the root MQTT Root Topic. This keeps secondary and later modules
            # to attach to the broker without resetting the telemetry values.
            # Publish topic(s)
            elif self.chk_ss(): self.set_sub_state(self.is_primary_mqtt(1,4))               # Only publish topics if primary add-on brd
            elif self.chk_ss(): self.mqtt_publish(MQTT_IQOS, MQTT_IRETAIN, f'{topic}/button', str(int(self.iotc_button)))                 
            elif self.chk_ss(): self.mqtt_publish(MQTT_IQOS, MQTT_IRETAIN, f'{topic}/temp', str(round(self.iotc_temp,1)))                    
            elif self.chk_ss(): self.mqtt_publish(MQTT_IQOS, MQTT_IRETAIN, f'{topic}/count', str(self.iotc_count))
            
            elif self.chk_ss(): self.set_sub_state(self.is_model("RNWF02","1.0.0", 2, 1))   # RNWF02v1 does not support next cmd
            elif self.chk_ss(): self.cmd_issue(f'AT+MQTTSUBLST')                            # Show MQTT subscriptions

            elif self.chk_ss(): self.app_sub_state = APP_STATE_COMPLETE
            else:
                self.chk_ss(APP_STATE_COMPLETE)
        return self.app_sub_state

    ##########################################
    ### 5 - APP_STATE_IOTC_DEMO
    ##########################################
    def sm_iotc_demo_app(self) -> int:
        """ Final demo state where user can interact with the broker by sending and receiving telemetry.
        """
        banner_txt = f' {APP_STATE_DEMO} - APP_STATE_IOTC_DEMO '

        if self.chk_ss(APP_STATE_BEGIN):
            if APP_DISPLAY_LEVEL >= APP_DISPLAY_STATES:
                banner(f'{banner_txt}', BANNER_BORDER_LEV_2)
            # If the demo banner/help is not displayed it appears hung...so always display
            banner(help_str_demo, BANNER_BORDER_LEV_2)
            self.demo_info()
            self.log_state(banner_txt)
            self.cmd_issue('NOOP', 1)   # Use the No Operation(NOOP) command to increment the sub-state
        else:
            if self.app_wait:  # Wait here until last command completes
                return self.app_sub_state
            #################################################
            ##  Demo Sub-State APP_SUB_STATE_DEMO_LOOP(1)  ##
            #################################################
            elif self.chk_ss():
                # Main state handler for all user input keys 'B', 'C', 'T', 'I', 'TAB' or 'Resume'
                #
                # Display Demo state help screen
                if self.kb.key_cmd == HELP_KEY:
                    banner(help_str_demo, BANNER_BORDER_LEV_2)
                    self.demo_info()
                #
                # Sends TELEMETRY 'button' [0|1] ==> Broker. Toggles the button state 0 to 1 to 0.
                elif self.kb.key_cmd == BUTTON_KEY:
                    local_button = int(not self.iotc_button)
                    topic = f'{self.get_topic_path()}/button'
                    self.iotc_int_telemetry_send(topic , local_button, 1 )
                    if EN_LOCAL_TELEMETRY:
                        self.iotc_button = local_button
                        self.demo_display('button')
                #
                # Sends TELEMETRY 'counter' [0-n] ==> Cloud. Counter incremented and sent to Cloud
                elif self.kb.key_cmd == COUNT_KEY:
                    local_count = self.iotc_count
                    if local_count == '':
                        local_count = 0
                    else:
                        local_count += 1
                    topic = f'{self.get_topic_path()}/count'
                    self.iotc_int_telemetry_send(topic, local_count, 1)
                    if EN_LOCAL_TELEMETRY:
                        self.iotc_count = local_count
                        self.demo_display('count')                    
                #
                # Sends TELEMETRY 'temp' [0.0-n] ==> Cloud. Temperature random delta updated and sent to Cloud
                elif self.kb.key_cmd == TEMP_KEY:
                    local_temp = self.iotc_temp
                    if local_temp == '':
                        local_temp = 0
                    else:
                        local_temp += self.random_delta_temp()      # round((random.randrange(-50, +50) / 10), 1)
                    topic = f'{self.get_topic_path()}/temp'
                    self.iotc_double_telemetry_send(topic, round(local_temp,1), 1)
                    if EN_LOCAL_TELEMETRY:
                        self.iotc_temp = round(local_temp, 1)
                        self.demo_display('temp')                    
                #
                # Changes report rate from 0s => 1 => 2 => 5 => 10 => 0s on each 'I' or "TAB" press
                elif self.kb.key_cmd == REPORT_RATE_KEY or self.kb.key_cmd == REPORT_RATE_INF_KEY:
                    self.telemetry_index += 1
                    # Roll the index back to zero for a circular interval list
                    if self.telemetry_index > (len(self.telemetry_ints) - 1):
                        self.telemetry_index = 0

                    self.telemetry_interval = self.telemetry_ints[self.telemetry_index]
                    if self.telemetry_interval:
                        if self.kb.key_cmd == REPORT_RATE_INF_KEY:
                            self.demo_loops = -1                # When negative counts up to infinity
                        else:
                            self.demo_loops = DEMO_LOOP_COUNT   # When positive counts down to 0
                        self.delay.stop()
                        start_val = self.delay.start()
                    else:
                        self.demo_loops = 0
                        self.delay.stop()
                    self.demo_display()

                # RESUME Command
                #   Broker DISCONNECTED: Attempt broker reconnection by jumping to state 'APP_STATE_MQTT_CONNECT_BROKER' 
                #   Wi-Fi  DISCONNECTED: Restart the demo at the Wi-Fi connection 'APP_STATE_WIFI_CONNECT'
                elif self.kb.key_cmd == RESUME_KEY:
                    # Restart DEMO mode
                    if not self.wifi_connected:
                        banner(f'Attempting to reconnect to the AP...')
                        self.set_state_direct(APP_STATE_WIFI_CONNECT, 0)
                    elif not self.broker_connected:
                        banner(f'Attempting to reconnect to the MQTT Broker...')
                        self.set_state_direct(APP_STATE_MQTT_CONNECT_BROKER, 0)
                    else:
                        banner(f'Cannot "resume" while Broker is still connected.')

                else:   # Back to top of the Demo Loop
                    self.set_state_direct(APP_STATE_DEMO, APP_SUB_STATE_DEMO_LOOP)

                # Clear the fs_command
                self.kb.cmd = ''
                self.kb.key_cmd = ''
            else:
                self.set_state_direct(APP_STATE_DEMO, APP_SUB_STATE_DEMO_LOOP)

            # Update interval if it's running or should be. 
            if self.demo_loops:
                self.delay.start()
                if self.delay.delay_sec_poll(self.telemetry_interval):

                    # Using the mod operator to update each of the 3 values
                    # one time per loop.
                    if self.demo_loops % 3 == 2:
                        self.kb.key_cmd = COUNT_KEY
                    elif self.demo_loops % 3 == 1:
                        self.kb.key_cmd = BUTTON_KEY
                    elif self.demo_loops % 3 == 0:
                        self.kb.key_cmd = TEMP_KEY

                    self.demo_loops -= 1
                    self.delay.stop()
                    self.delay.start()
            else:
                self.telemetry_interval = 0
                # pass
        return self.app_sub_state

    def demo_info(self, do_banner: bool = True) -> str | None:
        """ Called to output or return text containing
            login and server info.
        """
        server = f'{iotp.params["mqtt_broker_url"]}:{iotp.params["mqtt_broker_port"]}' 
        ver = f'{iotp.params["mqtt_version"]}'   
        topic =  f'{self.get_topic_path()}'
        login =  f'{self.mqtt_client_id}'
        sub =    f'{topic}/{iotp.params["mqtt_subscription"]}'
        if iotp.params["mqtt_subscription"] == "":
            sub = f'None'
        
        info : str = (
            f' MQTT v{ver} BROKER: {server} | MQTT ID: {login} \n'
            f'  SUBSCRIPTION: {sub}\n' 
            f'  TOPICS:       {topic}/button\n' 
            f'                {topic}/count\n' 
            f'                {topic}/temp\n'
        )
        if do_banner:
            banner(f'{info}')
        else:
            return info

    def demo_display(self, dict_key: str = None) -> None:
        """ Called to display or setup the response info. If a key value, 'button', 'count' or 'temp'
            is passed, that value is flagged as "updated" and the "demo display" is not displayed. To
            display the demo value, call this function without any parameters.
            eg: demo_display()                     # Show display & clear 'dict_key's'
                demo_display('count')              # 'count' is flagged as changed or dirty

            dict_keys: {count, button, temp}
        """
        if dict_key != None or APP_DISPLAY_LEVEL < APP_DISPLAY_DEMO:
            self.resp_dict[dict_key] = '*'
            return
        # Horiz spacing for header text
        # Count, Button, Temp
        spc = [11, 11, 11, 10]      # Note: Make the field sizes here equal the physical screen size desired
                                    # First 3 fields are for 10 char fields + 1 char [' ' or '*'] showing a
                                    # changed field value.  
        data_dict = {"count": self.iotc_count, "button": self.iotc_button, "temp": self.iotc_temp}

        hdr = f' ' \
              f'{"Count" : <{spc[0]}}'\
              f'{"Button" : <{spc[1]}}'\
              f'{"Temp" : <{spc[2]}}'\
              f'{"Report Rate" : <{spc[3]}}'
        
        # When incrementing counter by an interval timer change the
        # 'repRate' to include the loop count down.
        # Infinity char "∞"
        if self.demo_loops:
            if self.demo_loops < 0:
                tele_str = f'{str(self.telemetry_interval)}s (oo)'
            else:
                tele_str = f'{str(self.telemetry_interval)}s ({self.demo_loops})'
        else:
            tele_str = f'{str(self.telemetry_interval)}s'
        dat = f'{self.resp_dict["count"]}{str(int(self.iotc_count)) : <{spc[0] - 1}}'\
              f'{self.resp_dict["button"]}{str(int(self.iotc_button)) : <{spc[1] - 1}}'\
              f'{self.resp_dict["temp"]}{str(self.iotc_temp): <{spc[2] - 1}}'\
              f'{tele_str: ^{spc[3]}}'

        banner(f'{hdr}\n{dat}\n', BANNER_BORDER_LEV_2)              # Don't show data direction
        # self.resp_dict.clear()
        for key, value in self.resp_dict.items():
            self.resp_dict[key] = ' '

    def iotc_int_telemetry_send(self,
                                topic: str,
                                ival: int,
                                next_step: int = 1,
                                alt_resp: str = "") -> None:
        self.mqtt_publish(MQTT_IQOS, MQTT_IRETAIN, topic, f'{str(ival)}', next_step, alt_resp)

    def iotc_double_telemetry_send(self,
                                   topic: str,
                                   dval: float,
                                   next_step: int = 1,
                                   alt_resp: str = "") -> None:
        # print(f'Sending TELEMETRY \'{parameter}\' double value of: {str(dval)}')
        self.mqtt_publish(MQTT_IQOS, MQTT_IRETAIN, topic, f'{str(dval)}', next_step, alt_resp)

    def err_handler(self, cmd_time: float, rsp: str, ext_sig: str = '') -> bool:
        # print(f'RSP[{self.app_state:0>2}.{self.app_sub_state:0>2}]: {rsp} ({cmd_time:.2f}s)\n', flush=True, end='')

        # Typical Error RSP: 'AT+TLSC=1,2,"rnwftestDev1_cert" [ER]:0.4,"Invalid Parameter"'
        iss = sol = tip = ''
        if ext_sig == '':
            err_sig = f'{self.app_state:0>2}:{self.app_sub_state:0>2}'
        else:
            err_sig = ext_sig

        if rsp.find("[ER]") == -1 and rsp.find("WSTAERR") == -1:
            return False
        
        if self.app_state >= APP_STATE_DEMO:   # Don't fault OR disconnect in Demo state
            # print(f'RSP[{self.app_state:0>2}.{self.app_sub_state:0>2}]: {rsp} ({cmd_time:.2f}s)\n', flush=True, end='')
            self.cmd_log(f'RSP[{self.app_state:0>2}.{self.app_sub_state:0>2}]: {rsp} ({cmd_time:.2f}s)')
            self.cmd_kill()
            return False

        self.cmd_log(f'          : {rsp} ({cmd_time:.2f}s)\n')

        cmd_fail = self.at_command

        if rsp.find('[ER]:NTP') != -1:
            # Actually failed @ 01:12 but due to cfg issue @ 01:09
            cmd_fail=  f'AT+SNTPC=3,"{iotp.params["ntp_server_ip_addr"]}"'
            iss = f'Wi-Fi NTP ({iotp.params["ntp_server_ip_addr"]}) configuration'
            sol = f'- Verify Network Time Server is online'
            tip = f'- Specify a valid NTP server in \'{APP_CONFIG_FILE}\' '
        elif rsp.find('STA Connection Failed') != -1:
            iss = f'Wi-Fi ({iotp.params["wifi_ssid"]}) configuration'
            sol = f'- Verify router power, SSID, passphrase and security settings'
            tip = f'- Use the CLI \'scan\' tool'
        elif rsp.find('Association Not Found') != -1:
            iss = f'Wi-Fi ({iotp.params["wifi_ssid"]}) configuration'
            sol = f'- Wi-Fi connection was not complete'
            tip = f''            
        elif err_sig.find('01:17') != -1:
            iss = f'TLS DEVICE Certificate '
            sol = f'- Load device certificate (\'{iotp.params["device_cert_filename"]}\') and verify \'iotp.params["device_cert_filename"]\' in \'{APP_CONFIG_FILE}\''
            tip = f'- Use CLI command \'dir c\' to view installed certificates'
        elif err_sig.find('01:18') != -1:
            iss = f'TLS KEY Certificate '
            sol = f'- Load KEY certificate (\'{iotp.params["device_key_filename"]}\') and verify \'iotp.params["device_key_filename"]\' in \'{APP_CONFIG_FILE}\''
            tip = f'- Use CLI command \'dir k\' to view installed key certificates'
        else:
            iss = ''
            sol = ''
            tip = ''

        print('\n')

        msg = f' An ERROR has been detected:\n'
        msg += f' CMD[{err_sig}]: {cmd_fail} ({cmd_time:.2f}s)\n'
        try:
            msg += f' ERR[{err_sig}]: {rsp.split("[ER]:")[1]}\n'
        except:
            pass

        if iss != '':
            msg += f'\n {iss}\n'
        if len(sol):
            msg += f'  {sol}\n'
        if len(tip):
            msg += f'  {tip}'
        banner(msg, BANNER_BORDER_LEV_1)
        print('\n\n')

        self.app_state = APP_STATE_CLI
        self.app_sub_state = 0
        self.app_wait = False
        self.at_command_prev = self.at_command
        self.at_command = None
        self.evt_handler = None
        self.ser_buf = ""
        return True

    def substr_swap(self, str_msg: str, dic: dict) -> str:
        """ Parses a string and replaces the passed in dictionary keys values with
            the substring value for that key. The modified string is returned.
            e.g.: rsp = self.substr_swap(rsp, {">": "", "OK": "[OK]", "\n": ""})
               In rsp, ">" is replaced by an empty string ""
                  rsp, "OK" is replaced with "[OK]"
                  rsp, "\n" is replaced by an empty string ""
        """
        for char in dic.keys():
            str_msg = str_msg.replace(char, dic[char])
        return str_msg
    
    def list_to_dict(self, list_in: list) -> dict:
        """ Takes list with an even number of values and returns a dictionary object."""
        dict_out: dict = {}
        if len(list_in) % 2 == 0:
            # Convert list to a dict using a dictionary comprehension
            dict_out = {list_in[i]: list_in[i + 1] for i in range(0, len(list_in), 2)}
        
        return dict_out
    
    ##################################
    ### Process Receive Data
    ##################################
    def rx_data_process(self, received: str) -> None:
        """ Single command Queue depth Rx data handler """
        rsp = received
        self.evt_handler = None

        # Modify received data for a cleaner response string output
        rsp = self.substr_swap(rsp, {">": "", "OK": "[OK]", "ERROR": "[ER]", "\r": "", "\n": " "})
        rsp = rsp.rstrip()

        cmd_time = time.time() - self.at_command_timer.time_start

        if self.err_handler(cmd_time, rsp):
            self.set_state_direct(APP_STATE_CLI)
            return
        # At the top we check to see if the CMD sent is to be completed. Most commands complete
        # when the device returns the CMD 'text' sent in the response.
        #   cmd_issue(f'AT+MQTTPUB=0,0,0') <== Default version waits on the original command return.
        #     CMD(AT+MQTTPUB=0,0,0...) == RSP(AT+MQTTPUB=0,0,0...[OK]    <== This is COMPLETE
        #
        # Other commands need to wait for a different response, either from the device or the cloud. When
        # this is required the 'cmd_issue' includes the completion text or command to wait on.
        #   cmd_issue(f'AT+WSTA=1', 1, "+TIME:") <== Sends WSTA command, completes on "+TIME:" text
        #       CMD(AT+WSTA=1...) == RSP(+TIME:) [OK]  <== This is complete
        #
        if self.at_command_resp != "" and self.at_command_resp in rsp: # and self.at_command:
            # Solicited Response line display i.e. commands that have COMPLETED.
            # print(f'RSP[{self.app_state:0>2}.{self.app_sub_state:0>2}]: {rsp} ({cmd_time:.2f}s)\n', flush=True, end='')
            self.cmd_log(f'RSP[{self.app_state:0>2}.{self.app_sub_state:0>2}]: {rsp} ({cmd_time:.2f}s)')
            self.cmd_kill()

            # Increment to the next sub-state
            if APP_STATE_CLI <= self.app_state <= APP_STATE_DEMO:
                # Increment the sub-state which is only effective if the offset is NOT 0
                # If it is '0', then an evt handler will update the sub state instead
                self.app_sub_state += int(self.next_sub_state_offset)
        else:
            # Blocks "+TIME" text and clears the Rx buffer to keep the CLI less cluttered.
            if rsp.find("+TIME:") >= 0:
                self.evt_ntp_received(received)
                self.ser_buf = ""
                if BLOCK_PERIODIC_TIME_RESP:
                    return
                else:
                    banner(f' NTP server updated UTC Time: {self.last_utc_update} ')
                    return
        # Unsolicited command response line display.
        #    RSP's received without an outstanding matched command, are displayed here.
        if rsp != '' and self.at_command_timer.isStarted:
            self.cmd_log(f'          : {rsp}') #, end='')

        # Special handlers for CLI File system commands
        if rsp != "":
            if "AT+FS" in rsp:                              # SysCert & Key dir command response
                self.evt_fs_data_result(received)

            if "WSCNIND" in rsp:  # Wi-Fi scan command response
                # Get the wifi list, max length of SSID string, and number of SSID skipped; eg named '[]'
                wifi_list, ssid_max_len, ssid_skipped_count  = self.evt_wifi_scan_result(received)

                if self.app_state != APP_STATE_WIFI_CONNECT:    # Just display Wi-Fi scan results
                    banner(f' Wi-Fi Scan Results')
                    count = 0
                    for w in range(1, len(wifi_list)):          # Loop on the list. Start at 1 because 0 is 
                        count += 1                              #   for Wi-Fi selection menu to RESCAN Wi-Fi.
                        wifi = wifi_list[w]
                        wifi = list(wifi.split(','))

                        print(f'  {str(count):>2}. '
                            f' {str(wifi[3])}  '                # MAC address
                            f'Ch: {str(wifi[2]):>2}  '          # Wi-Fi Channel
                            f'Sec: {wifi[1]}  '                 # Wi-Fi Security type
                            f'Sig: {str(wifi[0]):>3}dBm '       # Signal strength
                            f'  "{wifi[4]}"')                   # Wi-Fi SSID
                else:
                    if self.evt_wifi_prompt_user(wifi_list, ssid_max_len) == False:
                        print( f'\nUser Exit by \'ESC\'' )
                    else:                                       # SUCCESS: User set Wi-Fi creds so restart state 2
                        print( f'\n' )
                        self.set_state_direct(APP_STATE_WIFI_CONNECT, 0)

        #
        # Additional response handling calls, completed or not
        #
        if ("ATE1" in received) and ("ERROR:" in received):
            self.evt_handler = self.evt_init_error

        elif "ASSOC:" in received:            # ASSOC data received AFTER Wi-Fi connects to AP
                                              # eg: '+ASSOC:1,0,"9C:1C:12:96:1D:61",-59'
            try:
                rsp = self.substr_swap(rsp, {"+ASSOC:": "", "\"": "","\r": "", "\n": ""})
                assoc_list = rsp.split(",")
                self.wifi_assoc_id = assoc_list[0]
                if assoc_list[1] == '0':
                    self.wifi_ap_sta = f'AP({assoc_list[1]})'
                elif assoc_list[1] == '1':
                    self.wifi_ap_sta = f'STA({assoc_list[1]})'
                else:
                    self.wifi_ap_sta = f'???'

                self.wifi_bssid = assoc_list[2]
                self.wifi_rssi = assoc_list[3]
                self.evt_handler = self.evt_wifi_connected
            except:
                self.wifi_ap_sta = '???'                # AT+ASSOC; 0=AP, 1=Station
                self.wifi_assoc_id = '?'                # ASSOC ID 
                self.wifi_bssid = '00:00:00:00:00:00'   # AT+ASSOC; MAC of AP connected to
                self.wifi_rssi = '???'                  # AT+ASSOC; RSSI of AP in dbm

        elif "NETIFC:2" in received:                    # Decode the MAC address of the module; eg: '+NETIFC:2,"40:84:32:90:23:8D"'
            try:
                rsp = self.substr_swap(rsp, {"+NETIFC:": "", "\"": "","[OK]": "","\r": "", "\n": ""," ": ""})
                assoc_list = rsp.split(",")
                self.mac = assoc_list[2]
                # self.mac = "00:00:00:00:00:00"          # Uncomment to test MAC address test
                unique_tag = self.substr_swap(self.mac, {":": "-"})
                unique_tag = unique_tag[-8:]

                # Create a unique MQTT Client ID to login to broker (per device based on MAC address)
                if self.mqtt_client_id == "":
                    if len(self.mac) == 17 and self.mac != "00:00:00:00:00:00":
                        unique_tag = self.substr_swap(self.mac, {":": "-"})
                        self.mqtt_client_id = f'{self.dev_model[:15]}_{unique_tag[-8:]}'
                    else:
                        raise ValueError("Invalid MAC Address")
                
                # Add new root topic only if it is currently blank
                if self.mqtt_root_topic == "":
                    iotp.params["mqtt_root_topic"] = self.mqtt_client_id
                    self.mqtt_root_topic = self.mqtt_client_id
                    iotp.write()            
            except Exception as e:
                banner(f' Error: {e} detected in {self.dev_model} module.\n\n'
                    f'  MAC Address: \'{self.mac}\'\n')
                exit(1)
        elif "+GMM:" in received:
            pass
        elif "+WIFIC:" in received:
            rsp = self.substr_swap(rsp, {"AT+WIFIC+WIFIC:": "", "[OK]": "", "+WIFIC:": ",", "\"": ""})
            # Convert to a list using 'split' then pass to function for conversion to a dictionary
            try:
                wifi_cfg_dict = self.list_to_dict(rsp.split(","))
                self.wifi_reg_domain = wifi_cfg_dict['10']          # 10: Wi-Fi regulatory domain
                dom_cnt: int = int(wifi_cfg_dict['11'])             # 11: Number of domains in flash
                self.wifi_reg_domain_available = ""                 # 11.0-11.x, ToDo: Wi-Fi supported domains
            except:
                self.wifi_reg_domain = ""
                self.wifi_reg_domain_available = ""
        elif "+CFG:" in received:
            pass
        elif "GMR" in received:                 # Firmware device info received
            self.evt_gmr_data_result(received)

        elif ("AT+WSTAC" in received) and ("ERROR:" in received):
            self.evt_handler = self.evt_init_error
        
        elif "+WSTA:1" in received:             # Wi-Fi connected
            pass
            self.wifi_connected = True
            self.evt_handler = '' #self.evt_wifi_connected

        elif "+WSTA=0" in received:             # Wi-Fi not connected
            self.wifi_connected = False
            self.broker_connected = False       # Broker cannot be connected if Wi-Fi is not
            self.evt_handler = self.evt_wifi_connected

        elif "+WSTAAIP:" in received:           # IP address received from device
            self.wifi_connected = True
            start = received.find('"') + 1      # eg: '+WSTAAIP:1,"172.31.99.108"\r\n>'
            end = start + received[(start + 1):].find('"') + 1
            ipaddress = received[start:end]
            if ipaddress.find(':') != -1:       # Check for IPv6
                self.ip_addr_ipv6 = received[start:end]
            elif ipaddress.find('.') != -1:     # Check for IPv4
                self.ip_addr_ipv4 = received[start:end]

        elif "AT+MQTTC +MQTTC:1," in rsp:
            if APP_DISPLAY_LEVEL >= APP_DISPLAY_INFO:
                mqttc_str = rsp.replace(",", " - ")
                mqttc_list = mqttc_str.split(" +", )
                for i in range(1, len(mqttc_list)):
                    print(f'            +{mqttc_list[i]}')

        # elif "AT+MQTTCONN" == self.at_command_prev:
        #     if APP_DISPLAY_LEVEL >= APP_DISPLAY_INFO:
        #         banner(f' Event: Broker Not Connected - Query Current Connection Status')

        elif "AT+MQTTDISCONN" == self.at_command_prev or "AT+MQTTDISCONN=152" in rsp:
            self.broker_connected = False
            if APP_DISPLAY_LEVEL >= APP_DISPLAY_INFO:
                banner(f' Event: Broker DISCONNECTED - By Command\n')

        elif "+MQTTCONN:0" in received:
            if self.broker_connected == True:
                self.broker_connected = False
                # Change the time out since the connection failed...
                # no point in waiting now.
                print(f'', flush=True)  # Required to prevent banner line break issues
                banner(f' Event: Broker DISCONNECTED - By Timeout or Error')
            self.cmd_kill(True)

        elif "+MQTTCONN:1" in received:
            self.broker_connected = True
            if self.app_state >= APP_STATE_MQTT_CONNECT_BROKER:
                if APP_DISPLAY_LEVEL >= APP_DISPLAY_INFO:
                    banner(' Event: MQTT Broker Connected')

        elif "+MQTTSUBRD:" in received:
            pass

        elif "+MQTTSUBLST" in received:
            if APP_DISPLAY_LEVEL >= APP_DISPLAY_DECODES:
                mqttc_str = self.substr_swap(rsp, {",0 [OK]": "", "AT+MQTTSUBLST": "", "0 +MQTTSUBLST:": "",
                                                   " [OK]": "","+MQTTSUBLST:": "", ",0\r\nOK\r\n": ""})
                mqttc_list = mqttc_str.split(",")

                mqttc_str = f' MQTT Subscriptions:\n───────────────────\n'
                if mqttc_list[0] == '':
                    mqttc_str += f' None'
                else:
                    for i in range(0, len(mqttc_list)):
                        mqttc_str += f' {i+1}: {mqttc_list[i].lstrip()}\n'
                banner(mqttc_str)

        elif "+MQTTSUBRX:" in received:
            """ This response can be received in 2 formats, one with 5 parameters and one with 6. The
                response with 5 parameters is the one we are interested in as it contains the payload value.
                The 6 parameter version is supported by RNWF02_v2 and RNWF11_v1 and serves as a "subscribed
                data notification" only. It does not contain the payload. RNWF02_v1 does not support the 6
                parameter response.
            """
 
            if self.app_state >= APP_STATE_DEMO or self.app_state == APP_STATE_CLI:
                # print(f'SRx: {rsp}', flush=True)
                self.cmd_log(f'SRx: {rsp}\n')

            # DEBUG_START: String with multiple telemetry values
            # Comment for production
            # rsp = '+MQTTSUBRX:0,0,0,"RNWF02_90-23-8D/button","1" +MQTTSUBRX:0,0,0,"RNWF02_90-23-8D/temp","50.5" +MQTTSUBRX:0,0,0,"RNWF02_90-23-8D/count","99"'
            # DEBUG_STOP

            rsp = self.substr_swap(rsp, {'"': ""})
            payload_list = rsp.split(",")
            resp_list = rsp.split("+MQTTSUBRX:")

            is_dirty: bool = False
            for r in resp_list:
                payload = r.split(",")
                if r == '' or len(payload) > 5:
                    continue
                try:
                    field_name = (payload[3]).split("/")[-1]
                    if (field_name == 'button'):
                        is_dirty = True
                        self.iotc_button = bool(int(payload[4]))
                        self.demo_display('button')
                    elif (field_name == 'temp'):
                        is_dirty = True
                        self.iotc_temp =  float(payload[4])
                        self.iotc_temp = round(self.iotc_temp, 1)                        
                        self.demo_display('temp')
                    elif (field_name == 'count'):
                        is_dirty = True
                        self.iotc_count = int(payload[4])
                        self.demo_display('count')
                except:
                    pass

            if (self.app_state == APP_STATE_DEMO or self.app_state == APP_STATE_CLI) and is_dirty == True:
                self.demo_display()

        elif "+ECCRDSER:" in received and self.is_model("RNWF11"):
            start = received.find('"') + 1      # eg: '+ECCRDSER:18,"01232943D301723001"'
            end = start + received[(start + 1):].find('"') + 1
            #MQTT_USERNAME
            # iotp.params["iotp.params["mqtt_username"]"] = f'sn{received[start:end]}'
            iotp.params["device_cert_filename"] = ""
            iotp.params["device_key_filename"] = ""
            iotp.write()

        elif "+ECCRDCERT:" in received and self.is_model("RNWF11"):
            if "AT+ECCRDCERT=" in rsp and "OK" in rsp:
                self.evt_cert_received(rsp)
        elif self.evt_handler == None:
            pass
        if rsp != "":
            print(f'', flush=True)          # Puts space between sub-state output
            rsp = ""
            received = ""


    def handle_file_system_command(self, cli_list: list) -> None:
        """ Issues file system/Internal (FS) commands
        """
        if len(cli_list):
            cli_list.append(" ")  # Append at least 1 param for sub_cmd checks
            cmd = cli_list[0].upper()
            sub_cmd = cli_list[1].upper()
            # print(f'handle_file_system_command \'{cmd}\'')
            if cmd == "DIR" and sub_cmd.startswith("K") and EN_CERT_SUPPORT:
                self.cmd_issue("AT+FS=2,2", 0)
            elif cmd == "DIR" and sub_cmd.startswith("C") and EN_CERT_SUPPORT:
                self.cmd_issue("AT+FS=2,1", 0)
            elif cmd == "DEL" and sub_cmd.startswith("K") and len(cli_list) == 4 and EN_CERT_SUPPORT:
                fn = str(cli_list[2]).replace('\'', '').replace('\"', '')
                self.cmd_issue(f'AT+FS=3,2,"{fn}"')
            elif cmd == "DEL" and sub_cmd.startswith("C") and len(cli_list) == 4 and EN_CERT_SUPPORT:
                fn = str(cli_list[2]).replace('\'', '').replace('\"', '')
                self.cmd_issue(f'AT+FS=3,1,"{fn}"')
            elif cmd == "SYS":
                print(f'\nSystem Info Request...\n')
                self.cmd_issue_quiet("AT+FS=4", 0)
            elif cmd == "SCAN":
                print(f'\nWi-Fi Scan Request...')
                self.cmd_issue_quiet("AT+WSCN=0", 0, "+WSCNIND:")           # Only show RSP output
            else:
                print(f'FS Unknown Command: {cli_list} {cmd} {len(cli_list)}')
        else:
            print(f'FS Unknown Command: {cli_list}')
    
    def cfg_to_log(self, msg: str = ''):
        # if msg !='':
        #     print(f' cfg_to_log(): {msg}')
        if self.log_file_handle:
            try:    # Write the config file to the log
                cfg = open(f'{APP_CONFIG_FILE}', "r")
                self.log_file_handle.write('\n')
                self.log_state(f'Configuration Settings', '*')
                for item in cfg:
                    self.log_file_handle.write(item)
                self.log_file_handle.write('\n\n')
                cfg.close()
                # print(f' Configuration file logged')
            except:
                # print(f' Configuration was not logged')
                pass

    def keyboard_listen(self) -> None:
        """ Wait for keyboard events """

        # Don't poll keyboard during initial RESET
        if self.app_state == APP_STATE_INIT and self.app_state < 2:     # Ignore ESC during initial AT+RST
            return
        else:
            ret_bool = self.kb.poll_keyboard(True)                      # Allow for single char commands in CLI

        if ret_bool == False:           # ESC pressed
            if LOCAL_ECHO:
                # Second ESC press to exit application
                if self.app_state == APP_STATE_CLI:
                    self.cmd_log(f'Exit Application')
                    sleep(0.1)
                    if self.broker_connected:
                        self.cmd_log(f'\nDisconnecting Broker...')
                        self.cmd_issue_quiet('AT+MQTTDISCONN=0', 0, "+MQTTCONN:0")
                        sleep(0.75)
                        self.cmd_kill(False)
                    #
                    # Its important to disconnect Wi-Fi on exit to notify the AP that the connection is closed.
                    # When the module sends the AP+WSTA=0 disconnect command, it sends the AP a "De-AUTH" packet 
                    # telling the AP to close the connection. Without it, the AP may reject the 'next' connection
                    # from the module.
                    #
                    if self.wifi_connected:
                        self.cmd_log(f'\nDisconnecting Wi-Fi...\n\n')
                        self.cmd_issue_quiet('AT+WSTA=0', 0)
                        sleep(0.75)
                        self.cmd_kill(False)
                    self.cfg_to_log("keyboard_listen()")
                    sleep(0.5)
                    exit(0)
                else:
                    # First ESC press to APP_STATE_CLI
                    self.cmd_check(True)
                    self.cmd_log(f'Exit To CLI...')

                    self.telemetry_index = 0                            # Stop auto telemetry updates on exit to CLI
                    self.demo_loops = 0
                    self.telemetry_interval = 0

                    print('\n')
                    self.set_state_direct(APP_STATE_CLI, 0)
                    if self.broker_connected:
                        self.cmd_log(f'Broker is still connected...\n')
                    else:
                        self.cmd_log(f'Broker is disconnected...\n')
                
                # On exit, [ESC][ESC], write the config file to the log
                # self.cfg_to_log("keyboard_listen()")
        else:
            if self.kb.cmd_received():
                kb_received = self.kb.cmd_get()

                # Process CLI input for handling of AT, MQTT and FS commands

                if kb_received[0] == '+':
                    kb_received = f'AT{kb_received}'
                is_at_cmd = self.kb_data_process(kb_received)
                if is_at_cmd:
                    if self.pub_topic == "":
                        print("AT Command = " + kb_received);
                        self.cmd_issue(kb_received, 1)
                    else:
                        # todo Not supported in kb_data_process() yet
                        print("MQTT Command = " + kb_received)
                        self.mqtt_publish(MQTT_IQOS, MQTT_IRETAIN, self.pub_topic, self.pub_payload)
                elif len(self.kb.cmd):
                    self.kb.cmd = self.kb.cmd.upper()

                    cli = kb_received.strip()
                    cli = cli.split(" ", 3)
                    # Only capitalize the CMD...not the filename
                    # cli[0] = cli[0].upper()
                    if cli[0].upper() == "DIR" and len(cli) == 2 and EN_CERT_SUPPORT:
                        self.handle_file_system_command(cli)
                    elif cli[0].upper() == "DEL" and len(cli) == 3 and EN_CERT_SUPPORT:
                        self.handle_file_system_command(cli)
                    elif cli[0].upper() == "SYS" and len(cli) == 1:
                        self.handle_file_system_command(cli)
                    elif cli[0].upper() == "SCAN" and len(cli) == 1:
                        self.handle_file_system_command(cli)
                    else:
                        print(f'Invalid command or parameters {cli}')
                        self.kb.cmd = ''
                else:
                    print("CLI command not found")
        self.kb.cmd_clear()

    ##################################
    ### run_app (Mainline)
    ##################################
    def run_app(self) -> None:
        """ Mainline application """
        resp: int = 0
        self.keyboard_listen()                                  # read keyboard, scan for exit (ESC) or AT commands
        self.cmd_check(False)                                   # Checks for command timeout

        if self.app_state == APP_STATE_CLI:
            resp = self.sm_cli()                                # Call CLI statemachine
            if resp == APP_STATE_COMPLETE:
                print("\nExit Application", flush=True)
                exit(0)

        if self.app_state == APP_STATE_INIT:                    # Start with statemachine initialization
            resp = self.sm_init()
            if resp == APP_STATE_COMPLETE:
                self.set_state_direct(APP_STATE_START)          # Change 'APP_STATE_START' jump to a state for debug or run
        
        if self.app_state == APP_STATE_WIFI_CONNECT:            # Start Wi-Fi statemachine
            resp = self.sm_wifi_init()
            if resp == APP_STATE_COMPLETE:
                self.set_state_direct(APP_STATE_MQTT_SETTINGS)

        elif self.app_state == APP_STATE_MQTT_SETTINGS:         # Set MQTT settings
            resp = self.sm_mqtt_settings()
            if resp == APP_STATE_COMPLETE:
                self.set_state_direct(APP_STATE_MQTT_CONNECT_BROKER)

        elif self.app_state == APP_STATE_MQTT_CONNECT_BROKER:   # Connect to broker
            resp = self.sm_mqtt_connect()
            if resp == APP_STATE_COMPLETE:
                self.set_state_direct(APP_STATE_DEMO)

        elif self.app_state == APP_STATE_DEMO:             # Loop on the Demo interface
            resp = self.sm_iotc_demo_app()
            if resp == APP_STATE_COMPLETE:
               self.set_state_direct(APP_STATE_DEMO)
        else:
            pass

        rx_data = self.serial_receive()
        if rx_data:
            # Process the received data and format for the display
            self.rx_data_process(rx_data)

            # If an event handler was set for a response call it
            if self.evt_handler:
                self.evt_handler()
                self.evt_handler = None

    def __del__(self) -> None:
        """ Mainline 'destructor' """

        self.cfg_to_log("__del__()")
        
        try:
            self.ser.close()
        except:
            print("  Serial port closure FAILED")
        else:
            print(f'  Serial port \'{self.ser.name}\' closed successfully')

        try:
            if self.log_file_handle:
                self.log_file_handle.close()
                print(f'  Log file "{APP_CMD_LOG_FILE}" closed successfully')
        except:  
            print(f'  Log file "{APP_CMD_LOG_FILE}" closure FAILED')
########################################
# App Startup
########################################
os.system('cls')  # Clear terminal screen

# Auto detect com port
model, com_port = find_com_port()
if model == "":
    # Show failed startup banner
    banner(f' IoT Out-Of-Box MQTT Demonstration v{APP_REL_VERSION}\n'
                     f'              FAILED\n'
                     f'  Compatible device not detected',
           BANNER_BORDER_LEV_2)
    print(f'\n')
    exit(APP_RET_COM_NOT_FOUND)


# Instantiate global classes
ac = IotCloud(com_port, 230400, model)      # Create primary IotCloud object
if APP_CMD_LOG_FILE and ac.log_file_handle:
    logline = f' Log File:         {APP_CMD_LOG_PATH}/{APP_CMD_LOG_FILE} '
else:
    logline = f' Log File:         Disabled'
cfgline = f' Config File:      {ARGS.cfg}'

banner_width = 1
# Show startup banner
banner(f' RNWFxx Out-Of-Box MQTT Demonstration v{ac.__version__}\n'
       f'  Detected:         \'{ac.dev_model}\' on {ac.dev_com_port} \n'
       f'  Display Level:    [ {APP_DISPLAY_LEVEL} ] \n'
       f'\n {cfgline}\n'
       f' {logline}\n',
       BANNER_BORDER_LEV_2)

print(f'{" [ESC] exit to CLI or [ESC][ESC] to QUIT": <}\n')

try:
    MAX_ID_LEN = 23
    if EN_CERT_SUPPORT:
        if len(iotp.params["mqtt_username"]) > MAX_ID_LEN or len(iotp.params["device_cert_filename"]) > MAX_ID_LEN or len(iotp.params["device_key_filename"]) > MAX_ID_LEN:
            print(f'\n\n  Error: Invalid data detected in \'{APP_CONFIG_FILE}\'\n'
                f'  ----------------------------------------\n'
                f'  The maximum string length({MAX_ID_LEN}) has been exceeded by one or more of the following:\n'
                f'      iotp.params["device_cert_filename"]({len(iotp.params["device_cert_filename"])})\n'
                f'      iotp.params["device_key_filename"]({len(iotp.params["device_key_filename"])})\n'
                f'      iotp.params["mqtt_username"]({len(iotp.params["mqtt_username"])})\n')
            exit(1)
    else:
        if len(iotp.params["mqtt_username"]) > MAX_ID_LEN:
            print(f'\n\n  Error: Invalid data detected in \'{APP_CONFIG_FILE}\'\n'
                f'  ----------------------------------------\n'
                f'  The maximum string length({MAX_ID_LEN}) has been exceeded by the following:\n'
                f'      iotp.params["mqtt_username"]({len(iotp.params["mqtt_username"])})\n')
            exit(1)

    while True:  # Start the app
        if ac.app_state_prev != ac.app_state:
            ac.app_state_prev = ac.app_state
        ac.run_app()

except KeyboardInterrupt:
    print(f'\n   [CTRL-C] User Exit')

except serial.SerialException:
    print(f'\n  Serial UART Communication Lost')


# Application/Demo Version