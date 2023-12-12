#!/usr/bin/python3

# © 2023 Microchip Technology Inc. and its subsidiaries
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
    import json
    from time import sleep
    import atexit
except ModuleNotFoundError:
    print(f'\n\n----------------------------------------------')
    print(f' Error! Python module not found.')
    print(f'   Please run "pip install -r requirements.txt"')
    print(f'   from the command line. Then try again.')
    print(f'----------------------------------------------')    
    exit(1)

# Demo state 6 constants
DEVICE_2_CLOUD = True
CLOUD_2_DEVICE = False
NONE_2_NONE = None

# LOCAL_ECHO - Set to True to display each command char
LOCAL_ECHO = True
BLOCK_PERIODIC_TIME_RESP = True
BANNER_BORDER_LEV_1 = '■'  # "─ ━  ═  ■  "
BANNER_BORDER_LEV_2 = '━'  # "─ ━  ═  ■  "
BANNER_BORDER_LEV_3 = '─'  # "─ ━  ═  ■  "

COUNTER_KEY = 67            # 'C'
BUTTON_KEY = 66             # 'B'
REPORT_RATE_KEY = 73        # 'I'
RESUME_KEY = 82             # 'R'
LED0_KEY = 76               # 'L'
HELP_KEY = 72               # 'H'

# Application Configuration File
APP_CONFIG_FILE = "app.cfg"         # File name for application configuration settings
APP_CMD_LOG_PATH = "logs"           # Hardcoded relative log file path

# Object read/write configuration json file
iotp = iot_parameters(APP_CONFIG_FILE, False)

try:
    is_dirty = False

    WIFI_SSID = iotp.params["wifi_ssid"]
    WIFI_PASSPHRASE = iotp.params["wifi_passphrase"]
    WIFI_SECURITY = iotp.params["wifi_security"]
    NTP_SERVER = iotp.params["ntp_server"]
    ID_SCOPE = iotp.params["id_scope"]
    APP_CMD_LOG_FILE = iotp.params["log"]

    # Supported part numbers are in a dictionary of tuples.
    # The device is the key and the tuple contains all the possible
    # device names returned by the AT+GMM command. The identified
    # device determines how the script will run.
    SUPPORTED_RNS_DICT = {"RNWF02": ("PIC32MZW2", "RNWF02"),
                          "RNWF11": ("PIC32MZW1", "RNWF11")
                          }
    MQTT_BROKER_URL = iotp.params["mqtt_broker_url"]
    MQTT_BROKER_PORT = iotp.params["mqtt_broker_port"]
    MQTT_CLIENT_ID = iotp.params["mqtt_client_id"]
    MQTT_PASSWORD = iotp.params["mqtt_password"]
    MQTT_KEEP_ALIVE = iotp.params["mqtt_keep_alive"]
    MQTT_VERSION = iotp.params["mqtt_version"]

    OPERATION_ID = iotp.params["operation_id"]
    ASSIGNED_HUB = iotp.params["assigned_hub"]

    FORCE_DPS_REG = int(iotp.params["force_dps_reg"])
    if FORCE_DPS_REG >= 1 or OPERATION_ID == "" or ASSIGNED_HUB == "":
        OPERATION_ID = iotp.params["operation_id"] = ""
        ASSIGNED_HUB = iotp.params["assigned_hub"] = ""
        iotp.write()

    DEVICE_CERT_FILENAME = iotp.params["device_cert_filename"]
    DEVICE_KEY_FILENAME = iotp.params["device_key_filename"]
    DEVICE_TEMPLATE = iotp.params["device_template"]

    TLS_PROVISION_SERVER = iotp.params["tls_provision_server"]
    TLS_DEVICE_SERVER = iotp.params["tls_device_server"]
    APP_DISPLAY_LEVEL = int(iotp.params["display_level"])
    AT_COMMAND_TIMEOUT = int(iotp.params["at_command_timeout"])  # AT cmds timeout in seconds

    if is_dirty:
        iotp.write()

except KeyError as e:
    banner(f' Error: Configuration parameter {e} missing \n\n'
            f'Verify the parameter {e} in "{APP_CONFIG_FILE}"\n'
            f'  Manually add/edit the parameter OR\n'
           
            f'  Delete "{APP_CONFIG_FILE}" to recreate it on the next run', BANNER_BORDER_LEV_3)
    exit(1)

TLS_CFG_INDEX = 1   # All AT+TLSC commands can be programmed into 1 of 2 banks, 1 or 2.
                    # Then AT+MQTT=7,x will set which bank is used for the TLSC commands.
                    # Use 1 or 2, not 0(AT Spec RNWF11 doc is incorrect)

TLS_CERT_DPS = "DigiCertGlobalRootG2"
TLS_CERT_IOTC = "DigiCertGlobalRootG2"

TLS_CERT_BUILDS = "./Tools/CertificateTool/CertBuilds"

APP_DISPLAY_OFF = 0         # Extra displays off...cleanest output
APP_DISPLAY_STATES = 1      # Display State Banners & lower
APP_DISPLAY_INFO = 2        # Display info and events & lower
APP_DISPLAY_DEMO = 3        # Display 'Demo' IOTC data and lower
APP_DISPLAY_DECODES = 4     # Display Decodes like JSON, CRx & lower

DEMO_LOOP_COUNT = 10        # Number of times to send Telemetry data

API_VERSION_DPS = "2019-03-31"          # API version for DPS call
API_VERSION_DEV_TWIN = "2021-04-12"     # API version for Device Twin call

# -----------------------------------------------------------------------------
# Application States
APP_STATE_CLI = 0                       # CLI state occurs on fatal error OR after the DEMO

APP_STATE_WIFI_CONNECT = 1
APP_STATE_MQTT_SETTINGS = 2
APP_STATE_DPS_REGISTER = 3
APP_STATE_IOTC_CONNECT = 4
APP_STATE_IOTC_GET_SET_DEV_TWIN = 5
APP_STATE_IOTC_DEMO = 6

APP_SUB_STATE_DEMO_LOOP = 2
APP_SUB_STATE_DEMO_SUCCESS_RSP = 4
APP_SUB_STATE_DEMO_FAILURE_RSP = 5

APP_STATE_INIT = APP_STATE_WIFI_CONNECT     # Sets the beginning STATE

APP_STATE_COMPLETE = 254
APP_STATE_UNKNOWN = 255

help_str_0 = f' {APP_STATE_CLI} - APP_STATE_CLI Help\n' \
'  H    - This help screen\n' \
'  AT+  - AT command with or w/o the \'AT\' eg: \'AT+GMM\' or \'+GMM\'\n' \
'  DIR  - List certs & keys. eg: dir [c | k] \n' \
'  DEL  - Delete certs & keys. eg: del [c | k] <FILENAME>\n' \
'  SCAN - Scan & displays Wi-Fi information\n' \
'  SYS  - Displays IP address, firmware and file system info\n' \
'  ESC  - [ESC] key. Exits application\n'

help_str_6 = f' {APP_STATE_IOTC_DEMO} - APP_STATE_IOTC_DEMO\n' \
'  H    - This help screen\n' \
'  B    - Telemetry: Increment \'buttonEvent.press_count\'(0->N)\n' \
'  C    - Telemetry: Increment \'counter\'(0->N)\n' \
'  L    - Property:  Increment \'LED0\' (1, 2, 3)\n' \
'  I    - Property:  Increment \'reportRate\' (0s, 2s, 5s, 10s) \n' \
'  R    - Resume Demo (Wi-Fi, Azure Reconnect)\n' \
'  AT+  - AT command with or w/o the \'AT\' eg: \'AT+GMM\' or \'+GMM\'\n' \
'  DIR  - List certs & keys. eg: dir [c | k] \n' \
'  DEL  - Delete certs & keys. eg: del [c | k] <FILENAME>\n' \
'  SCAN - Scan & displays Wi-Fi information\n' \
'  SYS  - Displays IP address, firmware and file system info\n' \
'  ESC  - [ESC] key exits to CLI. [ESC] x 2 exits application\n'

# -----------------------------------------------------------------------------
# Azure Device Provisioning Service (DPS) Topics
TOPIC_IOTC_TELEMETRY = "devices/" + MQTT_CLIENT_ID + "/messages/events/"

# initiate DPS registration
TOPIC_DPS_INIT_REG = "$dps/registrations/PUT/iotdps-register/?$rid="

TOPIC_DPS_POLL_REG_COMPLETE1 = "$dps/registrations/GET/iotdps-get-operationstatus/?$rid="
TOPIC_DPS_POLL_REG_COMPLETE2 = "&operationId="

# DPS result topic (for subscription)
TOPIC_DPS_RESULT = "$dps/registrations/res/#"

# RNFW11 only value.
MQTT_SUBSCRIPTION_READ_THRESHOLD = 700

# Azure IoT Central Topics
# telemetry topic (for publish)
# write property to cloud topic (for publish)
TOPIC_IOTC_WRITE_PROPERTY = "$iothub/twin/PATCH/properties/reported/?rid="

# request all device twin properties (for publish)
TOPIC_IOTC_PROPERTY_REQUEST = "$iothub/twin/GET/?$rid=getTwin"

TOPIC_IOTC_CMD_RESP = "$iothub/methods/res/200/?$rid="

# method topic (for subscription)
TOPIC_IOTC_METHOD_REQ = "$iothub/methods/POST/#"

# property topics (for subscriptions)
TOPIC_IOTC_PROP_DESIRED = "$iothub/twin/PATCH/properties/desired/#"
TOPIC_IOTC_PROPERTY_RES = "$iothub/twin/res/#"
# -----------------------------------------------------------------------------

# APP OS Return/Error codes
APP_RET_OK = 0
APP_RET_COM_NOT_FOUND = 1
APP_RET_COM_BUSY = 2


