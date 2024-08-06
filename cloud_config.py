#!/usr/bin/python3

# Copyright (C) 2024 released Microchip Technology Inc.  All rights reserved.
# Microchip licenses to you the right to use, modify, copy and distribute
# Software only when embedded on a Microchip microcontroller or digital signal
# controller that is integrated into your product or third party product
# (pursuant to the sublicense terms in the accompanying license agreement).
# You should refer to the license agreement accompanying this Software for
# additional information regarding your rights and obligations.
# SOFTWARE AND DOCUMENTATION ARE PROVIDED AS IS WITHOUT WARRANTY OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING WITHOUT LIMITATION, ANY WARRANTY OF
# MERCHANTABILITY, TITLE, NON-INFRINGEMENT AND FITNESS FOR A PARTICULAR PURPOSE.
# IN NO EVENT SHALL MICROCHIP OR ITS LICENSORS BE LIABLE OR OBLIGATED UNDER
# CONTRACT, NEGLIGENCE, STRICT LIABILITY, CONTRIBUTION, BREACH OF WARRANTY, OR
# OTHER LEGAL EQUITABLE THEORY ANY DIRECT OR INDIRECT DAMAGES OR EXPENSES
# INCLUDING BUT NOT LIMITED TO ANY INCIDENTAL, SPECIAL, INDIRECT, PUNITIVE OR
# CONSEQUENTIAL DAMAGES, LOST PROFITS OR LOST DATA, COST OF PROCUREMENT OF
# SUBSTITUTE GOODS, TECHNOLOGY, SERVICES, OR ANY CLAIMS BY THIRD PARTIES
# (INCLUDING BUT NOT LIMITED TO ANY DEFENSE THEREOF), OR OTHER SIMILAR COSTS.

# @file     Handles reading, writing and validating the json configuration
#           parameters from both the input file and the CLI.
#           If this config file does not exist, it is created and the user is
#           prompted for the required parameters.

# @info     FILENAME.cfg
#               format: JSON
#               Keys & Values: ALl must be enclosed in quotes
#                              No SPACES allowed. Values must by <128 bytes long.
#

import json

PARAMETER_FILE = "app.cfg"

MAX_VALUE_LEN = 256
# JSON default values for the config file dictionary
#   If a config file does NOT exist, the default 'app.cfg' is created.
#   Set any default values below. When a required string is empty, the user will
#   be prompted for a value when the "oobDemo.py script is first run".
#   Some blank fields will not prompt the user for input as they are not
#   required. These non-prompt fields are set in the '_DO_NOT_PROMPT' array below.
# 
_WIFI_SSID =            ""                      # Wi-Fi SSID
_WIFI_PASSPHRASE =      ""                      # Wi-Fi Passphrase
_WIFI_SECURITY_TYPE =   ""                      # Ref +WSTAC command in "AT Command Specification"
                                                    # 0 = Open 
                                                    # 2 = WPA2 Personal Mixed Mode
                                                    # 3 = WPA2 Personal
                                                    # 4 = WPA3 Personal Transition Mode
                                                    # 5 = WPA3 Personal
                                                    # 6 = WPA2 Enterprise Mixed Mode
                                                    # 7 = WPA2 Enterprise
                                                    # 8 = WPA3 Enterprise Transition Mode
                                                    # 9 = WPA3 Enterprise

_DEVICE_CERT_FILENAME = "ClientCert"            # Manually set. Device "public" certificate file name w/o extension
_DEVICE_KEY_FILENAME =  "ClientKey"             # Manually set. Device "private" certificate file name w/o extension
_CA_CERT_NAME = "mosquitto"                     # Manually set. Certificate Authority Certificate Name


# REQUIRED NTP Time server for secure connections. 
# IP address is preferred here over a URL: 
# 162.159.200.1, 139.59.55.93, 216.239.35.0
_NTP_SERVER_IP_ADDR = "162.159.200.1"           # This should be an IP Address over a URL           

_MQTT_ROOT_TOPIC =      ""                      # Client ID = Device Name + Last 3 bytes of the MAC address. i.e. RNWF02_0A-44-DE 
                                                # Full topic string eg: "RNWF02_0A-44-DE/data/temp/outside"
_MQTT_SUB_TOPIC =       ""                      # Optional sub-topic supporting Module(%M), MAC(%N) 
_MQTT_SUBSCRIPTION =    "#"                     # Default subscription string: "{_MQTT_ROOT_TOPIC}/{_MQTT_SUB_TOPIC}/{THIS_FIELD}"                                            
_MQTT_USERNAME =        ""                      # Manually set. For test.mosquitto.org: "rw"
_MQTT_PASSWORD =        ""                      # Manually set test.mosquitto.org: "readwrite"
_MQTT_VERSION =         "3"                     # MQTT v3 supported by the script
_MQTT_KEEP_ALIVE =      "45"                    # Seconds to keep MQTT session open
_MQTT_BROKER_URL =      "test.mosquitto.org"    # For MQTT broker 
_MQTT_BROKER_PORT =     "1883"                  # i.e. 1883, 1884 (if MQTT Username & password are set)

