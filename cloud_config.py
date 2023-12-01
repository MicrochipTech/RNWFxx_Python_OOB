#!/usr/bin/python3

# Copyright (C) 2023 released Microchip Technology Inc.  All rights reserved.
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

MIN_WIFI_SECURITY_TYPE = 0
MAX_WIFI_SECURITY_TYPE = 9
WIFI_SECURITY_LIST = [0, *range(2, 9, 1)]
MAX_VALUE_LEN = 256
# JSON default values for the config file dictionary
#   If a config file does NOT exist, the default 'app.cfg' is created.
#   Set any default values below. When a required string is empty, the user will
#   be prompted for a value when the "oobDemo.py script is first run".
#   Some blank fields will not prompt the user for input as they are not
#   required for Azure secure connections
# 
_WIFI_SSID =            ""      # Wi-Fi SSID
_WIFI_PASSPHRASE =      ""      # Wi-Fi Passphrase
_WIFI_SECURITY_TYPE =   ""      # Ref +WSTAC command in "AT Command Specification"
                                    # 0 = Open 
                                    # 2 = WPA2 Personal Mixed Mode
                                    # 3 = WPA2 Personal
                                    # 4 = WPA3 Personal Transition Mode
                                    # 5 = WPA3 Personal
                                    # 6 = WPA2 Enterprise Mixed Mode
                                    # 7 = WPA2 Enterprise
                                    # 8 = WPA3 Enterprise Transition Mode
                                    # 9 = WPA3 Enterprise

# NOTE: Limit the next 3 parameters to a MAXIMUM of 23 chars!!!
#       Make sure the certificate Common Name is at most 23 characters ong
_DEVICE_CERT_FILENAME = ""      # Manually set. Device "public" certificate file name w/o extension
_DEVICE_KEY_FILENAME =  ""      # Manually set. Device "private" certificate file name w/o extension
_MQTT_CLIENT_ID =       ""      # Manually set. Azure: Same name as certificate "Common Name"

_ID_SCOPE =             ""      # Manually set. Azure: My apps->App->Settings-Application

# These setting are automatically set on successful Azure DPS registration
_OPERATION_ID =         ""      # "" = Automatically set during Azure DPS
_ASSIGNED_HUB =         ""      # "" = Automatically set during Azure DPS
_FORCE_DPS_REG =        "0"     # When set to 0, after a successful DPS registration
                                #  the returned values for 'Operational_ID' & 'Assigned_ID'
                                #  stored in "app.cfg" will be used for subsequent executions
                                #  and will speed up the login by about 20s.
                                # If set to 1, DPS is forced to re-register every time and will
                                #  be slower due to the additional DPS processing.

# REQUIRED PRE-SET Azure settings
#                       "global.azure-devices-provisioning.net"         # For Baltimore TLS cert
_MQTT_BROKER_URL =      "g2-cert-dps.azure-devices-provisioning.net"    # For DigiCert Global G2 
_MQTT_BROKER_PORT =     "8883"
_TLS_PROVISION_SERVER = "*.azure-devices-provisioning.net"
_TLS_DEVICE_SERVER =    "*.azure-devices.net"
_DEVICE_TEMPLATE =      "dtmi:com:Microchip:AVR128DB48_CNANO;1"

# REQUIRED NTP Time server. Adjust if needed for proper UTC time
_NTP_SERVER =           "0.in.pool.ntp.org"     # i.e. time.google.com"


_MQTT_PASSWORD =        "NA"        # Not used, do not set
_MQTT_VERSION =         "3"         # MQTT v3 or MQTT v5
_MQTT_KEEP_ALIVE =      "45"        # Seconds to keep MQTT session open

# Search 'oobDemo.py' for definition of "APP_DISPLAY_LEVEL"
_DISPLAY_LEVEL =        "3"         # Enable additional CLI output & info

                                        # 0 - Extra displays off...cleanest output
                                        # 1 - Display State Banners & lower
                                        # 2 - Display info and events & lower
                                        # 3 - Display 'Demo' IOTC data and lower
                                        # 4 - Display Decodes like JSON & lower
_AT_COMMAND_TIMEOUT =   "60"        # Default AT+ command timeout in seconds
_LOG_FILE_SPEC =        "%M.log"    # Default log file name; %M=Model, %D=Date, %T=Time
                                    # i.e: "%M_%D@%T.log" would create
                                    #      "RNWF02_NOV-01-2023@10-45-59.txt"