def detect_port(com_ports: list, supported_pn: dict) -> str:
    """
    Detect the connected COM port by sending +GMM command to each
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
                    s = serial.Serial(port=port, baudrate=230400, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout=4.0, write_timeout=4.0, inter_byte_timeout=0.5)
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


def find_com_port() -> str:
    """
    Attempts to find a COM port. If found returns a Windows
    compatible "COMx" string. If not found the returned string is
    empty.
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
    def __init__(self) -> None:
        self.kb = kbhit.KBHit()
        self.input_buf = ""
        self.cmd = ""               # Word commands
        self.key_cmd = ""           # Single key commands
        # Single key commands from the CLI
        self.EXIT_KEY = 27          # ESC

        self.key_commands = [COUNTER_KEY, BUTTON_KEY, REPORT_RATE_KEY, LED0_KEY, RESUME_KEY, HELP_KEY]

    def poll_keyboard(self) -> bool:
        if self.kb.kbhit():
            c = self.kb.getch()
            c_upper = c.upper()
            if len(c) == 0:
                return True
            if ord(c) == self.EXIT_KEY:
                return False

            # Limit key_cmd registration to 1st buffer char only
            if len(self.input_buf) == 0:
                for self.key_cmd in self.key_commands:
                    if self.key_cmd == ord(c_upper):
                        break
                    else:
                        self.key_cmd = ''

            if self.key_cmd:
                #print(f'KeyCmd: {self.key_cmd} ')
                self.cmd = ''
                self.input_buf = ''
                return True             # Return immediately for processing

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
    def __init__(self, port: str, baud: int) -> None:
        # initialize class variables
        self.ser_buf = ""  # serial buffer for processing messages

        # main application state
        self.app_state = APP_STATE_INIT
        self.app_sub_state = 0
        self.app_state_prev = -1
        self.app_wait = False
        self.next_sub_state_offset = 1

        # firmware Syntax for parse RNFW02: '+GMR:"1.0.0 0 630f6fcf [13:57:15 Jun 27 2023]"'
        # firmware Syntax for parse RNFW11: '+GMR:"78de24c4 [09:48:06 Nov  2 2023]"'
        self.fw_version = "Not Reported"
        self.fw_hash = "Not Reported"
        self.fw_datestamp = "Not Reported"

        self.log_file_handle = ""       # Log file handle if created

        # MQTT handling variables
        self.rid = 0  # request id field used by some publish commands.
        #   incremented between publishing attempts
        self.sub_payload = ""  # application serial buffer used to process received data.
        self.pub_topic = ""
        self.pub_payload = ""

        # wifi connection related variables
        self.wifi_connected = False  # set to True when WiFi connected

        # DPS connection variables
        self.broker_connected = False  # set to True when connected to DPS broker

        # IOTC connection variables
        self.iotc_topic_index = 1  # tracks how many topics have been subscribed to for
        # iotc event call back to adjust the state variable.

        # IOTC Demo variables
        self.iotc_button_event = 0          # Telemetry: "buttonEvent" reported to Azure
        self.iotc_button_press_count = 0    # Telemetry: "buttonEvent:press_count" reported to Azure
        self.iotc_counter = ''              # Telemetry: "counter" reported to Azure

        self.iotc_reboot_delay = ''         # Command: Reboot delay from Azure
        self.iotc_echo = ''                 # Command: Echo command from Azure

        self.telemetry_interval = ''        # Property: Telemetry interval
        self.iotc_led0 = ''                 # Property: "LED0"
        self.ip_addr_ipv4 = 'n/a'           # Property: IP Address reported to Azure
        self.ip_addr_ipv6 = 'n/a'           # IP Address returned from router
        self.telemetry_ints = [0, 2, 5, 10] # Demo state 6 supported telemetry intervals in seconds
        self.telemetry_index = 0            # Demo state 6 index to current telemetry interval
        self.demo_loops = 0                 # Max number of telemetry updates in State 6 Demo

        self.last_utc_update = 0            # Update this each time the time signal come in
        self.resp_dict = {}
        self.reboot_timer = Delay_Non_Blocking()

        self.at_quiet_command = False       # Disable CLI command output for 1 cmd before reset
        self.at_command = ""                # The AT command currently being executed
        self.at_command_prev = ""           # Previously executed AT command
        self.at_command_resp = ""           # Alt 'response' to use if the command itself isn't the desired response

        self.at_command_timer = Delay_Non_Blocking()
        self.at_command_timer.stop()
        self.at_command_timeout = AT_COMMAND_TIMEOUT  # AT command timeout. Commands must complete within this many seconds

        self.evt_handler = ""

        self.SER_TIMEOUT = 0.1  # sets how long pyserial will delay waiting for a character
        #   reading a character a time, no need to wait for long messages

        # initialize pyserial, delay and keyboard handler classes
        try:
            self.ser = serial.Serial(port, baud, timeout=self.SER_TIMEOUT)
        except:
            print(f'  Serial port open FAILED. Is {port} in use?')
            exit(APP_RET_COM_BUSY)
        self.delay = Delay_Non_Blocking()
        self.kb = Polling_KB_CMD_Input()

        self.open_log()                             # Start the log file

    def set_log_file_name(self) -> str | datetime:
        """ Decodes and sets the global APP_CMD_LOG_FILE
            and returns the constructed log 'filename' and the
            datetime object for its creation.
        """
        file_name = globals()["APP_CMD_LOG_FILE"]
        now = datetime.now()
        t = now.strftime("%H-%M-%S")
        d = now.strftime("%b_%d_%Y")
        file_name = file_name.replace("%m", "%M").replace("%M", MODEL)
        file_name = file_name.replace("%d", "%D").replace("%D", d)
        file_name = file_name.replace("%t", "%T").replace("%T", t)
        globals()["APP_CMD_LOG_FILE"] = file_name
        return file_name, now

    def open_log(self) -> None:
        """ Sets the logfile handle, if applicable and opens the log file for writing """
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
                self.log_file_handle.write(f'IoT Out-Of-Box Azure Demonstration Command Log\n')
                self.log_file_handle.write(f'{"-" * 46}\n')
                self.log_file_handle.write(f'Filename:  {file_name}\n')
                self.log_file_handle.write(f'Created:   {now.strftime("%b %d, %Y")} {now.strftime("%H:%M:%S")}\n')
                self.log_file_handle.write(f'Device:    {MODEL}\n')
                self.log_file_handle.write(f'COM Port:  {COM_PORT}\n')
                self.log_file_handle.write(f'Force DPS: {FORCE_DPS_REG}\n')
                self.log_file_handle.write(f'{"-" * 46}\n\n')
        else:
            self.log_file_handle = None

    def log_state(self, msg: str, border_char: str = '#', single_line: bool = False) -> None:
        """ Adds a banner in the log if log is used"""
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
        """ Outputs the CMD/RSP strings to the CLI and option log file """

        # Remove any NULL's returned by the device such as during AT+RST
        msg = ''.join(msg.split('\x00'))
        msg = msg.strip('\n')
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

    def is_model(self, dev: str, val_true: any = True, val_false: any = False) -> any:
        """ Verifies device MODEL number and returns True, False or the passed in type if true """
        global MODEL, FORCE_DPS_REG, OPERATION_ID, ASSIGNED_HUB
        # legacy_mode applies to the RNWF11 only. It causes the RNWF11 to act like a RNWF02 device when:
        #   The device is a RNWF11 and both OPERATION_ID and ASSIGNED_HUB are set or FORCE_DPS_REG is true
        legacy_mode = (dev == MODEL) and ((OPERATION_ID != "" and ASSIGNED_HUB != "") or bool(FORCE_DPS_REG))

        if dev == "RNWF11" and dev == MODEL and legacy_mode:
            return val_false
        if dev == MODEL:
            return val_true
        else:
            return val_false

    def hex_rid(self, rid: int = -1) -> str:
        """ Converts class 'self.rid' into a hex string w/o '0x' prefix for Azure MQTT commands.
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
                pass

    # keyboard processing
    def kb_data_process(self, received: str) -> bool:
        """
        Process a passed in str and returns True if an AT+
        command or False if its a FS (File System) command.
        If a FS command that command is saved in the class.
        """
        if received.startswith("AT"):
            self.pub_topic = ""
            self.sub_topic = ""
            return True
        return False

    def set_state(self, new_state: int, new_sub_state: int = 0) -> None:
        """
        Sets a new state and optionally a new sub-state. If the sub_state
        is not passed, the default 0 is used showing the state banner
        """
        if APP_STATE_CLI <= new_state <= APP_STATE_IOTC_DEMO:
            self.app_state_prev = self.app_state
            self.app_state = new_state
            self.app_sub_state = new_sub_state

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
                self.cmd_log(f'Command "{self.at_command}" timed out after {run_time:.2f}s')
                print(f'\n')
                self.at_command_timer.stop()
                self.at_command_prev = self.at_command

                self.at_command = ""
                self.at_command_resp = ""
                self.at_command_timeout = 0 # AT_COMMAND_TIMEOUT

                err_sig = f'{self.app_state:0>2}:{self.app_sub_state:0>2}'

                # Special handling of time critical command calls
                if err_sig == '01:21':
                    self.err_handler(run_time, f'AT+SNTPC=3,"{NTP_SERVER}" [ER]:NTP server did not respond @ [{err_sig}]', '01:09')
                # other elif go here
                else:
                    pass
                # Make sure this is last
                self.set_state(APP_STATE_CLI, 0)
            elif terminate:
                banner(f' Command "{self.at_command}" terminated at {run_time:.2f}s', '▫')
                self.at_command_timer.stop()
                self.at_command_prev = self.at_command
                self.at_command = ""
                self.at_command_resp = ""
                self.at_command_timeout = 0 # AT_COMMAND_TIMEOUT

    def cmd_issue_quiet(self,
                  command: str,
                  next_sub_state_offset: int = 0,
                  alt_resp: str = "",
                  timeout: int = AT_COMMAND_TIMEOUT) -> None:
        self.at_quiet_command = True
        self.cmd_issue(command, next_sub_state_offset, alt_resp, timeout)

    """ This is an alternate function to submit AT+ commands but blocks CLI screen output.
        If a log file is used the command will appear in the logs.
        Also the default 'next_sub_state_offset' is set to '0' so that it can be used
        during startup and not increment the programmed substate.
    """
    # cmd_issue() - Issue serial command to AzureCloud
    # Modified to automatically wait until a response string
    # is received in 'rx_data_process() function where the 'next'
    # step will be incremented by 1, unless the 'next_step' value is
    # passed where the specified 'next_step' will be "added" to
    # the 'app_sub_state' allowing for a relative sub-state jump.
    # Negative offsets are allowed.

    def cmd_issue(self,
                  command: str,
                  next_sub_state_offset: int = 1,
                  alt_resp: str = "",
                  timeout: int = AT_COMMAND_TIMEOUT) -> None:
        command = self.substr_swap(command, {'\r': '', '\n': ''})

        # Debug support for NOOP command without any processing
        if command == "NOOP":
            self.cmd_log(f'CMD[{self.app_state:0>2}.{self.app_sub_state:0>2}]: NOOP - No operation')
            self.cmd_log(f'RSP[{self.app_state:0>2}.{self.app_sub_state:0>2}]: NOOP - No operation')
            print("\r")
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

    # poll serial port for received. read until prompt '>',
    # return whole message
    def serial_receive(self) -> str:
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

    # returns JSON from AT+MQTTPUB event notification payload
    def process_topic_notification(self, payload: str) -> tuple[any, int]:
        ''' Process the MQTTSUBRX response into proper JSON for variable extraction
        DPS_STATE 03:02 +MQTTSUBRX:0,0,0,"$dps/registrations/res/202/?$rid=1&retry-after=3","{\\"operationId\\":\\"5.f459fec3883c3357.2c044a97-aa77-40f1-bf49-add7330b9704\\",\\"status\\":\\"assigning\\"}"
        operationId:   "5.f459fec3883c3357.2c044a97-aa77-40f1-bf49-xxxxxxxxxxxx"
        status:        "assigning"
        DPS_STATE 03:03 +MQTTSUBRX:0,0,0,"$dps/registrations/res/200/?$rid=2",...
        operationId:  "5.f459fec3883c3357.2c044a97-aa77-40f1-bf49-xxxxxxxxxxxx"
        status:       "assigned"
        '''
        jsn_str = ''
        # RegX to capture all text between '{}'
        jsn_list = re.findall(r'\{.*?}.*', payload)

        # Get HTML response, usually 200 or 202
        # 200: Request successful and complete
        # 202: Request accepted for processing, but processing is NOT complete
        resp_list = payload.split("/", 4)
        try:
            resp_code = int(resp_list[3])
        except:
            resp_code = -1
        # banner(f'Payload:\n{payload}\n{jsn_list}')
        try:
            if len(jsn_list):
                # Cleanup the jsn_list by replacing characters to form a proper JSON message
                jsn_str = self.substr_swap(jsn_list[0], {'\r': '', '\n': '', '\\': '', '}"': '}'})
                # Convert to JSON object
                json_obj = json.loads(jsn_str)
            else:
                json_obj = None
                payload = self.substr_swap(payload, {'\r': '', '\n': '', '>': ''})
                resp_list = payload.split(",", 6)
                # This is the command that will request the twin variables but using the proper
                # sized buffer contained in 'resp_list[5]' + 10 characters as a buffer
                self.cmd_issue(f'AT+MQTTSUBRD={resp_list[3]}, {resp_list[4]}, {resp_list[5] + 10}')
        except:
            banner(f'JSON Invalid:     \'{jsn_str}\'\n'
                   f'  JSON Size       {len(jsn_str)} bytes\n'
                   f'  Payload Size:   {len(payload)} bytes\n'
                   f'  Response Code:  {resp_code}\n')
            # exit(10)
        return json_obj, resp_code

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

    def evt_wifi_scan_result(self, rx: str) -> None:
        """ Outputs the Wi-Fi scan results """
        if len(rx):
            print('\n')
            banner(f' Wi-Fi \'Passive\' Scan Results')

            rx = self.substr_swap(rx, {"\r\n\r": "", "\\0": "", '"': "", "+WSCNDONE:": "\n"})
            rx.removesuffix('+WSCNDONE:')
            wifi_list = list(rx.split("+WSCNIND:"))
            count = 0
            for w in range(1, len(wifi_list) - 1):
                count += 1
                wifi = wifi_list[w]
                wifi = list(wifi.split(','))
                print(f'  {str(count):>2}. '
                      f' {str(wifi[3])}  '             # MAC address
                      f'Ch: {str(wifi[2]):>2}  '         # Wi-Fi Channel
                      f'Sec: {wifi[1]}  '                # Wi-Fi Security type
                      f'Sig: {str(wifi[0]):>3}dBm '     # Signal strength
                      f'  "{wifi[4]}"')                 # Wi-Fi SSID

    def evt_fs_data_result(self, rx: str) -> None:
        """ Outputs file system (FS) results """
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
                banner(f' Network Info (AT+WSTA=1)\n'
                       f'  IP Address IPv4:   {self.ip_addr_ipv4}\n'
                       f'  IP Address IPv6:   {self.ip_addr_ipv6}\n'
                       f'  Wi-Fi Connected:   {self.wifi_connected}\n'
                       f'  Broker Connected:  {self.broker_connected}\n\n'
                       f'Firmware Info (AT+GMR)\n'
                       f'  Version:           {self.fw_version}\n'
                       f'  Date:              {self.fw_datestamp}\n'
                       f'  Signature:         {self.fw_hash}\n\n'
                       f'File System Info (AT+FS=4)\n'
                       f'  Free Space:        {fs_status_list[1]} bytes\n'
                       f'  File Handles:      {fs_status_list[2]}\n\n'
                       )
            elif "+FS=2" in rx:  # File system DIR (List)
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
                # +GMR:"1.0.0 0 630f6fcf [13:57:15 Jun 27 2023]" OK <- RNWF02 format
                # +GMR:"78de24c4 [09:48:06 Nov  2 2023]" OK         <- RNWF11 format
                # +GMR:"78de24c4 [16:59:49 Nov 22 2023]" OK         <- RNWF11 Beta format
                to_remove = {'"': '', '[': '', ']': '', '>': '',
                             '\r\n': '', 'AT+GMR': '', '+GMR:': '', 'OK': ''}
                parsed = self.substr_swap(rx, to_remove)
                parsed = ' '.join(parsed.split())
                parsed = parsed.split(' ')

                for item in parsed:
                    if item.__contains__('.') and self.fw_version == rep_str:
                        self.fw_version = item
                    elif len(item) == 8 and self.fw_hash == rep_str:
                        self.fw_hash = item
                    elif item.__contains__(':') and self.fw_datestamp == rep_str:
                        self.fw_datestamp = f'{item} '
                    elif len(item) < 1 or item == '0':
                        continue
                    else:
                        self.fw_datestamp += f'{item} '
            except:
                self.fw_version = "???"
                self.fw_hash = "???"
                self.fw_datestamp = "???"

            if APP_DISPLAY_LEVEL >= APP_DISPLAY_INFO:
                banner_str = (f' Firmware Info:\n  Version:    {self.fw_version}\n'
                              f'  Date:       {self.fw_datestamp}\n  Signature:  {self.fw_hash}')
                banner(banner_str)

    def evt_wifi_connected(self) -> None:
        """ Outputs Wi-Fi status on change """
        if APP_DISPLAY_LEVEL >= APP_DISPLAY_INFO:
            if self.wifi_connected == True:
                banner(" Event: Wi-Fi connected...(wait for NTP) ")
            else:
                banner(" Event: Wi-Fi not connected")

    def evt_dps_topic_notified(self) -> None:
        """ Handles Azure DPS results """
        global OPERATION_ID, ASSIGNED_HUB
        jsn, resp_code = self.process_topic_notification(self.sub_payload)

        if OPERATION_ID == "":
            try:
                OPERATION_ID = jsn["operationId"]  # DPS state 12 complete...got operationalId
                OPERATION_ID = iotp.params["operation_id"] = jsn["operationId"]
                if self.sub_payload.__contains__('errorCode'):
                    raise Exception("DPS Negotiation error")
            except:
                banner(f' Error: Failed to initiate Azure\'s DPS negotiation. \n'
                        f'Possible local/remote certificate or \'ID Scope\' issue. \n\n'
                        f'  * Reload device certificate and key to device if applicable.\n'
                        f'  * Upload the appropriate subordinate certificate to Azure.\n'
                        f'  * Verify \'id_scope\' string in the config \'{APP_CONFIG_FILE}\'file.\n'
                        f'\nCMD[{self.app_state}.{self.app_sub_state}]: {self.at_command_prev}\n'
                        f'JSON: "{jsn}"', BANNER_BORDER_LEV_1)
                exit(1)
            if APP_DISPLAY_LEVEL >= APP_DISPLAY_INFO:
                banner(
                    f' Event: DPS Subscription Notification \n'
                    f' Operation ID:     "{OPERATION_ID}"\n'
                    f' Assigned Hub:     "{ASSIGNED_HUB}"\n'
                    f' Status:           "{jsn["status"]}"\n'
                    f' Response Code:    {resp_code}')
                if APP_DISPLAY_LEVEL >= APP_DISPLAY_DECODES:
                    json_pretty = json.dumps(jsn, indent=4)
                    banner(f' JSON Decode of \'+MQTTSUBRX\' RSP[{self.app_state}:{self.app_sub_state - 1}]'
                            f'{json_pretty}')
            self.app_sub_state += 1
        elif jsn["status"] == "assigning":  # DPS state running...wait for "assigned"
            pass
            # Do not update state. Waiting for 'assigning' to change to 'assigned'
            # Also need to clear the Payload below or the assignment will not be caught
        elif jsn["status"] == "assigned":  # DPS state complete...status == assigned
            self.app_sub_state += 1
            # We need this in the next IOTC statemachine for MQTT
            ASSIGNED_HUB = iotp.params["assigned_hub"] = jsn["registrationState"]["assignedHub"]
            iotp.write()
            if APP_DISPLAY_LEVEL >= APP_DISPLAY_INFO:
                banner(
                    f' Event: DPS Subscription Notification(cont) \n'
                    f' Operation ID:     "{OPERATION_ID}"\n'
                    f' Assigned Hub:     "{ASSIGNED_HUB}"\n'
                    f' Status:           "{jsn["status"]}"\n'
                    f' Response Code:    {resp_code}')

                if APP_DISPLAY_LEVEL >= APP_DISPLAY_DECODES:
                    json_pretty = json.dumps(jsn, indent=4)
                    banner(f' JSON Decode of \'+MQTTSUBRX\' RSP[{self.app_state}:{self.app_sub_state - 1}]\n'
                           f'{json_pretty}')
        self.sub_payload = ""

    def evt_iotc_command(self) -> None:
        """ Handles Azure IOTC event
            'echoString': Displays a message sent from Azure
            'delay':      Sets time before rebooting in the form PT#.#X
                eg:         PT1S - reboot in 1s
                            PT2M - reboots in 2 minutes (120s)
                            PT1H - reboots in 1 hour (3600s)
                            * also supports decimals i.e. PT1.5M (90s)
            * A delay of 0S, 0M or 0H, returns a "status=Failure" to Azure for status testing
        """
        # Accepted Commands:
        # ------------------
        # +MQTTSUBRX:0,0,0,"$iothub/methods/POST/echo/?$rid=1","{\"echoString\":\"test\"}"
        # +MQTTSUBRX: 0, 0, 0, "$iothub/methods/POST/reboot/?$rid=3", "{\"delay\":\"PT10S\"}"

        rsp = self.sub_payload
        rsp = self.substr_swap(rsp, {">": "", "OK": "[OK]", "ERROR": "[ER]", "\r": "", "\n": " "})
        rsp = rsp.rstrip()
        self.cmd_log(f'CRx[{self.app_state:0>2}.{self.app_sub_state:0>2}]: {rsp} \n')
        # 'rid' value is hex not decimal and the response value MUST be the same hex value as the
        # original Azure command "CRx:" received. Azure will increment the 'rid' value on each
        # command, so we receive it here, then set the class 'rid' value to the one received.
        self.set_rid_from_string(rsp)
        azure_cmd_dict: dict = {"echoString": "", "delay": ""}
        (payload, resp_code) = self.process_topic_notification(self.sub_payload)

        self.set_rid_from_string(self.sub_payload)
        azure_cmd_dict.update(payload)

        # After receiving a "Message" command from the cloud we have to acknowledge it otherwise Azure will fail it
        # on the cloud side. State 3 in the Demo handles sending out the command success acknowledgement.
        if azure_cmd_dict['echoString'] != "":
            if payload['echoString'] is None:
                # self.iotc_echo = ""
                self.demo_display('echoString', CLOUD_2_DEVICE)
                self.set_state(APP_STATE_IOTC_DEMO, APP_SUB_STATE_DEMO_FAILURE_RSP)  # Send "AT+MQTTPUB ... status=Failure" to Azure
                self.sub_payload = ""
                return
            else:
                self.iotc_echo = azure_cmd_dict["echoString"]
                self.demo_display('echoString', CLOUD_2_DEVICE)
                self.set_state(APP_STATE_IOTC_DEMO, APP_SUB_STATE_DEMO_SUCCESS_RSP)  # Send "AT+MQTTPUB ... status=Success" to Azure
        elif azure_cmd_dict['delay'] != "":
            # If delay is an empty string, turn off interval timer to prevent a crash
            if payload['delay'] is None:
                self.demo_display('reboot', CLOUD_2_DEVICE)
                self.sub_payload = ""
                self.set_state(APP_STATE_IOTC_DEMO, APP_SUB_STATE_DEMO_FAILURE_RSP)
                return
            else:
                re_list = re.findall(r'^(PT)(\d*[.]?\d*)([S,M,H])', azure_cmd_dict['delay'])
            # If cmd is correct syntax, then 're.findall' should return
            # [('PT', '#.#','S|M|H')] - only interested if return is NOT empty
            # and the value of '#.#'.
            # Azure supports float time periods like 'PT1.5H' so we need a float until
            # its converted to integer seconds
            if len(re_list):
                delay = float(re_list[0][1])
                if re_list[0][2] == 'H':        # Hours specified, convert to seconds
                    delay *= 3600.0
                elif re_list[0][2] == 'M':      # Minutes specified, convert to seconds
                    delay *= 60.0
                elif re_list[0][2] == 'S':      # Seconds specified
                    pass
                else:
                    delay = 0

                delay = int(delay)              # Convert to an INT; Floats cause issues with the UI output

                if delay > 0:   # Send "AT+MQTTPUB ... status=Success" to Azure
                                # AND start the reboot timer
                    self.set_state(APP_STATE_IOTC_DEMO, APP_SUB_STATE_DEMO_SUCCESS_RSP)
                    self.iotc_reboot_delay = delay
                    self.reboot_timer.start()
                    status = 'Success'
                else:           # Send "AT+MQTTPUB ... status=Success" to Azure
                                # AND cancel the reboot
                    self.set_state(APP_STATE_IOTC_DEMO, APP_SUB_STATE_DEMO_SUCCESS_RSP)
                    self.iotc_reboot_delay = 0
                    self.reboot_timer.stop()
                    status = 'Failure'

                # banner(f' Command:      "delay", RID = {self.rid}\n'
                #        f'Data:         "{azure_cmd_dict["delay"]}"\n'
                #        f'Reboot Delay: "{delay:,.0f}s"\n'
                #        f'Status:       "{status}"'
                #        )
                self.demo_display('reboot', CLOUD_2_DEVICE)
                if APP_DISPLAY_LEVEL >= APP_DISPLAY_DECODES:
                    if status == 'Failure':
                        print(f'* Reboot cancelled with \'0\' time parameter from Azure, eg: \'PT0S, PT0M or PT0H\'\n'
                            f'  Reported \'failure\' status on cancellations is for demonstration only.')
                    else:
                        print(f'  * Reboot in approximately {delay:,.0f} seconds!')

            else:
                banner(f' Error! Invalid "delay" command.\n'
                       f'Func:   "evt_iotc_command()"\n'
                       f'Delay:  "{re_list[0][1]}"\n'
                       f'S|M|H:  "{re_list[0][2]}"'
                       , BANNER_BORDER_LEV_1)
        else:
            pass
        self.sub_payload = ""
        return

    def property_int_response(self, property_name: str, topic: str, payload: str) -> int:
        """Handles Azure integer response"""
        # (topic,payload) = self.process_topic_notification(self.sub_payload)
        # todo: Remove topic param??
        if property_name in payload:
            json_payload = json.loads(payload)
            version = json_payload["$version"]
            print("$version = " + str(version))
            int_val = json_payload[property_name]
            ad = property_name + " set to: " + str(int_val)
            print(ad)
            resp = '{\\\"' + property_name + '\\\" : {\\\"ac\\\" : 200, \\\"av\\\" : ' + str(
                version) + ', \\\"ad\\\" : \\\"' + ad + '\\\", \\\"value\\\" : ' + str(int_val) + '}}'
            self.rid += 1
            self.mqtt_publish(0, 0, (TOPIC_IOTC_WRITE_PROPERTY + self.hex_rid()), resp)
            return int(int_val)

    def evt_iotc_property_received(self) -> None:
        """ Handles Azure IOTC property change event """
        (json_obj, resp_code) = self.process_topic_notification(self.sub_payload)

        # msg = f' Property updated from IoT Central\n'

        for key in json_obj:
            key_str = str(key).replace(':', '')
            if key == "LED0":
                # msg += f'  \'{key_str}\' was updated from \'{self.iotc_led0}\' to \'{json_obj[key]}\''
                self.iotc_led0 = int(json_obj[key])
                self.demo_display('LED0', CLOUD_2_DEVICE)
            elif key == "reportRate":
                # msg += f'  \'{key_str}\' was updated from \'{self.telemetry_interval}\' to \'{json_obj[key]}\''
                self.telemetry_interval = int(json_obj[key])
                if self.telemetry_interval > 0:
                    self.delay.stop()
                    self.demo_loops = DEMO_LOOP_COUNT       # This will kick off reportRate update to Azure
                else:
                    self.telemetry_interval = 0
                    self.demo_loops = 0                     # Stop the interval if 0 or negative

                self.demo_display('reportRate', CLOUD_2_DEVICE)
            elif key == "ipAddress":
                # msg += f'  \'{key_str}\' cannot be updated from the cloud! \'{self.ip_addr_ipv4}\''
                self.telemetry_interval = json_obj[key]
                self.demo_display('ipAddress', CLOUD_2_DEVICE)
            elif key == "$version":
                ver = {json_obj[key_str]}
                pass
            else:
                dbg_banner(f'Unsupported {key_str} received...\n'
                           f'  Key:{key} Value:{json_obj[key]}')
                return
        # if msg != '':
        #     banner(msg)
        rsp = self.sub_payload
        rsp = self.substr_swap(rsp, {">": "", "OK": "[OK]", "ERROR": "[ER]", "\r": "", "\n": " "})
        rsp = rsp.rstrip()
        print(f'PRx[{self.app_state:0>2}.{self.app_sub_state:0>2}]: {rsp} \n', flush=True, end='')

        self.demo_display()
        self.sub_payload = ""

    def evt_iotc_property_download(self) -> None:
        """ Handles Azure JSON payload return strings """
        payload: any = ""
        resp_code: int = 0
        try:
            (payload, resp_code) = self.process_topic_notification(self.sub_payload)
            if "reportRate" in payload["desired"]:
                self.telemetry_interval = payload["reported"]["reportRate"]
                self.demo_display("reportRate", CLOUD_2_DEVICE)
                # print(f'Telemetry Interval set to {self.telemetry_interval}s based on Device Twin State')
            if "LED0" in payload["desired"]:
                self.iotc_led0 = int(payload["reported"]["LED0"])
                # print(f'LED0 desired as "{str(self.iotc_led0)}" based on Device Twin State')
            if "ipAddress" in payload["reported"]:
                self.ip_addr_ipv4 = payload["reported"]["ipAddress"]
                self.demo_display("ipAddress", CLOUD_2_DEVICE)
                # print(f'IP Address reported as "{str(self.ip_addr_ipv4)}" based on Device Twin State')
        except:
            banner(f' Error: Failed to read Azure\'s \'Device Twin\' setting(s)\'s \n'
                   f'Possible issue with the Azure service or the \'Device Template\' for the {MODEL}.\n\n'
                   f'  * Payload must contain \'reported\' values for \'ipAddress\', \'LED0\', & \'reportRate\'\n'
                   f'  * Issue may clear itself after a period of time of 24h or more.\n'
                   f'\nCMD[{self.app_state}.{self.app_sub_state}]: {self.at_command_prev}\n'
                   f'JSON: "{payload}"', BANNER_BORDER_LEV_1)

            # exit(1)
            # self.cmd_issue(f'AT+AT+MQTTSUBRD=')
        self.sub_payload = ""

    def evt_cert_received(self, rsp) -> None:
        """
        RNWF11 specific function. Handles the Certificate response from the device
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
                    os.makedirs(f'{globals()["TLS_CERT_BUILDS"]}/{globals()["MQTT_CLIENT_ID"]}')
                except FileExistsError:
                    # directory already exists
                    pass
                if fmt > 0 and fmt < 4:
                    f = open(f'{globals()["TLS_CERT_BUILDS"]}/{globals()["MQTT_CLIENT_ID"]}/{file_name_list[fmt]}', "w")
                    f.write(cert)
                    f.close()
            if APP_DISPLAY_LEVEL >= globals()["APP_DISPLAY_INFO"]:

                banner(f' Certificate Written:\n  File Name:  "{file_name_list[fmt]}"\n'
                       f'  Path:       "{globals()["TLS_CERT_BUILDS"]}/{globals()["MQTT_CLIENT_ID"]}/\"')
            if APP_DISPLAY_LEVEL >= globals()["APP_DISPLAY_DECODES"]:
                print(cert)
        except Exception as e:
            banner(f' Certificate Write FAILED:\n  File Name:  "{file_name_list[fmt]}"\n'
                   f'  Path:       "{globals()["TLS_CERT_BUILDS"]}/{globals()["MQTT_CLIENT_ID"]}/\"', "■")
        return

    ##################################
    ### 0 - APP_STATE_CLI
    ##################################
    def sm_cli(self) -> int:
        """ CLI State machine entry point """

        if self.app_sub_state == 0:         # Sub state 0 - Shows CLI Banner
          banner(f' Command Line Interface \n', BANNER_BORDER_LEV_3)
          self.set_state(APP_STATE_CLI, 1)
          self.at_command = self.at_command_resp = ""
          self.at_command_timeout = 0
          self.app_wait = False
        else:
            if self.app_wait:
                return self.app_state
            elif self.kb.key_cmd == HELP_KEY:
                self.kb.key_cmd = ''
                banner(help_str_0, BANNER_BORDER_LEV_2)
            
            elif self.app_sub_state == 1:                   # CLI Help Display
                banner(f'{help_str_0}', BANNER_BORDER_LEV_3)
                self.set_state(APP_STATE_CLI, 2)
                return self.app_state

            elif self.app_sub_state == 2:                   # CLI until exit
                # In the CLI we stay in this state until we are done
                self.set_state(APP_STATE_CLI, 2)
                return self.app_state
            
            elif self.app_sub_state < APP_STATE_COMPLETE:  # Bounce back to sub state 2
                # In the CLI we stay in this state until we are done
                self.set_state(APP_STATE_CLI, 2)
                return self.app_state
            
            elif self.app_sub_state == APP_STATE_COMPLETE:  # Exit app from CLI
                self.set_state(APP_STATE_CLI, APP_STATE_COMPLETE)
                return self.app_state
            
            else:
                dbg_banner(f' Warning: Unhandled "sm_cli()" state ({self.app_sub_state})!')
                self.app_state = APP_STATE_COMPLETE
        return self.app_state

    ##########################################
    ### 1 - APP_STATE_WIFI_CONNECT
    ##########################################
    def sm_wifi_init(self) -> int:
        """Start Wi-Fi initialization with an AT-RST (reset) """
        if self.app_sub_state == 0:
            banner_txt = f' {APP_STATE_WIFI_CONNECT} - APP_STATE_WIFI_CONNECT'
            if APP_DISPLAY_LEVEL >= APP_DISPLAY_STATES:
                banner(f'{banner_txt}\n'
                       f'     SSID:     \'{WIFI_SSID}\'\n'
                       f'     SECURITY: \'{WIFI_SECURITY}\'\n'
                       , BANNER_BORDER_LEV_1)
                self.log_state(banner_txt)
            self.set_state(APP_STATE_WIFI_CONNECT, 1)
        else:
            if self.app_wait:  # Wait here until last command completes
                pass
            # Reset the chip on every execution (erases previous Wi-Fi, etc settings)
            elif self.app_sub_state == 1:
                if APP_DISPLAY_LEVEL >= APP_DISPLAY_INFO:
                    banner(' Event: Device Reset ')  # Reset chip parameters
                self.cmd_issue('AT+RST', 1, "RNWF - AT Command Interface", 60)
            elif self.app_sub_state == 2:  # Set local echo
                self.cmd_issue('ATE1')
            elif self.app_sub_state == 3:  # Get chip revision
                self.cmd_issue('AT+GMR',
                               self.is_model("RNWF11", 1, 6))
            # Internal Certificate commands only supported by RNFW11
            elif self.app_sub_state == 4:       # Get RNWF11's serial number name for the certs
                self.cmd_issue(f'AT+ECCRDSER')  # RNWF11 requires this command to make the certs
            elif self.app_sub_state == 5:           # Get DEVICE(1) certificate
                self.cmd_issue('AT+ECCRDCERT=1,1500', 1)
            elif self.app_sub_state == 6:           # Get SIGNER(2) certificate status
                self.cmd_issue('AT+ECCRDCERT=2,1500', 2)        # Skip the root cert
            elif self.app_sub_state == 7:           # Get ROOT(3) certificate
                self.cmd_issue('AT+ECCRDCERT=3,1500', 1)        # Skipped

            elif self.app_sub_state == 8:       # RNWF11 set ECC device type to 'TrustNGo' connection status
                self.cmd_issue('AT+ECCWRDEVTYPE=1')

            elif self.app_sub_state == 9:  # Set SSID string
                self.cmd_issue(f'AT+WSTAC=1,"{WIFI_SSID}"')
            elif self.app_sub_state == 10:  # Set WPA(2=Security Type),(Passed in)
                self.cmd_issue(f'AT+WSTAC=2,{WIFI_SECURITY}')
            elif self.app_sub_state == 11:  # Set Wi-Fi passphrase
                self.cmd_issue(f'AT+WSTAC=3,"{WIFI_PASSPHRASE}"')
            elif self.app_sub_state == 12:  # Set Wi-Fi channel to "any"
                self.cmd_issue(f'AT+WSTAC=4,0')
            elif self.app_sub_state == 13:  # Set NTP Client function: Disable(0), Enable(1)
                self.cmd_issue(f'AT+SNTPC=1,1')
            elif self.app_sub_state == 14:  # Set NTP Config Mode: DHCP can set(0), STATIC cannot be set by DHCP(1)
                self.cmd_issue(f'AT+SNTPC=2,1')
            elif self.app_sub_state == 15:  # Set NTP server URL
                self.cmd_issue(f'AT+SNTPC=3,"{NTP_SERVER}"')
            elif self.app_sub_state == 16:  # Set internal TLS handshake certificate
                self.cmd_issue(f'AT+TLSC={TLS_CFG_INDEX},1,"{TLS_CERT_DPS}"',
                               self.is_model("RNWF11", 3, 1))
            elif self.app_sub_state == 17:  # Set Device CERTIFICATE filename
                self.cmd_issue(f'AT+TLSC={TLS_CFG_INDEX},2,"{DEVICE_CERT_FILENAME}"')
            elif self.app_sub_state == 18:  # Set Device KEY filename
                self.cmd_issue(f'AT+TLSC={TLS_CFG_INDEX},3,"{DEVICE_KEY_FILENAME}"', 1)  # Skip next state
            elif self.app_sub_state == 19:  # Set TLS device server
                self.cmd_issue(f'AT+TLSC={TLS_CFG_INDEX},5,"{TLS_DEVICE_SERVER}"',
                               self.is_model("RNWF11", 1, 2))
            elif self.app_sub_state == 20:  # Use RNWF11's ECC Device. RNWF02 skips this command
                self.cmd_issue(f'AT+TLSC={TLS_CFG_INDEX},8,1')
            elif self.app_sub_state == 21:  # Connect to AP  & Wait for NTP server UTC time
                self.cmd_issue(f'AT+WSTA=1', 1, "+TIME:", 60)
            elif self.app_sub_state == 22:
                self.app_sub_state = APP_STATE_COMPLETE
            else:
                dbg_banner(f' Warning: Unhandled "sm_wifi_init()" state ({self.app_sub_state})!')
                self.app_sub_state = APP_STATE_COMPLETE
        return self.app_sub_state
    ##########################################
    ### 2 - APP_STATE_MQTT_SETTINGS
    ##########################################
    def sm_mqtt_settings(self) -> int:
        """Start Azure Device Provisioning Service(DPS """
        if self.app_sub_state == 0:
            banner_txt = f' {APP_STATE_MQTT_SETTINGS} - APP_STATE_MQTT_SETTINGS '
            if APP_DISPLAY_LEVEL >= APP_DISPLAY_STATES:
                banner(f'{banner_txt}', BANNER_BORDER_LEV_1)
                self.log_state(banner_txt)
            self.set_state(APP_STATE_MQTT_SETTINGS, 1)
        else:
            if self.app_wait:  # Wait here until last command completes
                pass
            elif self.app_sub_state == 1:  # Broker URL Azure
                self.cmd_issue(f'AT+MQTTC=1,"{MQTT_BROKER_URL}"')
            elif self.app_sub_state == 2:  # DPS broker port (TLS)
                self.cmd_issue(f'AT+MQTTC=2,{MQTT_BROKER_PORT}')
            elif self.app_sub_state == 3:  # MQTT Client ID
                 self.cmd_issue(f'AT+MQTTC=3,"{MQTT_CLIENT_ID}"')
            elif self.app_sub_state == 4:  # MQTT Username
                self.cmd_issue(f'AT+MQTTC=4,"{ID_SCOPE}/registrations/{MQTT_CLIENT_ID}/api-version={API_VERSION_DPS}"')
            elif self.app_sub_state == 5:  # Set MQTT Keep Alive
                self.cmd_issue(f'AT+MQTTC=6, {MQTT_KEEP_ALIVE}')
            elif self.app_sub_state == 6:  # Set TLS configuration index see "AT+TLSC"
                self.cmd_issue(f'AT+MQTTC=7, {TLS_CFG_INDEX}')
            elif self.app_sub_state == 7:  # Set MQTT version 3 or 5
                self.cmd_issue(f'AT+MQTTC=8, {MQTT_VERSION}', 0)
                self.set_state(2, self.is_model("RNWF11",
                                self.app_sub_state + 1, self.app_sub_state + 8))
                               #self.is_model("RNWF11", 1, 8)) # RNWF02 skips next 6 commands
            elif self.app_sub_state == 8:
                # This check is for a physical RNWF11 device, even if FORCE_DPS is enabled
                if MODEL == "RNWF11":       # RNWF11 Only! Set the 'Subscription read threshold' to prevent JSON failure.
                    self.cmd_issue(f'AT+MQTTC=9, {MQTT_SUBSCRIPTION_READ_THRESHOLD}',
                                                  self.is_model("RNWF11", 1, 7))
                    #self.cmd_issue(f'NOOP', 7)
                else:
                    self.app_sub_state + 7

            #
            # START: RNWF11 Specific commands used to perform Azure DPS internal to the device
            #
            elif self.app_sub_state == 9:  # RNWF11 select Azure Server(1), Other(0)
                self.cmd_issue(f'AT+MQTTC=10, 1', 1)
            elif self.app_sub_state == 10:  # RNWF11 select device template
                self.cmd_issue(f'AT+AZUREC=1, "{DEVICE_TEMPLATE}"', 1)
            elif self.app_sub_state == 11:
                self.cmd_issue('AT+MQTTCONN=1', 1, "+MQTTCONNACK", 60)
            elif self.app_sub_state == 12:
                # RNWF11 ONLY: Send MQTTC=4 to retrieve the internally negotiated Assigned Hub string
                self.cmd_issue(f'AT+MQTTC=4')
            elif self.app_sub_state == 13:
                # FW Bug Fix: Initial fw release doesn't send the 'api-version' with this cmd.
                #
                # The Assigned Hub is retrieved by "rx_data_process()" under "elif "+MQTTC=4 +MQTTC:4""
                # Reconstruct the string with the 'api-version' on the end and resubmit.

                # If the previous 'MQTT=4' command set the 'ASSIGNED_HUB' string, this firmware has the bug
                # and will resubmit the MQTTC=4 command. If the 'ASSIGNED_HUB' is empty, the firmware has the
                # fix and the command is not needed and skipped. See rx_data_process() @ elif "+MQTTC=4 +MQTTC:4"
                if ASSIGNED_HUB:
                    self.cmd_issue(f'AT+MQTTC=4,"{ASSIGNED_HUB}/{MQTT_CLIENT_ID}/?api-version={API_VERSION_DEV_TWIN}"')
                else:
                    self.set_state(self.app_state, self.app_sub_state + 1)
            #
            # END: RNWF11 specific commands
            #
            elif self.app_sub_state == 14:          # Disconnect from MQTT server
                self.cmd_issue('AT+MQTTDISCONN=0', 1, "+MQTTCONN:0")
            elif self.app_sub_state == 15:          # Report MQTT settings
                self.cmd_issue(f'AT+MQTTC')
            elif self.app_sub_state == 16:          # MQTT make the connection
                self.cmd_issue(f'AT+MQTTCONN=1', 1, "+MQTTCONNACK", 60)  # CRITICAL Wait for this response
            elif self.app_sub_state == 17:
                if self.is_model("RNWF11"):          # RNFW11 skips DPS completely
                    self.set_state(APP_STATE_IOTC_CONNECT, 0)
                else:                               # RNFW02 does DPS now
                    self.app_sub_state = APP_STATE_COMPLETE
            else:
                dbg_banner(f' Warning: Unhandled "sm_mqtt_settings()" state ({self.app_sub_state})!')
                self.app_sub_state = APP_STATE_COMPLETE
        return self.app_sub_state

    ##########################################
    ### 3 - APP_STATE_DPS_REGISTER
    ##########################################
    def sm_dps_register(self) -> int:
        """Start Azure Device Provisioning Service(DPS """
        global OPERATION_ID, ASSIGNED_HUB

        if self.app_sub_state == 0:
            if APP_DISPLAY_LEVEL >= APP_DISPLAY_STATES:
                banner_txt = f' {APP_STATE_DPS_REGISTER} - APP_STATE_DPS_REGISTER '
                banner(f'{banner_txt}', BANNER_BORDER_LEV_1)
                self.log_state(banner_txt)
            self.set_state(APP_STATE_DPS_REGISTER, 1)
        else:
            if self.app_wait:  # Wait here until last command completes
                pass
            elif self.app_sub_state == 1:  # MQTT subscription
                 self.mqtt_subscribe(TOPIC_DPS_RESULT, 0, 1, "+MQTTSUB:0")
                 self.rid += 1
            elif self.app_sub_state == 2:  # MQTT registration
                # Send this 'put' command one time...eventually RSP will be "+MQTTSUBRX"
                # banner(' Publish DPS registration message ')
                if OPERATION_ID == '' or ASSIGNED_HUB == '' or FORCE_DPS_REG:
                    # If the above values are populated, the DPS registration has already been done
                    # so we can skip the registration state and save some time. If the "app.cfg"
                    # option 'force_dps_reg' is set, DPS registration always occurs.
                    self.mqtt_publish(0, 0, f'{TOPIC_DPS_INIT_REG}{self.hex_rid()}',
                                      ('{\\\"payload\\\": {\\\"modelId\\\": \\\"' + DEVICE_TEMPLATE + '\\\"}}'),
                                      0,  # State Increment in "evt_dps_topic_notified()"
                                      "+MQTTSUBRX:")
                    self.rid += 1
                else:
                    # Skip DPS and save about 20s of setup time
                    self.set_state(APP_STATE_DPS_REGISTER, self.app_sub_state + 2)
            elif self.app_sub_state == 3:  # Send command every 3s until response is received
                self.delay.start()
                if self.delay.delay_sec_poll(3):
                    # "delay_sec_poll()" returns True if time exceeded
                    self.mqtt_publish(0, 0, (
                        f'{TOPIC_DPS_POLL_REG_COMPLETE1}{self.hex_rid()}{TOPIC_DPS_POLL_REG_COMPLETE2}{OPERATION_ID}'),
                                      "",
                                      0,  # State Increment in "evt_dps_topic_notified()"
                                      "+MQTTSUBRX:")
            elif self.app_sub_state == 4:  #
                self.cmd_issue(f'AT+MQTTC=1,"{ASSIGNED_HUB}"')
            elif self.app_sub_state == 5:
                # CRITICAL COMMAND: API version different from DPS version causes Get Device Twin
                #                   to fail in State 4!
                self.cmd_issue(f'AT+MQTTC=4,"{ASSIGNED_HUB}/{MQTT_CLIENT_ID}/?api-version={API_VERSION_DEV_TWIN}"')
            elif self.app_sub_state == 6:
                self.cmd_issue('AT+MQTTDISCONN=0', 1, "+MQTTCONN:0")
            elif self.app_sub_state == 7:  # Report MQTT settings
                self.cmd_issue(f'AT+MQTTC')
            elif self.app_sub_state == 8:  # MQTT make the connection
                self.cmd_issue(f'AT+MQTTCONN=1', 1, "+MQTTCONNACK", 60)  # CRITICAL Wait for this response
            elif self.app_sub_state == 9:
                self.app_sub_state = APP_STATE_COMPLETE
            else:
                dbg_banner(f' Warning: Unhandled "sm_dps_register()" state ({self.app_sub_state})!')
                self.app_sub_state = APP_STATE_COMPLETE
        return self.app_sub_state

    ##########################################
    ### 4 - APP_STATE_IOTC_CONNECT
    ##########################################
    def sm_iotc_connect(self) -> int:
        """ Configure and connect to iotc MQTT broker"""
        if self.app_sub_state == 0:
            if APP_DISPLAY_LEVEL >= APP_DISPLAY_STATES:
                banner_txt = f' {APP_STATE_IOTC_CONNECT} - APP_STATE_IOTC_CONNECT '
                banner(f'{banner_txt}', BANNER_BORDER_LEV_1)
                self.log_state(banner_txt)
            self.set_state(APP_STATE_IOTC_CONNECT, 1)
        else:
            if self.app_wait:  # Wait here until last command completes
                return self.app_sub_state
            elif self.app_sub_state == 1:
                self.cmd_issue(f'AT+MQTTSUB="{TOPIC_IOTC_METHOD_REQ}",0', 1, "+MQTTSUB:0")
                # self.cmd_issue(f'NOOP')
            elif self.app_sub_state == 2:
                self.cmd_issue(f'AT+MQTTSUB="{TOPIC_IOTC_PROP_DESIRED}",0', 1, "+MQTTSUB:0")
                # self.cmd_issue(f'NOOP')
            elif self.app_sub_state == 3:
                self.cmd_issue(f'AT+MQTTSUB="{TOPIC_IOTC_PROPERTY_RES}",0', 1, "+MQTTSUB:0")
            elif self.app_sub_state == 4:
                self.app_sub_state = APP_STATE_COMPLETE
            else:
                dbg_banner(f' Warning: Unhandled "sm_iotc_connect()" state ({self.app_sub_state})!')
                self.app_sub_state = APP_STATE_COMPLETE
        return self.app_sub_state

    ##########################################
    ### 5 - APP_STATE_IOTC_GET_SET_DEV_TWIN
    ##########################################
    def iotc_get_device_twin_state(self) -> int:
        if self.app_sub_state == 0:
            if APP_DISPLAY_LEVEL >= APP_DISPLAY_STATES:
                banner_txt = f' {APP_STATE_IOTC_GET_SET_DEV_TWIN} - APP_STATE_IOTC_GET_SET_DEV_TWIN '
                banner(f'{banner_txt}', BANNER_BORDER_LEV_1)
                self.log_state(banner_txt)
            self.set_state(APP_STATE_IOTC_GET_SET_DEV_TWIN, 1)
        else:
            if self.app_wait:  # Wait here until last command completes
                return self.app_sub_state
            elif self.app_sub_state == 1:
                print("Read current device twin settings from IOTC")
                #self.rid += 1
                self.mqtt_publish(0, 0,
                                  f'{TOPIC_IOTC_PROPERTY_REQUEST}', "", 1, "+MQTTSUBRX:")
            elif self.app_sub_state == 2:
                self.rid += 1
                #print("Report Read-Only Property: IP Address = " + self.ip_addr_ipv4)
                self.iotc_str_property_send("ipAddress", self.ip_addr_ipv4, 1, "MQTTPUB")
                self.demo_display("ipAddress", DEVICE_2_CLOUD)
            elif self.app_sub_state == 3:
                #print("Report Writable Property: LED State")
                print(f'Synchronizing LED0, reportRate, press_count, and counter values with the Azure...')
                self.iotc_led0 = 1                      # Range is 1-3
                self.iotc_int_property_send("LED0", str(self.iotc_led0), 1)
                self.demo_display("LED0", DEVICE_2_CLOUD)
            elif self.app_sub_state == 4:
                #print("Report Writable Property: Telemetry Reporting Rate")
                self.telemetry_interval = self.telemetry_ints[self.telemetry_index]
                self.iotc_int_property_send("reportRate", self.telemetry_interval, 1)
                self.demo_display("reportRate", DEVICE_2_CLOUD)
            elif self.app_sub_state == 5:
                self.iotc_button_press_count = 0
                # JSON Payload eg: "{\"buttonEvent\": {\"button_name\": \"SW0\",\"press_count\": 3}}"
                payload = ('{\\\"buttonEvent\\\": {\\\"button_name\\\": \\\"SW0\\\",\\\"press_count\\\": ' +
                           str(self.iotc_button_press_count) + '}}')
                self.iotc_json_telemetry_send(payload, 1)
                self.demo_display('buttonEvent', DEVICE_2_CLOUD)
            elif self.app_sub_state == 6:
                self.iotc_counter = 0
                self.iotc_int_telemetry_send("counter",
                                         self.iotc_counter, 1, "counter")
                self.demo_display('counter', DEVICE_2_CLOUD)
            elif self.app_sub_state == 7:
                self.app_sub_state = APP_STATE_COMPLETE
                self.demo_display()
            else:
                dbg_banner(f' Warning: Unhandled "iotc_get_device_twin_state()" state ({self.app_sub_state})!')
                self.app_sub_state = APP_STATE_COMPLETE
        return self.app_sub_state

    ##########################################
    ### 6 - APP_STATE_IOTC_DEMO
    ##########################################
    # IOTC Demo variables

    # Class Variables                Type      Name            Direction
    # ---------------                ----      ----            ---------
    # self.iotc_counter = 0          Telemetry "counter"       # D2C
    # self.iotc_button_event = 0     Telemetry "buttonEvent"   # D2C
    # self.ipaddr = 0                Property  "ipAddress"     # D2C (RO in cloud)
    # self.iotc_led0 = 0             Property  "LED0"          # D2C | C2D
    # self.telemetry_interval = 0    Property  "reportRate"    # D2C | C2D
    # self.reboot_timer = 0          Command   "reboot"        # C2D
    # self.iotc_echo = ''            Command   "echo"          # C2D
    def sm_iotc_demo_app(self) -> int:
        banner_txt = f' {APP_STATE_IOTC_DEMO} - APP_STATE_IOTC_DEMO '

        if self.app_sub_state == 0:
            if APP_DISPLAY_LEVEL >= APP_DISPLAY_STATES:
                banner(f'{banner_txt}', BANNER_BORDER_LEV_1)
            # If the demo banner/help is not display it appears hung...so always display
            banner(help_str_6, BANNER_BORDER_LEV_1)
            self.log_state(banner_txt)
            self.set_state(APP_STATE_IOTC_DEMO, 1)
        else:
            if self.app_wait:  # Wait here until last command completes
                return self.app_sub_state
            #
            # First 3 states preset the Azure's copy of: Device IP Address, LED value and Telemetry report rate
            #
            elif self.app_sub_state == 1:
                self.set_state(APP_STATE_IOTC_DEMO, APP_SUB_STATE_DEMO_LOOP)
                #
                # SubState 1:  Main state handler all user input keys 'B', 'C', etc
                #
            elif self.app_sub_state == APP_SUB_STATE_DEMO_LOOP:
                # Display state 6 help screen
                if self.kb.key_cmd == HELP_KEY:
                    banner(help_str_6, BANNER_BORDER_LEV_2)
                #
                # Sends TELEMETRY 'buttonEvent' [0|1] ==> Azure. Increments the button state.push_count on each execution
                #       CMD: AT+MQTTPUB=0,0,0,"devices/RNWF02-Dev99/messages/events/","{\"buttonEvent\":
                #            {\"button_name\": \"SW0\",\"press_count\": 1}}"
                #       RSP: AT+MQTTPUB=0,0,0,"devices/RNWF02-Dev99/messages/events/","{\"buttonEvent\":
                #            {\"button_name\": \"SW0\",\"press_count\": 1}}" [OK]

                # Azure: Does accept telemetry updates but does not acknowledge the update back
                elif self.kb.key_cmd == BUTTON_KEY:
                    self.iotc_button_press_count += 1
                    # JSON Payload eg: "{\"buttonEvent\": {\"button_name\": \"SW0\",\"press_count\": 3}}"
                    payload = ('{\\\"buttonEvent\\\": {\\\"button_name\\\": \\\"SW0\\\",\\\"press_count\\\": ' +
                               str(self.iotc_button_press_count) + '}}')
                    self.iotc_json_telemetry_send(payload , 1)
                    self.demo_display('buttonEvent', DEVICE_2_CLOUD)
                #
                # Sends TELEMETRY 'counter' [0-n] ==> Azure. Counter incremented and sent to Azure
                #       CMD: AT+MQTTPUB=0,0,0,"devices/COMMON_NAME/messages/events/","{\"counter\" : 0}
                #       RSP: AT+MQTTPUB=0,0,0,"devices/COMMON_NAME/messages/events/","{\"counter\" : 0}" [OK]
                elif self.kb.key_cmd == COUNTER_KEY:
                    if self.iotc_counter == '':
                        self.iotc_counter = 0
                    else:
                        self.iotc_counter += 1
                    self.iotc_int_telemetry_send("counter",
                                                 self.iotc_counter, 1, "counter")
                    self.demo_display('counter', DEVICE_2_CLOUD)
                #
                # Sends PROPERTY 'reportRate' [0|2|5|10]s ==> Azure. After 10s returns to 0s.
                # When 'reportRate' > 0, will increments & send TELEMETRY 'counter' to Azure every
                # 'reportRate' seconds for 10 cycles.
                #       CMD: AT+MQTTPUB=0,0,0,"$iothub/twin/PATCH/properties/reported/?rid=2","{\"reportRate\" : R}"
                #       CMD: AT+MQTTPUB=0,0,0,""devices/COMMON_NAME/messages/events/","{\"counter\" : CC}
                #       RSP: AT+MQTTPUB=0,0,0,""devices/COMMON_NAME/messages/events/","{\"counter\" : CC}" [OK]
                elif self.kb.key_cmd == REPORT_RATE_KEY:
                    self.telemetry_index += 1
                    # Roll the index back to zero for a circular interval list
                    if self.telemetry_index > (len(self.telemetry_ints) - 1):
                        self.telemetry_index = 0

                    self.telemetry_interval = self.telemetry_ints[self.telemetry_index]
                    if self.telemetry_interval:
                        self.demo_loops = DEMO_LOOP_COUNT
                        self.delay.stop()
                        start_val = self.delay.start()
                    else:
                        self.demo_loops = 0
                        self.delay.stop()

                    self.iotc_int_property_send("reportRate",
                                                self.telemetry_ints[self.telemetry_index], 1)
                    self.demo_display('reportRate', DEVICE_2_CLOUD)
                #
                # Sends PROPERTY 'LED0' [1|2|3] ==> Azure 1 time. On each command sends the 'LED0' value
                #       Enumerated values as defined by device template: ".\tools\DeviceTemplates\avr128db48_cnano-1.json"
                #         LED0 == 1 (ON)
                #         LED0 == 2 (OFF)
                #         LED0 == 3 (BLINKING)
                #       CMD: AT+MQTTPUB=0,0,0,"$iothub/twin/PATCH/properties/reported/?rid=1","{\"LED0\" : N}"
                #       RSP: AT+MQTTPUB=0,0,0,"$iothub/twin/PATCH/properties/reported/?rid=1","{\"LED0\" : N}" [OK]
                elif self.kb.key_cmd == LED0_KEY:
                    # Roll LED0 back to 1 for circular LED0 states; Range [1 -3]
                    if self.iotc_led0 == '':
                        self.iotc_led0 = 0
                    self.iotc_led0 += 1
                    if self.iotc_led0 > 3:
                        self.iotc_led0 = 1

                    # Update Azure with the new LED0 property
                    self.iotc_int_property_send("LED0", self.iotc_led0, 1, "LED0")
                    self.demo_display("LED0", DEVICE_2_CLOUD)
                #
                # RESUME Command
                #   Broker DISCONNECTED: Attempt broker reconnection by jumping to STATE 3 & skip DPS
                #   Wi-Fi  DISCONNECTED: Restart the demo from the beginning
                elif self.kb.key_cmd == RESUME_KEY:
                    # Restart DEMO mode
                    if not self.wifi_connected:
                        banner(f'Attempting to reconnect to the Internet...')
                        self.set_state(APP_STATE_WIFI_CONNECT, 0)
                    elif not self.broker_connected:
                        banner(f'Attempting to reconnect to the cloud...')
                        self.set_state(APP_STATE_DPS_REGISTER, 8)
                    else:
                        banner(f'Cannot "resume" while Azure is still connected.')

                else:   # Back to top of the Demo Loop
                    self.set_state(APP_STATE_IOTC_DEMO, APP_SUB_STATE_DEMO_LOOP)

                # Clear the fs_command
                self.kb.cmd = ''
                self.kb.key_cmd = ''

            elif self.app_sub_state == 3:       # If Demo state 2 is complete, loop back in and continue
                self.app_sub_state = APP_SUB_STATE_DEMO_LOOP

            #
            # Send ack messages back to Azure with a MQTTPublish
            #

            # This sub-state is set in 'evt_iotc_command()' after receiving a NON-ZERO time 'reboot' or 'message'
            # command from the cloud. We must acknowledge it. For either a 'Success' status is returned.
            # Without it the cloud will display an error.
            elif self.app_sub_state == APP_SUB_STATE_DEMO_SUCCESS_RSP:
                self.cmd_check(True)    # Kill any outstanding commands
                self.mqtt_publish(0, 0, f'{TOPIC_IOTC_CMD_RESP}{self.hex_rid()}',
                                  '{\\\"status\\\" : \\\"Success\\\"}', 99, "OK")

            # This sub-state is set in 'evt_iotc_command()' after receiving a ZER0 time 'reboot' command from the
            # cloud.  We must acknowledge it. For a reboot cancellation we acknowledge it with a 'Failure' status by
            # choice!  Without it the cloud will display an error. Failure is just an indication the reboot time
            # has been cancelled and is for demonstration purposes only...its not really a failure.
            elif self.app_sub_state == APP_SUB_STATE_DEMO_FAILURE_RSP:
                self.cmd_check(True)  # Kill any outstanding commands
                self.mqtt_publish(0, 0, f'{TOPIC_IOTC_CMD_RESP}{self.hex_rid()}',
                                  '{\\\"status\\\" : \\\"Failure\\\"}', 99, "OK")

            # This 'else' will catch any 'next_step = 99' to loop back to the top of the Demo loop
            else:
                self.set_state(APP_STATE_IOTC_DEMO, APP_SUB_STATE_DEMO_LOOP)

            # Update interval if it's running or should be. Azure could have sent us a 'reportRate'
            # property change. If so that was handled by evt_iotc_property_received()
            if self.demo_loops:
                self.delay.start()
                if self.delay.delay_sec_poll(self.telemetry_interval):
                    if self.iotc_counter == '':
                        self.iotc_counter = 0
                    else:
                        self.iotc_counter += 1
                    # Update Azure with a incremented 'counter'
                    self.iotc_int_telemetry_send("counter", self.iotc_counter, 99, "")
                    self.demo_display('counter', DEVICE_2_CLOUD)

                    self.demo_loops -= 1
                    self.delay.stop()
                    self.delay.start()
            else:
                pass
        return self.app_sub_state

    def demo_display(self,
                     dict_key: str = None,
                     direction: bool = NONE_2_NONE) -> None:
        """ Called to display or setup the response info
            eg: demo_display()                          # Show display & clear 'dict_key'
                demo_display('counter',DEVICE_2_CLOUD)  # counter updated to cloud

            dict_keys: {counter, buttonEvent, ipAddress, LED0, reportRate, reboot, echoString}
            direction: DEVICE_2_CLOUD==True, CLOUD_2_DEVICE==False, NONE_2_NONE==None
        """
        if dict_key != None or APP_DISPLAY_LEVEL < APP_DISPLAY_DEMO:
            self.resp_dict[dict_key] = direction
            return
        # Horiz spacing for header text
        # Counter, BtnEvt, ipAddr, Led0, RepRate, Reboot, Echo
        spc = [6, 7, 17, 6, 8, 8, 20]
        resp = ''

        data_dict = {"counter": self.iotc_counter, "buttonEvent": self.iotc_button_event,
                     "ipAddress": self.ip_addr_ipv4, "LED0": self.iotc_led0,
                     "reportRate": self.telemetry_interval, "reboot": self.reboot_timer,
                     "echoString": self.iotc_echo}

        # Truncate the message if too long
        echo_len_str = f'({len(self.iotc_echo)})'
        if len(self.iotc_echo) > spc[6]:
            # Trim the message to field size - 2 (for the single quotes)
            self.iotc_echo = f'\'{self.iotc_echo[0:spc[6]]}...\''
        else:
            self.iotc_echo = f'\'{self.iotc_echo}\''

        hdr = f'{"Count" : ^{spc[0]}}' \
              f'{"BtnEvt" : ^{spc[1]}}' \
              f'{"ipAddress" : ^{spc[2]}}' \
              f'{"LED0" : ^{spc[3]}}' \
              f'{"RepRate" : ^{spc[4]}}' \
              f'{"Reboot" : ^{spc[5]}}' \
              f'{"Echo" : <{spc[6] + 4 - len(echo_len_str)}} ' \
              f'{echo_len_str}'

        # When incrementing counter by an interval timer change the
        # 'repRate' to include the loop count down.
        if self.demo_loops:
            tele_str = f'{str(self.telemetry_interval)}s ({self.demo_loops})'
        else:
            tele_str = f'{str(self.telemetry_interval)}'

        dat = f'{str(self.iotc_counter) : ^{spc[0]}}' \
              f'{str(self.iotc_button_press_count) : ^{spc[1]}}' \
              f'{str(self.ip_addr_ipv4) : ^{spc[2]}}' \
              f'{str(self.iotc_led0) : ^{spc[3]}}' \
              f'{tele_str: ^{spc[4]}}' \
              f'{str(self.iotc_reboot_delay) : ^{spc[5]}}' \
              f'{self.iotc_echo : <{spc[6]}}'

        if len(self.resp_dict):
            # Create the data direction line output
            for index, key in enumerate(data_dict.keys()):
                try:
                    data_dir = self.resp_dict[key]
                except KeyError:
                    resp += f'{"---" : ^{spc[index]}}'
                    continue
                if data_dir == DEVICE_2_CLOUD:
                    resp += f'{"D>C" : ^{spc[index]}}'
                elif data_dir == CLOUD_2_DEVICE:
                    resp += f'{"C>D" : ^{spc[index]}}'
        else:
            resp = ''

        banner(f'{hdr}\n{dat}\n{resp}\n', BANNER_BORDER_LEV_2)

        self.resp_dict.clear()
        self.iotc_echo = ''


    def iotc_json_telemetry_send(self,
                                payload: str,
                                next_step: int = 1,
                                alt_resp: str = "") -> None:
        #print(f'Sending JSON TELEMETRY \'{payload}\'')
        # The JSON payload is passed by the caller when the string is too complicated to assemble here
        self.mqtt_publish(0, 0, TOPIC_IOTC_TELEMETRY, payload, next_step, alt_resp)

    def iotc_int_telemetry_send(self,
                                parameter: str,
                                ival: int,
                                next_step: int = 1,
                                alt_resp: str = "") -> None:
        # print(f'Sending TELEMETRY \'{parameter}\' integer value of: {str(ival)}')
        payload = '{\\\"' + parameter + '\\\" : ' + str(ival) + '}'
        self.mqtt_publish(0, 0, TOPIC_IOTC_TELEMETRY, payload, next_step, alt_resp)

    def iotc_str_telemetry_send(self,
                                parameter: str,
                                sval: str,
                                next_step: int = 1, alt_resp="") -> None:
        # print(f'Sending TELEMETRY \'{parameter}\' string value of: {sval}')
        payload = '{\\\"' + parameter + '\\\" : \\\"' + sval + '\\\"}'
        self.mqtt_publish(0, 0, TOPIC_IOTC_TELEMETRY, payload, next_step, alt_resp)

    def iotc_double_telemetry_send(self,
                                   parameter: str,
                                   dval: float,
                                   next_step: int = 1,
                                   alt_resp: str = "") -> None:
        # print(f'Sending TELEMETRY \'{parameter}\' double value of: {str(dval)}')
        payload = '{\\\"' + parameter + '\\\" : ' + str(dval) + '}'
        self.mqtt_publish(0, 0, TOPIC_IOTC_TELEMETRY, payload, next_step, alt_resp)

    def iotc_int_property_send(self,
                               parameter: str,
                               ival: int,
                               next_step: int = 1,
                               alt_resp: str = "") -> None:
        # print(f'Sending PROPERTY \'{parameter}\' integer value of: {str(ival)}')
        self.rid += 1
        self.mqtt_publish(0, 0, TOPIC_IOTC_WRITE_PROPERTY + self.hex_rid(),
                          '{\\\"' + parameter + '\\\" : ' + str(ival) + '}',
                          next_step, alt_resp)

    def iotc_str_property_send(self,
                               parameter: str,
                               sval: str,
                               next_step: int = 1,
                               alt_resp: str = "") -> None:
        # print(f'Sending PROPERTY \'{parameter}\' string value of: {sval}')
        self.rid += 1
        self.mqtt_publish(0, 0, TOPIC_IOTC_WRITE_PROPERTY + self.hex_rid(),
                          '{\\\"' + parameter + '\\\" : \\\"' + sval + '\\\"}',
                          next_step, alt_resp)

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

        if self.app_state >= APP_STATE_IOTC_DEMO:   # Don't fault in Demo state
            return False

        self.cmd_log(f'          : {rsp} ({cmd_time:.2f}s)\n')

        cmd_fail = self.at_command

        if rsp.find('[ER]:NTP') != -1:
            # Actually failed @ 01:12 but due to cfg issue @ 01:09
            cmd_fail=  f'AT+SNTPC=3,"{NTP_SERVER}"'
            iss = f'Wi-Fi NTP ({NTP_SERVER}) configuration'
            sol = f'- Verify Network Time Server is online'
            tip = f'- Specify a valid NTP server in \'{APP_CONFIG_FILE}\' '
        elif rsp.find('STA Connection Failed') != -1:
            iss = f'Wi-Fi ({WIFI_SSID}) configuration'
            sol = f'- Verify router power, BSID, passphrase and security settings'
            tip = f'- Use the CLI \'scan\' tool'
        elif err_sig.find('01:17') != -1:
            iss = f'TLS DEVICE Certificate '
            sol = f'- Load device certificate (\'{DEVICE_CERT_FILENAME}\') and verify \'device_cert_filename\' in \'{APP_CONFIG_FILE}\''
            tip = f'- Use CLI command \'dir c\' to view installed certificates'
        elif err_sig.find('01:18') != -1:
            iss = f'TLS KEY Certificate '
            sol = f'- Load KEY certificate (\'{DEVICE_KEY_FILENAME}\') and verify \'device_key_filename\' in \'{APP_CONFIG_FILE}\''
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
        self.at_command = ""
        self.evt_handler = ""
        self.ser_buf = ""
        return True

    def substr_swap(self, str_msg: str, dic: dict) -> str:
        for char in dic.keys():
            str_msg = str_msg.replace(char, dic[char])
        return str_msg

    ##################################
    ### Receive Process Data
    ##################################
    def rx_data_process(self, received: str) -> None:
        """ Single command Queue depth Rx data handler """
        rsp = received
        self.evt_handler = ""

        # Modify received data for a cleaner response string output
        rsp = self.substr_swap(rsp, {">": "", "OK": "[OK]", "ERROR": "[ER]", "\r": "", "\n": " "})
        rsp = rsp.rstrip()

        cmd_time = time.time() - self.at_command_timer.time_start

        if self.err_handler(cmd_time, rsp):
            self.set_state(APP_STATE_CLI)
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
        #
        if self.at_command_resp != "" and self.at_command_resp in rsp: # and self.at_command:
            # Solicited Response line display i.e. commands that have COMPLETED.
            # print(f'RSP[{self.app_state:0>2}.{self.app_sub_state:0>2}]: {rsp} ({cmd_time:.2f}s)\n', flush=True, end='')
            self.cmd_log(f'RSP[{self.app_state:0>2}.{self.app_sub_state:0>2}]: {rsp} ({cmd_time:.2f}s)')
            self.at_command_timer.stop()
            self.at_command_prev = self.at_command
            self.at_command = ""
            self.at_command_resp = ""
            self.app_wait = False
            self.at_quiet_command = False

            # Increment to the next sub-state
            if APP_STATE_CLI <= self.app_state <= APP_STATE_IOTC_DEMO:
                # Increment the sub-state which is only effective if the offset is NOT 0
                # If it is '0', then an evt handler will update the sub state instead
                self.app_sub_state += int(self.next_sub_state_offset)

            # Turn on the Demo Display once we start sending & receiving Azure data in states 5 & 6
            if self.app_state >= APP_STATE_IOTC_DEMO:
                self.demo_display()
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
            if "AT+FS" in rsp:  # Cert & Key dir command response
                self.evt_handler = self.evt_fs_data_result(received)

            if "WSCNIND" in rsp:  # Wi-Fi scan command response
                self.evt_handler = self.evt_wifi_scan_result(received)
        #
        # Additional response handling calls, completed or not
        #
        if ("ATE1" in received) and ("ERROR:" in received):
            self.evt_handler = self.evt_init_error

        elif "GMR" in received:                 # Firmware device info received
            self.evt_handler = self.evt_gmr_data_result(received)

        elif ("AT+WSTAC" in received) and ("ERROR:" in received):
            self.evt_handler = self.evt_init_error

        elif "+WSTA:1" in received:             # Wi-Fi connected
            banner(' Wi-Fi CONNECTED ')
            self.wifi_connected = True
            self.evt_handler = self.evt_wifi_connected

        elif "+WSTA=0" in received:             # Wi-Fi not connected
            self.wifi_connected = False
            self.evt_handler = self.evt_wifi_connected

        elif "+WSTA:0" in received:             # Wi-Fi not connected
            self.wifi_connected = False
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
            self.evt_handler = self.evt_wifi_connected

        elif "+MQTTC +MQTTC:1," in rsp:
            if APP_DISPLAY_LEVEL >= APP_DISPLAY_DECODES:
                mqttc_str = rsp.replace(",", " - ")
                mqttc_list = mqttc_str.split(" +", )
                for i in range(1, len(mqttc_list)):
                    print(f'            +{mqttc_list[i]}')

        elif "+MQTTC=4 +MQTTC:4" in rsp:  # and self.is_model("RNWF11"):
            # Only reassign the Hub if the api-version is NOT present AND Hub is blank
            if globals()["ASSIGNED_HUB"] == '' and not (rsp.__contains__("api-version=")):
                # Parse the HUB ID from the string stored in the RNWF11 device...
                # rsp: 'AT+MQTTC=4 +MQTTC:4,"iotc-62ad...c1e134.azure-devices.net/sn01232943D301723001" OK>'
                try:
                    if rsp.__contains__('azure-devices.net'):
                        # Split the rsp at the quotes, then split 2nd element from end @ the '/'
                        globals()["ASSIGNED_HUB"] = rsp.split('"')[-2].split('/')[0]
                except:
                    banner(f' Error: Assigned Hub not reported by the RNWF11 device.\n\n'
                           f'  DPS registration failed! In \'{APP_CONFIG_FILE}\'...\n'
                           f'  * Verify \'id_scope\' value is correct\n'
                           f'  * Delete values for \'operation_id\' or \'assigned_hub\'\n')

                    exit(1)
        elif "AT+MQTTCONN" == self.at_command_prev:
            if APP_DISPLAY_LEVEL >= APP_DISPLAY_INFO:
                banner(f' Event: Broker Not Connected - Query Current Connection Status')

        elif "AT+MQTTDISCONN=0" == self.at_command_prev:
            self.broker_connected = False
            if APP_DISPLAY_LEVEL >= APP_DISPLAY_INFO:
                print('\n', flush=True)
                banner(f' Event: Broker DISCONNECTED - By Command\n')

        elif "+MQTTCONN:0" in received:
            self.broker_connected = False
            # Change the time out since the connection failed...
            # no point in waiting now.
            self.at_command_timeout = 0  # AT_COMMAND_TIMEOUT
            print(f'\n')
            if self.app_state == APP_STATE_IOTC_CONNECT:
                banner(f' Error: Broker DISCONNECTED - By Timeout or Error\n\n'
                       f'  DPS registration failed! In \'{APP_CONFIG_FILE}\'...\n'
                       f'  * Force registration with \'force_dps_reg = 1\' OR \n'
                       f'  * Delete values for \'operation_id\' or \'assigned_hub\'\n')
            else:
                banner(f' Event: Broker DISCONNECTED - By Timeout or Error')
        elif "+MQTTCONN:1" in received:
            self.broker_connected = True
            if self.app_state == APP_STATE_DPS_REGISTER:
                if APP_DISPLAY_LEVEL >= APP_DISPLAY_INFO:
                    banner(f' Event: Broker CONNECTED for DPS \n  Broker: "{MQTT_BROKER_URL}"\n  Topic:  "{MQTT_CLIENT_ID}"\n')
            if self.app_state == APP_STATE_IOTC_CONNECT:
                if APP_DISPLAY_LEVEL >= APP_DISPLAY_INFO:
                    banner(' Event: Broker Connected for IOTC')
        elif "+MQTTSUBLST:" in received:
            if APP_DISPLAY_LEVEL >= APP_DISPLAY_DECODES:
                # mqttc_str = rsp.replace(",", " - ")

                mqttc_str = self.substr_swap(rsp, {",0 [OK]": "", "AT+MQTTSUBLST": "", "0 +MQTTSUBLST:": "",
                                                       "+MQTTSUBLST:": "", ",0\r\nOK\r\n": ""})
                # , "+MQTTSUBLST": ","})
                mqttc_list = mqttc_str.split(",")
                # print(f' MQTT Subscriptions\n ------------------')
                # for i in range(0, len(mqttc_list)):
                #     print(f' {i+1}: {mqttc_list[i].lstrip()}')

                mqttc_str = f' MQTT Subscriptions:\n───────────────────\n'
                for i in range(0, len(mqttc_list)):
                    mqttc_str += f' {i+1}: {mqttc_list[i].lstrip()}\n'
                banner(mqttc_str)

        elif "+MQTTSUBRX:" in received:
            # print("SRx: " + rsp, flush=True)
            if TOPIC_DPS_RESULT[:(len(TOPIC_DPS_RESULT) - 2)] in received:
                #    "$dps/registrations/res/#"
                if self.sub_payload == "":
                    self.sub_payload = received
                    self.evt_handler = self.evt_dps_topic_notified
            if TOPIC_IOTC_METHOD_REQ[:(len(TOPIC_IOTC_METHOD_REQ) - 2)] in received:
                #   "$iothub/methods/POST/#"
                if self.sub_payload == "":
                    self.sub_payload = received
                    self.evt_handler = self.evt_iotc_command
            if TOPIC_IOTC_PROP_DESIRED[:(len(TOPIC_IOTC_PROP_DESIRED) - 2)] in received:
                #   "$iothub/twin/PATCH/properties/desired/#"
                #   We get here from Demo State 6, when Azure sends us a property, eg LED0 or repRate
                if self.sub_payload == "":
                    self.sub_payload = received
                    self.evt_handler = self.evt_iotc_property_received
            if TOPIC_IOTC_PROPERTY_RES[:(len(TOPIC_IOTC_PROPERTY_RES) - 2)] in received:
                #   "$iothub/twin/res/#"
                # Response when the buffer is too small or 0
                # rsp == '+MQTTSUBRX:0,0,0,"$iothub/twin/res/200/?$rid=getTwin",0,106'
                # Response when buffer is sized at 700
                # rsp == '+MQTTSUBRX: 0, 0, 0, "$iothub/twin/res/200/?$rid=getTwin", "{\"desired\":{\"$version\":1},\"reported\":{\"ipAddress\":\"172.31.99.139\",\"LED0\":1,\"reportRate\":0,\"$version\":164}}"

                if self.sub_payload == "":
                    self.sub_payload = received
                    self.evt_handler = self.evt_iotc_property_download
        elif "+ECCRDSER:" in received and self.is_model("RNWF11"):
            start = received.find('"') + 1      # eg: '+ECCRDSER:18,"01232943D301723001"'
            end = start + received[(start + 1):].find('"') + 1
            #MQTT_CLIENT_ID
            iotp.params["mqtt_client_id"] = f'sn{received[start:end]}'
            iotp.params["device_cert_filename"] = iotp.params["mqtt_client_id"]
            iotp.params["device_key_filename"] = iotp.params["mqtt_client_id"]
            iotp.write()

            globals()["MQTT_CLIENT_ID"] = iotp.params["mqtt_client_id"]
        elif "+ECCRDCERT:" in received and self.is_model("RNWF11"):
            if "AT+ECCRDCERT=" in rsp and "OK" in rsp:
                self.evt_handler = self.evt_cert_received(rsp)
        elif self.evt_handler == "":
            pass
        if rsp != "":
            print("")

    def handle_file_system_command(self, cli_list: list) -> None:
        """ Issues file system/Internal (FS) commands
        """
        if len(cli_list):
            cli_list.append(" ")  # Append at least 1 param for sub_cmd checks
            cmd = cli_list[0].upper()
            sub_cmd = cli_list[1].upper()
            # print(f'handle_file_system_command \'{cmd}\'')
            if cmd == "DIR" and sub_cmd.startswith("K"):
                self.cmd_issue("AT+FS=2,2", 0)
            elif cmd == "DIR" and sub_cmd.startswith("C"):
                self.cmd_issue("AT+FS=2,1", 0)
            elif cmd == "DEL" and sub_cmd.startswith("K") and len(cli_list) == 4:
                fn = str(cli_list[2]).replace('\'', '').replace('\"', '')
                self.cmd_issue(f'AT+FS=3,2,"{fn}"')
            elif cmd == "DEL" and sub_cmd.startswith("C") and len(cli_list) == 4:
                fn = str(cli_list[2]).replace('\'', '').replace('\"', '')
                self.cmd_issue(f'AT+FS=3,1,"{fn}"')
            elif cmd == "SYS":
                self.cmd_issue("AT+FS=4", 0)
            elif cmd == "SCAN":
                self.cmd_issue("AT+WSCN=0", 0, "+WSCNIND:")
            else:
                print(f'FS Unknown Command: {cli_list} {cmd} {len(cli_list)}')
        else:
            print(f'FS Unknown Command: {cli_list}')

    def keyboard_listen(self) -> None:
        """ Wait for keyboard events """

        # Don't poll keyboard during initial RESET
        if self.app_state == APP_STATE_WIFI_CONNECT and self.app_sub_state == 1:
            return
        else:
            ret_bool = self.kb.poll_keyboard()

        if ret_bool == False:           # ESC pressed
            if LOCAL_ECHO:
                # Second ESC press to exit application
                if self.app_state == APP_STATE_CLI:
                    sleep(0.1)
                    if self.broker_connected:
                        self.cmd_log(f'\nDisconnecting Broker...\n')
                        self.cmd_issue_quiet('AT+MQTTDISCONN=0', 0, "+MQTTCONN:0")
                        sleep(0.5)

                    if self.log_file_handle:
                        try:    # Write the config file to the log
                            cfg = open(f'{APP_CONFIG_FILE}', "r")
                            self.log_file_handle.write('\n')
                            self.log_state(f'Configuration Settings')
                            for item in cfg:
                                self.log_file_handle.write(item)
                            self.log_file_handle.write('\n\n')
                            cfg.close()
                        except:
                            pass
                    self.cmd_log(f'Exit Application\n')
                    print(f'\n')
                    print('\n')
                    exit(0)
                else:
                    # First ESC press to APP_STATE_CLI
                    self.cmd_check(True)
                    self.cmd_log(f'Exit To CLI...\n')
                    print('\n')
                    self.set_state(APP_STATE_CLI, 0)
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
                        self.mqtt_publish(0, 0, self.pub_topic, self.pub_payload)
                elif len(self.kb.cmd):
                    self.kb.cmd = self.kb.cmd.upper()

                    cli = kb_received.strip()
                    cli = cli.split(" ", 3)
                    # Only capitalize the CMD...not the filename
                    # cli[0] = cli[0].upper()
                    if cli[0].upper() == "DIR" and len(cli) == 2:
                        self.handle_file_system_command(cli)
                    elif cli[0].upper() == "DEL" and len(cli) == 3:
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
        self.keyboard_listen()                          # read keyboard, scan for exit (ESC) or AT commands
        self.cmd_check(False)                           # Checks for command timeout

        # Check for Azure commanded reboot
        if self.reboot_timer.isStarted and self.reboot_timer.delay_sec_poll(self.iotc_reboot_delay):
            self.set_state(APP_STATE_WIFI_CONNECT, 0)
            banner(f'Azure commanded \'reboot\' initiated!')

        if self.app_state == APP_STATE_CLI:
            resp = self.sm_cli()                        # Call CLI statemachine
            if resp == APP_STATE_COMPLETE:
                print("\nExit Application\n", flush=True)
                exit(0)

        if self.app_state == APP_STATE_WIFI_CONNECT:  # Start Wi-Fi statemachine
            resp = self.sm_wifi_init()
            if resp == APP_STATE_COMPLETE:
                self.set_state(APP_STATE_MQTT_SETTINGS)

        elif self.app_state == APP_STATE_MQTT_SETTINGS:  # Set MQTT settings
            resp = self.sm_mqtt_settings()
            if resp == APP_STATE_COMPLETE:
                self.set_state(APP_STATE_DPS_REGISTER)

        elif self.app_state == APP_STATE_DPS_REGISTER:  # Subscribe to dps topics
            resp = self.sm_dps_register()
            if resp == APP_STATE_COMPLETE:
                self.set_state(APP_STATE_IOTC_CONNECT)

        elif self.app_state == APP_STATE_IOTC_CONNECT:  # Connect to Azure IOTC
            resp = self.sm_iotc_connect()
            if resp == APP_STATE_COMPLETE:
                self.set_state(APP_STATE_IOTC_GET_SET_DEV_TWIN)

        elif self.app_state == APP_STATE_IOTC_GET_SET_DEV_TWIN: # Get Azure device twin
            resp = self.iotc_get_device_twin_state()
            if resp == APP_STATE_COMPLETE:
                self.set_state(APP_STATE_IOTC_DEMO)

        elif self.app_state == APP_STATE_IOTC_DEMO:         # Loop on Azure telemetry
            resp = self.sm_iotc_demo_app()
            if resp == APP_STATE_COMPLETE:
               self.set_state(APP_STATE_IOTC_DEMO)
        else:
            pass  #

        rx_data = self.serial_receive()
        if rx_data != "":
            # Process the received data and format for the display
            self.rx_data_process(rx_data)

            # If an event handler was set for a response call it
            if self.evt_handler:
                self.evt_handler()
                self.evt_handler = ""

    def __del__(self) -> None:
        """ Mainline 'destructor' """
        try:
            self.ser.close()
        except:
            print("  Serial port closure FAILED")
        else:
            print(f'  Serial port \'{self.ser.name}\' closed successfully')
        try:
            if self.log_file_handle:
                self.log_file_handle.close()
                print(f'  Log File closed successfully')
        except:
            print(f'  Log File closure FAILED')