# Search 'oobDemo.py' for definition of "APP_DISPLAY_LEVEL"
_DISPLAY_LEVEL =        "4"                     # Enable additional CLI output & info
                                                    # 0 - Extra displays off...cleanest output (minimum output info)
                                                    # 1 - Display State Banners & lower
                                                    # 2 - Display info and events & lower
                                                    # 3 - Display 'Demo' IOTC data and lower
                                                    # 4 - Display Decodes like JSON & lower (maximum output info)
_AT_COMMAND_TIMEOUT =   "20"                    # Default AT+ command timeout in seconds
_LOG_FILE_SPEC =        "%M_%D_@_%T.log"        #  Default log file name is ""; Options: %M=Model, %D=Date, %T=Time
                                                #  i.e: "%M_%D_@_%T.log" would create
                                                #       "RNWF02_NOV-01-2023_@_10-45-59.txt"

_DO_NOT_PROMPT = {                              # Parameters not commented and not set in cfg file, will prompt user
    "wifi_ssid",                                # Wi-Fi credentials are set via a 'menu' within the 'oobdemo.py' script.
    "wifi_passphrase",                      
    "wifi_security",
    "device_cert_filename",                     # For TLS feature
    "device_key_filename",                      # For TLS feature
    "ca_cert_name",                             # For TLS feature
    "mqtt_root_topic",
    "mqtt_sub_topic",
    "mqtt_subscription",
    "mqtt_username",
    "mqtt_password",
    "mqtt_version",
    "mqtt_keep_alive",
    # "mqtt_broker_url",                          
    # "mqtt_broker_port",                         
    "ntp_server_ip_addr",
    "display_level",
    "at_command_timeout",
    "log_filename"
    }

