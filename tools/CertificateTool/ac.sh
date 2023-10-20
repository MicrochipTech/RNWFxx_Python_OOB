#!/bin/sh
clear

CLEAN_BUILD=1

OUT_FOLDER=CertBuilds
if [ ! -d "./${OUT_FOLDER}" ]     # Create the build output folder '_CertBuilds'
  then mkdir "${OUT_FOLDER}"
fi

echo
echo "###########################################"
echo "          X.509 Certificate Tool"
echo
echo "   Enter a unique Device ID/Common Name"
echo "###########################################"
echo
if [ "$1" == "" ]
  then
    read -rp "Device ID(Max 23 char): " device_id
    device_id=${device_id:?Device ID missing}

  else
    device_id=$1
fi

echo
echo
echo "###########################################"
echo "          X.509 Certificate Tool"
echo "  Step 1 of 2: Create Directory Structure"
echo "###########################################"
echo
. ./create_initial_setup.sh "rootca" "company.com" "Custom RootCA" "subca"
# ". ./create_initial_setup.sh:  Syntax makes variables visible in called script
echo
echo
echo "###########################################"
echo "          X.509 Certificate Tool"
echo "      Step 2 of 2: Create Certificates"
echo "      COMMON NAME = ${device_id}"
echo "###########################################"
echo
. ./create_device_certificate.sh ${device_id} "subca"
# ". ./create_device_certificate.sh:  Syntax makes variables visible in called script
echo
echo
echo
echo "###########################################"
echo "          X.509 Certificate Tool"
echo "                  Complete"
echo "###########################################"
echo
echo "Common Name:                    \"${dev_id}\""
echo "Device Certificate file:        \"${dev_id}.pem\""
echo "Device Key file:                \"${dev_id}.key\""
echo "Azure X.509 Intermediate Cert:  \"subca.crt\""
echo
echo
echo "Edit oobDemo's 'app.cfg' with these values"
echo "------------------------------------------"
echo "  \"device_cert_filename\": \"${dev_id}\","
echo "  \"device_key_filename\": \"${dev_id}\","
echo "  \"mqtt_client_id\": \"${dev_id}\","
echo
echo "Upload certificates TO <- FROM:"
echo "-------------------------------"
echo "RNWF02 module  <-  \".\\${OUT_FOLDER}\\${dev_id}\\${dev_id}.pem\""
echo "RNWF02 module  <-  \".\\${OUT_FOLDER}\\${dev_id}\\${dev_id}.key\""
echo "Azure App      <-  \".\\${OUT_FOLDER}\\${dev_id}\\${subca_folder}.crt\""

# Copy to builds folder
if [ ! -d "./${OUT_FOLDER}/${dev_id}" ]
  then
    mkdir "./${OUT_FOLDER}/${dev_id}"
  else
    rm -rf "./${OUT_FOLDER}/${dev_id}/"
    echo "Previous build is being deleted!"
    sleep 1
    mkdir "./${OUT_FOLDER}/${dev_id}"

fi

# Copy certificates to the build folder for easy location
if [ -f "./devcerts/${dev_id}/${dev_id}.key" ]
  then cp ./devcerts/${dev_id}/${dev_id}.key ./${OUT_FOLDER}/${dev_id}
  else echo "Missing device '${dev_id}.key' certificate"
  exit 1
fi

if [ -f "./devcerts/${dev_id}/${dev_id}.pem" ]
  then cp ./devcerts/${dev_id}/${dev_id}.pem ./${OUT_FOLDER}/${dev_id}
  else echo "Missing device '${dev_id}.pem' certificate"
  exit 1
fi

if [ -f "./subca/subca.crt" ]
  then cp ./subca/subca.crt ./${OUT_FOLDER}/${dev_id}
  else echo "Missing device 'subca.crt' certificate"
  exit 1
fi

# Archive the build folders with a move
if [ ${CLEAN_BUILD} -ne 0 ]
  then
    if [ ! -d "./${OUT_FOLDER}/${dev_id}/build" ]
    then

      mkdir "${OUT_FOLDER}/${dev_id}/build"
    fi
  mv "./devcerts" "./${OUT_FOLDER}/${dev_id}/build/devcerts"
  mv "./rootca" "./${OUT_FOLDER}/${dev_id}/build/rootca"
  mv "./subca" "./${OUT_FOLDER}/${dev_id}/build/subca"
fi