########################################
# App Startup
########################################
os.system('cls')  # Clear terminal screen

# Auto detect com port
MODEL, COM_PORT = find_com_port()
if MODEL == "":
    # Show failed startup banner
    banner(f' IoT Out-Of-Box Azure Demonstration\n'
                     f'              FAILED\n'
                     f'  Compatible device not detected',
           BANNER_BORDER_LEV_2)
    print(f'\n')
    exit(APP_RET_COM_NOT_FOUND)


# Instantiate global classes
ac = IotCloud(COM_PORT, 230400)      # Create primary IotCloud object
if APP_CMD_LOG_FILE and ac.log_file_handle:
    logline = f' Log File:  {APP_CMD_LOG_PATH}/{APP_CMD_LOG_FILE} '
else:
    logline = f' Log File:  Disabled'

# Show startup banner
banner(f' Starting {MODEL} IoT Out-Of-Box Azure Demonstration\n'
       f'              Detected {MODEL} on {COM_PORT} \n'
       f'         DPS Forced[ {FORCE_DPS_REG} ]  Display Level[ {APP_DISPLAY_LEVEL} ] \n'
       f'\n{logline: ^50}\n',
       BANNER_BORDER_LEV_2)
print(f'  {"Press [ESC][ESC] to exit the script": ^50}\n')

try:
    MAX_ID_LEN = 23
    if len(MQTT_CLIENT_ID) > MAX_ID_LEN or len(DEVICE_CERT_FILENAME) > MAX_ID_LEN or len(DEVICE_KEY_FILENAME) > MAX_ID_LEN:
        print(f'\n\n  Error: Invalid data detected in \'{APP_CONFIG_FILE}\'\n'
              f'  ----------------------------------------\n'
              f'  The maximum string length({MAX_ID_LEN}) has been exceeded by one or more of the following:\n'
              f'      device_cert_filename({len(DEVICE_CERT_FILENAME)})\n'
              f'      device_key_filename({len(DEVICE_KEY_FILENAME)})\n'
              f'      mqtt_client_id({len(MQTT_CLIENT_ID)})\n\n')
        exit(1)

    while True:  # Start the app
        if ac.app_state_prev != ac.app_state:
            ac.app_state_prev = ac.app_state
        ac.run_app()

except KeyboardInterrupt:
    print(f'\n   [CTRL-C] User Exit')

except serial.SerialException:
    print(f'\n  Serial UART Communication Lost')