class iot_parameters:
    """ Class handles reading, writing and validating the 
        config file defined by default 'PARAMETER_FILE' 
        Values are stored in a dictionary and can be set manually 
        by editing the 'app.cfg' file or at the CLI prompts. If 
        the "app.cfg" file does not exist it is created. Required, 
        missing parameters will prompt the user for those values
        at run time.
    """
    def __init__(self, filename=PARAMETER_FILE, disp_params=False):
        self.filename = filename
        self.file_was = "READ"
        self.display_params = disp_params
        self.no_prompt_keys = _DO_NOT_PROMPT  
        self.params = dict(
                           # User setting for Wi-Fi communications
                           wifi_ssid=_WIFI_SSID,                            # Menu-set. Wi-Fi menu prompt if not set in config file
                           wifi_passphrase=_WIFI_PASSPHRASE,                # Menu-set. User prompted on SSID menu selection
                           wifi_security=_WIFI_SECURITY_TYPE,               # Auto-set from Wi-Fi scan data. Manual setting optional.

                           # Uncomment these if 'oobDemo.py' global variable 'EN_CERT_SUPPORT' is set to True
                           device_cert_filename=_DEVICE_CERT_FILENAME,      # For TLS
                           device_key_filename=_DEVICE_KEY_FILENAME,        # For TLS
                           ca_cert_name = _CA_CERT_NAME,                    # For TLS

                           mqtt_root_topic=_MQTT_ROOT_TOPIC,                # Auto-set if not already set. Topic=Model_XX_XX_XX (X's last 3 bytes of MAC address)
                           mqtt_sub_topic=_MQTT_SUB_TOPIC,                  # Optional sub topic added after root topic "root\OPTIONAL_SUB"
                           mqtt_subscription=_MQTT_SUBSCRIPTION,            # Auto-set to '#' to subscribe to all telemetry data. Manual optional.

                           mqtt_username=_MQTT_USERNAME,                    # Set manually to enable PW security. Requires PW + Port == 1884
                           mqtt_password=_MQTT_PASSWORD,                    # Set manually to enable PW security. Requires Username + Port == 1884
                           mqtt_version=_MQTT_VERSION,                      # Auto-set to "3". Optional setting "5"
                           mqtt_keep_alive=_MQTT_KEEP_ALIVE,                # Auto-set. Time out period for MQTT traffic before disconnect. 
                           mqtt_broker_url=_MQTT_BROKER_URL,                # Auto-set to "test.mosquitto.org". Manual setting optional.
                           mqtt_broker_port=_MQTT_BROKER_PORT,              # Auto-set to "1883". Optional: For PW security, manually set to 1884.

                           ntp_server_ip_addr=_NTP_SERVER_IP_ADDR,          # Auto-set when TLS is supported. Should be an IP address over a URL which may fail.
                           display_level=_DISPLAY_LEVEL,                    # Auto-set. 0-4 for minimum to maximum data and reporting in CLI.
                           at_command_timeout=_AT_COMMAND_TIMEOUT,          # Auto-set. Sets period in seconds before an AT+ command fails when response is not received.
                           log_filename=_LOG_FILE_SPEC                      # Auto-set. [MODEL_Name].log. Options: Model(%M), Time(%T) and Date(%D)              
                          )                                                 #   eg: "%M_%D@%T.log" would create
                                                                            #       "RNWF02_NOV-01-2023@10-45-59.txt"
        try:
            self.read()
        except BaseException as e:
            self.error_handler(e)
        try:
            self.validate()
        except KeyboardInterrupt:
            print(f'\n\n  [CTRL-C] User Exit')
            exit(1)
        except FileNotFoundError as e:
            self.error_handler(e)
        except AttributeError as e:
            self.error_handler(e)

        if self.display_params:
            self.display()

    def error_handler(self, e):
        """ Method is called when an error is detected and provides
            possible solutions to the user.
        """
        error_name = str(type(e).__name__)
        msg = str("")
        if "JSONDecodeError" in error_name:
            msg = str(f' {type(e).__name__}\n')
            msg += str(f'   {e.msg} @ line:{e.lineno} col:{e.colno}\n\n')
            msg += str(f'   - Locate & fix JSON syntax error in "{self.filename}"\n')
            msg += str(f'   - Save & re-run the application')
        elif "PermissionError" in error_name:
            msg = str(f' {type(e).__name__}\n')
            msg += str(f'   - The "{self.filename}" file may be set to READONLY\n')
            msg += str(f'   - Remove READONLY attribute or recreate the file')
        elif "AttributeError" in error_name:
            msg = str(f' {type(e).__name__}\n')
            msg += str(f'   - The file "{self.filename}" might be missing quotes around the value \'{e.obj}\'\n')
        else:
            msg = str(f' {type(e).__name__}\n')
            msg += str(f'   {e.msg} @ line:{e.lineno} col:{e.colno}\n\n')

        print('\n')
        print(msg)
        exit(1)

    def write(self) -> None:
        """ Method writes the in-memory dictionary to disk. When
        called by the "read()" function, only dictionary 'keys'
        are written and dictionary values are empty "".
        :return: Nothing
        """
        try:
            file = open(self.filename, 'w', encoding='UTF-8')
        except BaseException as e:
            self.error_handler(e)


        json.dump(self.params, file, indent=4)
        file.close()

    def read(self):
        """ Module attempts to open the configuration file
        from disk and read into memory. If no file exists,
        a file is created with a call to "write()".
        :return: Nothing
        """
        try:
            file = open(self.filename, "r", encoding='UTF-8')
            string_dict = file.read()
            self.params = json.loads(string_dict)
            file.close()
            # if self.display_params:
            #     print("\n  Configuration file '%s'" % self.filename)
        except FileNotFoundError:
            self.file_was = "CREATED"
            self.write()
        print("\n  Configuration file '%s' was %s" % (self.filename, self.file_was))
  
    def display(self):
        """ Helper function display the configuration dictionary keys & values
        :return:
        """
        print(f'\n  Config File \'{self.filename}\'')
        for key in self.params.keys():
            print(f'    {key:24} = "{self.params[key]}"')

    def validate(self):
        """ Method to validate both the read in configuration file
        and/or user input from the CLI. Only does basic checks for
        No empty strings, No spaces and < 256 chars in length.
        :return: Nothing
        """
        header_done = False
        for key in self.params.keys():
            value = ""
            while value == "":
                value = self.params[key]
                
                # print(f'value: ("{value}") dict({key}:"{self.params[key]}")')

                if key in self.no_prompt_keys:
                    # Skip this key because it is set at runtime or is optional
                    break

                # General validation
                if value == "" or value.find(' ') != -1 or len(value) > MAX_VALUE_LEN:
                    value = ""
                    # Prompt user for a dictionary value
                    # Skip the passphrase prompt if security is set to '0' (open Wi-Fi network)
                    # if (key != "wifi_passphrase") or \
                    #         (key == "wifi_passphrase" and self.params["wifi_security"] != "0"):
                    if header_done is False:
                        print("\n  Use [CTRL-C] to Exit\n")
                        print("  Enter required parameters:\n  --------------------------")
                        header_done = True
                    self.params[key] = input('  {:<24s}: '.format(key.upper() + " ?"))
                    #   If Wi-Fi passphrase is empty, set Wi-Fi security to '0'
                    # if key == "wifi_passphrase" and self.params[key] == "":
                    #     value = self.params["wifi_security"] = "0"

        # Write the file to disk. User should not be prompted on next run.
        self.write()
        return

    def test():
        """
        Can be used to test this module or independently create a configuration
        JSON file.
        :return: Nothing
        """
        print(f'\n\nApp Configuration Helper\n-----------------------------')
        print('Creates or reads an existing configuration file.')
        print(f' - If a path is not specified, the file is expected in \'this\' directory.')
        print(f' - Press [ENTER] to use the default \'{PARAMETER_FILE}\' filename.')
        print(f' - Use [CTRL-C] to exit.')
        print(f'\n   Eg: "myConfig.cfg", "C:\somefolder\myConfig.cfg"')

        try:
            fn = ''
            fn = input('\n{:<3s}Enter a file name>'.format(" "))
            if fn == '':
                fn = PARAMETER_FILE
            iot_parameters(fn, True)
            print("\n")
        except FileNotFoundError:
            print(f'\n\n  ERROR! Invalid PATH or FILENAME \'{fn}\'\n')
        except KeyboardInterrupt:
            print(f'\n\n  [CTRL-C] User Exit')

if __name__ == "__main__":
    iot_parameters.test()
