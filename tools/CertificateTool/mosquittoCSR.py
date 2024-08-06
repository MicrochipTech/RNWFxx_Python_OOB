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

# @file     Creates certificate "key" file and a PEM encoded Certificate 
#           Signing Request (CSR) suitable for pasting into the 
#           "https://test.mosquitto.org/ssl/" TLS Client Certificate tool.
#

###################################################
###        Five user 'adjustable' fields        ###
###     Edit these strings, save and rerun      ###
###################################################
country_name: str = "US"
state_or_province_name: str = "Arizona"
locality_name: str = "Chandler"
organization_name: str = "Microchip"
common_name = "www.microchip.com"


line: str = "----------------------------------------------------------------"
crs_url: str = "https://test.mosquitto.org/ssl/" 

try:
    import os 
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    import pyperclip
except ModuleNotFoundError:
    print(f'\n\n{line}')
    print(f'                Error! Python module(s) not found.')
    print(f'{line}\n')
    user_in = input(f'            Install required Python modules now? [Y|n] ')
    if user_in.upper() == 'Y' or user_in == '':
        os.system("pip install -r requirements.txt")
        print(f'\n  Rerun the demo now...\n\n')
    else:
        print(f'\n   Please manually run "pip install -r requirements.txt" from the command line')
    exit(1)

# Prompt to continue
os.system('cls')
print (f'\n\n{line}')
print (f'      PEM encoded Certificate Signing Request (CSR) Tool')
print (f'{line}')
print(f' The certificate tool is about to run with these settings:')
print(f'    Country Name:                  "{country_name}')
print(f'    State or Province Name:        "{state_or_province_name}"')
print(f'    Locality or City Name:         "{locality_name}"')
print(f'    Organization Name:             "{organization_name}"')
print(f'    Common Name:                   "{common_name}"')

print(f'{line}\n')
user_in = input(f'Accept these certificate values? [Y|n] ')
if user_in.upper() == 'N':
    print(f'\n   Edit the "User Adjustable Fields in this file')
    print(f'\n    - Save and rerun.')
    exit(0)

# Start
print(f'\n{line}')
print(f'  Open this link in a browser "{crs_url}"')
print(f'                        then press ENTER.')
print(f'{line}')
user_in = input(f'')

# Generate our key
key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
)

# Write our key to disk for safe keeping
with open("ClientKey.key", "wb") as f:
    f.write(key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.TraditionalOpenSSL,
    encryption_algorithm=serialization.NoEncryption()
 ))

from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes

# Generate a CSR
csr = x509.CertificateSigningRequestBuilder().subject_name(x509.Name([
    # Provide various details about who we are.
    x509.NameAttribute(NameOID.COUNTRY_NAME, f'{country_name}'),
    x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, f'{state_or_province_name}'),
    x509.NameAttribute(NameOID.LOCALITY_NAME, f'{locality_name}'),
    x509.NameAttribute(NameOID.ORGANIZATION_NAME, f'{organization_name}'),
    x509.NameAttribute(NameOID.COMMON_NAME, f'{common_name}'),    
])).add_extension(
    x509.SubjectAlternativeName([
        # Describe what sites we want this certificate for.
        x509.DNSName("mysite.com"),
        x509.DNSName("www.mysite.com"),
        x509.DNSName("subdomain.mysite.com"),
    ]),
    critical=False,
# Sign the CSR with our private key.
).sign(key, hashes.SHA256())

# Write our CSR out to disk.
with open("ClientCSR.pem", "wb") as f:
    f.write(csr.public_bytes(serialization.Encoding.PEM))

csrFile = csr.public_bytes(serialization.Encoding.PEM)
# print(csrFile.decode())
pyperclip.copy(csrFile.decode())    # Put the cert string on the clipboard
f.close()


print (f'\n{line}')
print (f' PEM encoded Certificate Signing Request (CSR) created!')
print (f'{line}')
print (f'  CSR tool @ https://test.mosquitto.org/ssl/\n')
print (f'  1. The CSR has been copied to your "clipboard".')
print (f'     - Paste the clipboard\'s contents into the "CSR" control.')
print (f'     - Press the "Submit" button.')
print (f'\n                      <<<  OR >>>\n')
print (f'     Open the "ClientCSR.pem" file in a text editor.')
print (f'     - Copy the entire file\'s contents to the "clipboard".')
print (f'     - Paste the clipboards content into the "CSR" control.\n')
print (f'  2. Press the "Submit" button...')
print (f'     - Download the certificate to the "CertificateTool" folder.')
print (f'     - Use the filename "ClientCert.crt"')


print (f' ')