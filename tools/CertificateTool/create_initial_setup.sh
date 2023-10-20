#!/bin/sh

if [ "$1" == "" ]
then
  read -p "Enter the folder name for Root CA(Default=rootca):- " root_folder
  root_folder=${root_folder:-rootca}
else
  root_folder=$1
fi
#read -p "Enter the folder name for Root CA(Default=rootca):- " root_folder
#root_folder=${root_folder:-rootca}

if [ "$2" == "" ]
then
  read -p "Enter the domain suffix(Default=company.com):- " domain_suffix
  domain=${domain:-company.com}
else
  domain=$2
fi
#read -p "Enter the domain suffix(Default=company.com):- " domain_suffix
#domain=${domain:-company.com}

if [ "$3" == "" ]
then
  read -p "Enter the Root CA common name(Default=Custom RootCA):- " rootca_common_name
  rootca_common_name=${rootca_common_root_folder:-Custom RootCA}
else
  rootca_common_name=$3
fi
#read -p "Enter the Root CA common name(Default=Custom RootCA):- " rootca_common_name
#rootca_common_name=${rootca_common_root_folder:-Custom RootCA}

if [ "$4" == "" ]
then
  read -p "Enter the folder name for Sub CA(Default=subca):- " subca_folder
  subca_folder=${subca_folder:-subca}
else
  subca_folder=$4
fi
#read -p "Enter the folder name for Sub CA(Default=subca):- " subca_folder
#subca_folder=${subca_folder:-subca}

mkdir ${root_folder}
cd ${root_folder}
mkdir certs db private
chmod 700 private
touch db/index
openssl rand -hex 16 > db/serial
echo 1001 > db/crlnumber

home=../${root_folder}

echo "[default]
name                     = ${root_folder}
domain_suffix            = ${domain}
aia_url                  = http://${root_folder}.${domain}/${root_folder}.crt
crl_url                  = http://${root_folder}.${domain}/${root_folder}.crl
default_ca               = ca_default
name_opt                 = utf8,esc_ctrl,multiline,lname,align

[ca_dn]
commonName               = ${rootca_common_name}

[ca_default]
home                     = ../${root_folder}
database                 = ${home}/db/index
serial                   = ${home}/db/serial
crlnumber                = ${home}/db/crlnumber
certificate              = ${home}/${root_folder}.crt
private_key              = ${home}/private/${root_folder}.key
RANDFILE                 = ${home}/private/random
new_certs_dir            = ${home}/certs
unique_subject           = no
copy_extensions          = none
default_days             = 3650
default_crl_days         = 365
default_md               = sha256
policy                   = policy_c_o_match

[policy_c_o_match]
countryName              = optional
stateOrProvinceName      = optional
organizationName         = optional
organizationalUnitName   = optional
commonName               = supplied
emailAddress             = optional

[req]
default_bits             = 2048
encrypt_key              = yes
default_md               = sha256
utf8                     = yes
string_mask              = utf8only
prompt                   = no
distinguished_name       = ca_dn
req_extensions           = ca_ext

[ca_ext]
basicConstraints         = critical,CA:true
keyUsage                 = critical,keyCertSign,cRLSign
subjectKeyIdentifier     = hash

[sub_ca_ext]
authorityKeyIdentifier   = keyid:always
basicConstraints         = critical,CA:true,pathlen:0
extendedKeyUsage         = clientAuth,serverAuth
keyUsage                 = critical,keyCertSign,cRLSign
subjectKeyIdentifier     = hash

[client_ext]
authorityKeyIdentifier   = keyid:always
basicConstraints         = critical,CA:false
extendedKeyUsage         = clientAuth
keyUsage                 = critical,digitalSignature
subjectKeyIdentifier     = hash" > rootca.conf

openssl req -new -config rootca.conf -out rootca.csr -keyout private/rootca.key -nodes
openssl ca -selfsign -config rootca.conf -in rootca.csr -out rootca.crt -extensions ca_ext -batch

echo '###################################################'
echo '##################### ROOT CA #####################'
echo '##############SUCCESS SUCCESS SUCCESS##############'
echo '###################################################'

echo ""
echo ""


cd ../
mkdir ${subca_folder}
chmod 700 ${subca_folder}
cd ${subca_folder}
mkdir certs db private
chmod 700 private
touch db/index
openssl rand -hex 16 > db/serial
echo 1001 > db/crlnumber

home=${subca_folder}

echo "[default]
name                     = ${subca_folder}
domain_suffix            = ${domain}
aia_url                  = http://${subca_folder}.${domain}/${subca_folder}.crt
crl_url                  = http://${subca_folder}.${domain}/${subca_folder}.crl
default_ca               = ca_default
name_opt                 = utf8,esc_ctrl,multiline,lname,align

[ca_dn]
commonName               = ${rootca_common_name} SubCA

[ca_default]
home                     = ${subca_folder}
database                 = ${home}/db/index
serial                   = ${home}/db/serial
crlnumber                = ${home}/db/crlnumber
certificate              = ${home}/${subca_folder}.crt
private_key              = ${home}/private/${subca_folder}.key
RANDFILE                 = ${home}/private/random
new_certs_dir            = ${home}/certs
unique_subject           = no
copy_extensions          = copy
default_days             = 365
default_crl_days         = 90
default_md               = sha256
policy                   = policy_c_o_match

[policy_c_o_match]
countryName              = optional
stateOrProvinceName      = optional
organizationName         = optional
organizationalUnitName   = optional
commonName               = supplied
emailAddress             = optional

[req]
default_bits             = 2048
encrypt_key              = yes
default_md               = sha256
utf8                     = yes
string_mask              = utf8only
prompt                   = no
distinguished_name       = ca_dn
req_extensions           = ca_ext

[ca_ext]
basicConstraints         = critical,CA:true
keyUsage                 = critical,keyCertSign,cRLSign
subjectKeyIdentifier     = hash

[sub_ca_ext]
authorityKeyIdentifier   = keyid:always
basicConstraints         = critical,CA:true,pathlen:0
extendedKeyUsage         = clientAuth,serverAuth
keyUsage                 = critical,keyCertSign,cRLSign
subjectKeyIdentifier     = hash

[client_ext]
authorityKeyIdentifier   = keyid:always
basicConstraints         = critical,CA:false
extendedKeyUsage         = clientAuth
keyUsage                 = critical,digitalSignature
subjectKeyIdentifier     = hash" > subca.conf

openssl req -new -config subca.conf -out subca.csr -keyout private/subca.key -nodes

openssl ca -config ../${root_folder}/rootca.conf -in subca.csr -out subca.crt -extensions sub_ca_ext -batch

echo '###################################################'
echo '##################### Sub CA ######################'
echo '##############SUCCESS SUCCESS SUCCESS##############'
echo '###################################################'

cd ..
mkdir "devcerts"

