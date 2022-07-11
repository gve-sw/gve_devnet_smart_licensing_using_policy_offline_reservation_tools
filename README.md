# Cisco Smart Licensing - Offline License Reservation 

This is a sample project to demonstrate an offline license reservation using the "Smart License Using Policy" process, which might be used if Smart License enabled devices are in an air-gapped network.

This project contains a Postman collection & set of Python scripts to help automate the license management process.

Using either method, you can:
 - Request an offline license reservation from Smart Licensing
 - Upload a device usage report (RUM report)
 - Generate a Smart License reporting ACK
 - Return reserved licenses


## **Contacts**
* Matt Schmitz (mattsc@cisco.com)

## **Solution Components**
* Cisco Smart Licensing


## **Installation/Configuration - Postman Collection**


**[Step 1] Clone repo:**

```bash
git clone <repo_url>
```

**[Step 2] Import Postman Collection:**

1. Open Postman
2. `File > Import`
3. Import the following two files: `Smart Licensing Using Policy Offline.postman_collection.json` & `Smart Licensing.postman_environment.json`

**[Step 3] Configure required variables:**

There are a number of environment variables for this collection. For all requests, only the following are required:
 - `client_id`, `client_secret`, `smart_account`, `virtual_account`, `device_pid`, `device_serial`, and `license_tag`   
 - Additional variables may be required to upload usage reports or remove licenses.
 - Please see the below `Step 3` secion for Python Install/Config for details on these variables 

## **Installation/Configuration - Python Scripts**

**[Step 1] Clone repo:**

```bash
git clone <repo_url>
```

**[Step 2] Install required dependencies:**

```bash
pip install -r requirements.txt
```

**[Step 3] Configure required variables:**

1. Copy the `.env-example` file & rename to `.env`
2. Fill out the following required variables in that file:

```bash
##############
# SET THESE:
CLIENT_ID=""
CLIENT_SECRET=""
SMART_ACCOUNT=""
VIRTUAL_ACCOUNT=""
DEVICE_SERIAL=""
DEVICE_PID=""
DEVICE_HOSTNAME=""
LICENSE_TAG=""
##############
```

 - `CLIENT_ID` & `CLIENT_SECRET` - These are the Smart Licensing API credentials. Please follow the guide [here](https://apidocs-prod.cisco.com/?path=requestapiinfo) on how to register a new application & obtain these credentials.
 - `SMART_ACCOUNT` - The target Smart Account domain to use for licensing requests. (Example: networkteam.company.local)
 - `VIRTUAL_ACCOUNT` - The target Virtual Account to use for licensing requests. (Example: US1-LAB-NETWORK)
 - `DEVICE_SERIAL` & `DEVICE_PID` - These can be obtained on the target network device via the `show license udi` command. (Example: UDI: PID:C8000V,SN:ABCDEF1234)
 - `DEVICE_HOSTNAME` - The device hostname to be attached to the license reservation request
 - `LICENSE_TAG` - The ISO 19770-2 license tag (Example: regid.2019-03.com.cisco.DNA_HSEC,1.0_509c41ab-05a8-431f-95fe-ec28086e8844). This can be obtained in one of two ways:
    1. Run the following command on the target network device: `show license tech support | include Entitlement`
    2. Open the Postman collection & run the task `03 - Get License Usage by Tag` under the `License Verification` section
        -  In order to use this, please first run `01 - Get Auth Token` followed by `02 - Get SA/VA IDs`


## **Usage - Postman Collection**

The Postman collection is structured in the order of operations for use. The collection contains a number of tests for each request, which will query the response body & save the required variables for future requests.

All processes (reserve license, delete license, upload report, etc) **must** start with the `Authentication & SA/VA ID` section (Steps 1 & 2 here). 


**[Step 1] Get Authentication Token**

 - Run the Postman request: `Authentication & SA/VA ID` > `01 - Get Auth Token`
    - This will send `client_id` & `client_secret` to Cisco SSO, and provide an access token for Smart Licensing requests
    - This request will save the provided access token under the `access_token` variable

**[Step 2] Collect Smart Account & Virtual Account ID Numbers**

For all requests, we'll need the unique identifiers for the Smart Account & Virtual Account.

 - Run the Postman request: `Authentication & SA/VA ID` > `02 - Get SA/VA IDs`
    - This will query all Smart Accounts & Virtual Accounts that the API token has access to
    - This request will locate & save the `account_id` & `virtual_account_id` fields from the response for future requests

**[Step 3] Request License Reservation**

 - Run the Postman request: `License Reservation` > `03 - Get SA/VA IDs`
    - This request will send a license reservation request to Smart Licensing
    - Smart Licensing will return a task ID number (poll_id) which can be used to check the status of the task.
    - This request will parse & store the `poll_id` field


**[Step 4] Check License Reservation Status**

 - Run the Postman request: `License Reservation` > `04 & 06 - Check License Request / Obtain License / Get License ACK`
    - This request checks the status of a Smart Licensing task
    - When in-progress, Smart Licensing returns a `status` of `OK_POLL`
    - When completed, Smart Licensing returns a `status` of `COMPLETE`
 - If a license was successfully generated & reserved, the license data will be in the `smart_license` field
    - This field is base64 encoded & must be decoded prior to installing on the target device

 - License can be placed on a TFTP server & installed on the device with the following command:
    - `license smart import <bootflash|tftp>:lic.txt`

**[Step 5] Submit License Usage Report**
 
  *Note: This step can be troublesome in Postman, as it will require you to pull certain info from the device usage report & apply it in Postman **exactly** as it is in the device report. Any mis-matches will be rejected by the Smart Licensing server. The included python scripts will automatically parse & structure the POST payload in the format Smart Licensing is expecting.*

 - Collect device usage reports from the device with the following command:
    - `license smart save usage all file <bootflash|tftp>:<filename>`
 - Open the device usage report in a text editor, and find the latest usage report for the license you are reserving.
 - Within that usage report, copy the report payload & enter it in the Postman environment variable `usage_payload`
    - Note, this is only the contents of the payload field, starting with `"{\"asset_identification\":{\"asset\":` and ending with `\"value\":{\"type\":\"COUNT\",\"value\":\"1\"}}]}"` (just before the `header":{"type":"rum"}` section)
        - **NOTE:** Do not edit this payload. The payload must appear exactly as it does in the device usage report, with no spaces & escaped quotes. 
        - Smart Licensing will evaluate the signature of this payload field value against the provided signature. If they do not match, the report will be rejected.
        - For example, see the below payload for what must be included:
         ```
         "{\"asset_identification\":{\"asset\":{\"name\":\"regid.2019-10.com.cisco.C8000V,1.0_e361c3dc-27c2-4084-b4a4-cae639cff335\"},\"instance\":{\"sudi\":{\"udi_pid\":\"C8000V\",\"udi_serial_number\":\"abcdef123456\"}},\"signature\":{\"signing_type\":\"builtin\",\"key\":\"regid.2019-10.com.cisco.C8000V,1.0_e361c3dc-27c2-4084-b4a4-cae639cff335\",\"value\":\"abcdef123456\"}},\"meta\":{\"entitlement_tag\":\"regid.2018-12.com.cisco.DNA_P_50M_A,1.0_100fb8b2-f5cc-459c-9253-ac77b827fd71\",\"report_id\":1646687408,\"software_version\":\"17.06.02\",\"ha_udi\":[{\"role\":\"Active\",\"sudi\":{\"udi_pid\":\"C8000V\",\"udi_serial_number\":\"abcdef123456\"}}]},\"measurements\":[{\"log_time\":1657549482,\"metric_name\":\"ENTITLEMENT\",\"start_time\":1657549046,\"end_time\":1657550382,\"sample_interval\":1336,\"num_samples\":2,\"meta\":{\"termination_reason\":\"CurrentUsageRequested\"},\"value\":{\"type\":\"COUNT\",\"value\":\"1\"}}]}"
         ```

 - Within the same usage report, copy the `key` & `value` fields under the `signature` section - and add to the Postman environment variables `usage_signature_key` & `usage_signature_value` 
    - The `signature` section is the last item in the usage report payload
    - Example from a usage report: `"signature":{"sudi":{"udi_pid":"C8000V","udi_serial_number":"ABCD12345"},"signing_type":"builtin","key":"<usage_signature_key>","value":"<usage_signature_value>"}`
 - Run the Postman request: `License Reservation` > `05 - Report License Usage`
 - Similar to **Step 3**, the response will be a `poll_id` that we can use to check the status of the report

**[Step 6] Check License Usage Report Status**

 - Run the Postman request: `License Reservation` > `04 & 06 - Check License Request / Obtain License / Get License ACK`
    - Similar to **Step 3**, continue polling the status until Smart Licensing returns a `status` of `COMPLETE`
    - *Note: Usage reports can take several minutes to process*
 - If a usage report was accepted, a device ACK will be generated. This is stored in the `smart_license` field
    - This field is base64 encoded & must be decoded prior to loading onto the device
 - ACK data can be placed on a TFTP server & installed on the device with the following command:
    - `license smart import <bootflash|tftp>:ACK.txt`
 - Validate with the following command:
    - `show license status`



**[OPTIONAL] Return a License / Remove Device**

 - Please ensure you have recently run **Step 1** & **Step 2** and have a valid access token & SA/VA IDs.
 - Generate a license return code on your device with the following command:
    - `license smart authorization return local online`
 - Place this return code in the Postman environment variable: `remove_code`
 - Run the Postman request: `License Return` > `03 - Remove License`
    - This will provide a `poll_id` to check task status
 - Run the Postman request: `License Return` > `04 - Check Removal Request`
    - Continue polling the status until Smart Licensing returns a `status` of `COMPLETE`

**[OPTIONAL] Check License Inventory / Validate License Consumption**

 - Please ensure you have recently run **Step 1** & **Step 2** and have a valid access token & SA/VA IDs.
 - Run the Postman request: `License Verification` > `03 - Get License Usage by Tag`
    - Run the request as-is to query all licenses in the account
    - or fill in the `tags` list to query only specific licenses

This request can be used to look up the required ISO 19770-2 license tag for other requests

Alternatively, we can query a list of all devices in our Virtual Account - and see which devices have licenses assigned:

 - Run the Postman request: `License Verification` > `03a - Get Devices & License Assignment`

This request will query ALL devices in a Virtual account & display details on device identifiers (PID, SN, Name, etc) and any licenses assigned.


## **Usage - Python Scripts**

The included Python scripts follow the same order as the Postman collection steps above, but are simplified since we can automate a lot of the background tasks (like collecting auth tokens & SA/VA IDs).

**[Step 1] Generate License Reservation**

 - Run the Python script: `01 - reserve license.py`
 - If successful, the script will output the license XML payload to the console
    - This license will also be saved locally as: `lic.txt`
 - License can be placed on a TFTP server & installed on the device with the following command:
    - `license smart import <bootflash|tftp>:lic.txt`


**[Step 2] Upload Usage Report & Download ACK**

 - Collect device usage reports from the device with the following command:
    - `license smart save usage all file <bootflash|tftp>:<filename>`
 - Copy this file to the same directory as the Python scripts, named as `usage.txt`
 - Run the Python script: `02 - report license usage.py`
    - The script will prompt you to confirm that the usage file is present
 - If successful, the script will output the ACK XML payload to the console
    - This data will also be saved locally as: `ack.txt`
 - ACK data can be placed on a TFTP server & installed on the device with the following command:
    - `license smart import <bootflash|tftp>:ACK.txt`

**[OPTIONAL] Return a License / Remove Device**

 - Generate a license return code on your device with the following command:
    - `license smart authorization return local online`
 - Run the Python script: `03 - remove license.py`
    - The script will prompt to enter the license return code

# Screenshots

All screenshots below are from the Python script execution & reserving a DNA-HSEC license for a Catalyst 8000V router.

**Example of license reservation:**

![/IMAGES/example_license_reservation.png](/IMAGES/example_license_reservation.png)

**Example of license usage report:**

![/IMAGES/example_usage_report.png](/IMAGES/example_usage_report.png)

**Example of license removal:**

![/IMAGES/example_return_license.png](/IMAGES/example_return_license.png)





### LICENSE

Provided under Cisco Sample Code License, for details see [LICENSE](LICENSE.md)

### CODE_OF_CONDUCT

Our code of conduct is available [here](CODE_OF_CONDUCT.md)

### CONTRIBUTING

See our contributing guidelines [here](CONTRIBUTING.md)

#### DISCLAIMER:
<b>Please note:</b> This script is meant for demo purposes only. All tools/ scripts in this repo are released for use "AS IS" without any warranties of any kind, including, but not limited to their installation, use, or performance. Any use of these scripts and tools is at your own risk. There is no guarantee that they have been through thorough testing in a comparable environment and we are not responsible for any damage or data loss incurred with their use.
You are responsible for reviewing and testing any scripts you run thoroughly before use in any non-testing environment.