class iot_parameters:
    """ Class handles reading, writing and validating the 
        config file defined by default 'PARAMETER_FILE' 
        Values are stored in a dictionary and can be set manually 
        by updating the 'app.cfg' file or at the CLI prompts. If 
        the "app.cfg" file does not exist it is created. Required, 
        missing parameters will prompt the user for those values
        at run time.
    """
    def __init__(self, filename=PARAMETER_FILE, disp_params=False):
        self.filename = filename
        self.file_was = "READ"
        self.display_params = disp_params
        self.no_prompt_keys = {"operation_id", "assigned_hub", "display_level", "log"}
        self.params = dict(
                           # User setting for Wi-Fi communications
                           wifi_ssid=_WIFI_SSID,
                           wifi_passphrase=_WIFI_PASSPHRASE,
                           wifi_security=_WIFI_SECURITY_TYPE,

                           # User setting for X.509 certificates
                           device_cert_filename=_DEVICE_CERT_FILENAME,
                           device_key_filename=_DEVICE_KEY_FILENAME,
                           mqtt_client_id=_MQTT_CLIENT_ID,

                           # User setting from Azure account
                           id_scope=_ID_SCOPE,

                           # Auto set during Azure DPS
                           operation_id=_OPERATION_ID,
                           assigned_hub=_ASSIGNED_HUB,

                           # User Option to force DPS regardless of OperationID or AssignedHub
                           force_dps_reg=_FORCE_DPS_REG,

                           # Defaults for Azure...no setting required
                           mqtt_broker_url=_MQTT_BROKER_URL,
                           mqtt_broker_port=_MQTT_BROKER_PORT,
                           tls_provision_server=_TLS_PROVISION_SERVER,
                           tls_device_server=_TLS_DEVICE_SERVER,
                           device_template=_DEVICE_TEMPLATE,
                           ntp_server=_NTP_SERVER,
                           mqtt_password=_MQTT_PASSWORD,
                           mqtt_version=_MQTT_VERSION,
                           mqtt_keep_alive=_MQTT_KEEP_ALIVE,
                           display_level=_DISPLAY_LEVEL,
                           at_command_timeout=_AT_COMMAND_TIMEOUT,
                           log=_LOG_FILE_SPEC
                          )
        try:
            self.read()
        except BaseException as e:
            self.error_handler(e)
        try:
            self.validate()
        except KeyboardInterrupt:
            print(f'\n\n  [CTRL-C] User Exit')
            exit(1)
        except AttributeError as e:
            self.error_handler(e)

        if self.display_params:
            self.display()

    def error_handler(self, e):
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

    # @brief
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
        # if self.filename == PARAMETER_FILE:
        print("\n  Configuration file '%s' was %s" % (self.filename, self.file_was))
        # else:
        #     print("\n  Configuration file '%s' was %s" % (self.filename, self.file_was))


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
        No empty strings, No spaces and < 128 chars in length. Also
        validates security parameter for values (0 to 9 excluding 1).
        :return: Nothing
        """
        header_done = False
        for key in self.params.keys():
            value = ""
            while value == "":
                value = self.params[key]
                # print(f'value: ("{value}") dict({key}:"{self.params[key]}")')
                if key == "wifi_security":
                    # Verify Wi-Fi security is in range [0 - 9, excluding 1]
                    if value.isnumeric() and int(value) in WIFI_SECURITY_LIST:
                        value = value
                    else:
                        value = ""
                if key in self.no_prompt_keys:
                    # Skip this key because it is set at runtime or ??
                    break
                 # General validation
                if value == "" or value.find(' ') != -1 or len(value) > MAX_VALUE_LEN:
                    value = ""
                    # Prompt user for a dictionary value
                    # Skip the passphrase prompt if security is set to '0' (open Wi-Fi network)
                    if (key != "wifi_passphrase") or \
                            (key == "wifi_passphrase" and self.params["wifi_security"] != "0"):
                        if header_done is False:
                            print("\n  Use [CTRL-C] to Exit\n")
                            print("  Enter required parameters:\n  --------------------------")
                            header_done = True
                        self.params[key] = input('  {:<24s}: '.format(key.upper() + " ?"))
                    #   If Wi-Fi passphrase is empty, set Wi-Fi security to '0'
                    if key == "wifi_passphrase" and self.params[key] == "":
                        value = self.params["wifi_security"] = "0"

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
