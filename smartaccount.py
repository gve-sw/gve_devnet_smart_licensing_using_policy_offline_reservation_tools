"""
Copyright (c) 2022 Cisco and/or its affiliates.
This software is licensed to you under the terms of the Cisco Sample
Code License, Version 1.1 (the "License"). You may obtain a copy of the
License at
               https://developer.cisco.com/docs/licenses
All use of the material herein must be in accordance with the terms of
the License. All rights not expressly granted by the License are
reserved. Unless required by applicable law or agreed to separately in
writing, software distributed under the License is distributed on an "AS
IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
or implied.
"""

import re
import requests
import json
import os
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from dotenv import load_dotenv
from rich.console import Console
import time
import string
import secrets

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# Cisco Smart Account URLs & API paths
AUTH_URL = "https://cloudsso.cisco.com/as/token.oauth2"
BASE_URL = "https://swapi.cisco.com/services/api/smart-accounts-and-licensing/"
SMART_ACCOUNT_URL = "v2/accounts/search"
AUTH_REQUEST = "v2/devices/authrequest"
POLL_REQUEST = "v2/accounts/poll"
USAGE_REPORT = "v2/devices/reportusage"

# Required to send random nonce with most API calls to Smart Licensing
NONCE = "".join(
    (secrets.choice(string.ascii_letters + string.digits) for i in range(16))
)

# Load environment variables
load_dotenv()
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
SMART_ACCOUNT = os.getenv("SMART_ACCOUNT")
VIRTUAL_ACCOUNT = os.getenv("VIRTUAL_ACCOUNT")
LICENSE_TAG = os.getenv("LICENSE_TAG")


console = Console()


class SmartAccount:
    def __init__(self):
        self.s = requests.Session()
        self.auth_token = {}
        self.device_headers = None

    def getAuthToken(self):
        """
        Request access token to Smart License APIs
        """
        form_data = {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "client_credentials",
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        console.print("Sending authentication request...")
        response = self.postData(AUTH_URL, form_data, headers)
        # Pull token out of response & save for all future requests
        token = json.loads(response)["access_token"]
        self.auth_token = {"Authorization": f"Bearer {token}"}
        console.print("[green]Got Auth Token")

    def getAccountIDs(self):
        """
        Queries Smart Account for account info. Saves Smart Account &
        Virtual Account IDs, which are required for most requests
        """
        response = self.getData(BASE_URL + SMART_ACCOUNT_URL)
        console.print("Looking up Smart Account & Virtual Account IDs...")
        accounts = json.loads(response)["accounts"]
        # Response JSON should contain all smart accounts that we have access to with
        # our credentials.
        # So we'll need to find the one we want to use & save it's ID
        for smart_account in accounts:
            if (smart_account["domain"]).lower() == (SMART_ACCOUNT).lower():
                self.smart_account_id = smart_account["account_id"]
                console.print(f"Found SA ID: {self.smart_account_id}")
                # Same goes for virtual account - Need to find which one we want &
                # save the ID
                for virtual_account in smart_account["virtual_accounts"]:
                    if virtual_account["name"] == VIRTUAL_ACCOUNT:
                        self.virtual_account_id = virtual_account["virtual_account_id"]
                        console.print(f"Found VA ID: {self.virtual_account_id}")

    def requestAuthCode(self, pid, serial, hostname):
        """
        Request offline license authorization code

        Returns Poll ID, used to query task status & retrieve license
        """
        url = BASE_URL + AUTH_REQUEST
        request_body = json.dumps(
            {
                "data": {
                    "timestamp": self.getTimestamp(),
                    "nonce": NONCE,
                    "licenses": [
                        {
                            "sudi": {
                                "udi_pid": f"{pid}",
                                "udi_serial_number": f"{serial}",
                            },
                            "hostname": f"{hostname}",
                            "keys": [
                                {
                                    "entitlement": f"{LICENSE_TAG}",
                                    "count": "1",
                                }
                            ],
                        }
                    ],
                }
            }
        )
        # This is a device-specific request, which needs certain HTTP headers
        if not self.device_headers:
            self.createDeviceHeaders(pid, serial)
        # Send Request
        console.print("Submitting license reservation request")
        response = self.postData(url, request_body, self.device_headers)
        # Return poll id, which is used to check task status & get task results
        poll_id = json.loads(response)["poll_id"]
        console.print(f"Request submitted. Poll ID: {poll_id}")
        return poll_id

    def getPollRequest(self, poll_id, poll_type):
        """
        Checks status of an existing task
        """
        url = BASE_URL + POLL_REQUEST
        request_body = json.dumps(
            {
                "data": {
                    "timestamp": f"{self.getTimestamp()}",
                    "nonce": NONCE,
                    "poll_id": poll_id,
                    "action": poll_type,
                }
            }
        )
        console.print("Checking task status...")

        # RUM/usage reports can take a few minutes to process & give us a response
        # So we'll build in a buffer here before checking task status
        if "ack" in poll_type:
            console.print(
                "\nReports can take a short while to process. Waiting 30 sec..."
            )
            time.sleep(27)
        # Loop until response is received
        attempts = 1
        while True:
            # Wait a few seconds between each attempt
            time.sleep(3)
            response = json.loads(self.postData(url, request_body, self.device_headers))
            console.print(f"Attempt # {attempts}")
            # Status OK_POLL means still working, COMPLETE means the request has finished
            if response["status"] == "COMPLETE":
                console.print("[green]Task Completed!")
                return response
            elif response["status"] == "OK_POLL":
                if response["message"] == "":
                    console.print("Task not completed yet. Waiting...")
                    attempts += 1
                else:
                    console.print("[yellow]Something went wrong")
                    console.print(f"Error: {response['message_code']}")
                    break

    def createDeviceHeaders(self, pid, serial):
        """
        Creates & saves headers that are required for device-specific requests
        """
        # For devices-pecific requests, we need to send the device PID & serial
        # in the HTTP headers - as well as the target SA/VA IDs
        self.device_headers = {
            "Content-Type": "application/json",
            "X-CSW-SMART-ACCOUNT-ID": f"{self.smart_account_id}",
            "X-CSW-VIRTUAL-ACCOUNT-ID": f"{self.virtual_account_id}",
            "X-CSW-REQUESTING-SYSTEM": json.dumps(
                {
                    "udi_pid": f"{pid}",
                    "udi_serial_number": f"{serial}",
                }
            ),
        }

    def sendUsageReport(self, report_data, pid, serial):
        """
        Generates License Usage report & sends to Smart Licensing

        Returns Poll ID, used to query task status & retrieve ACK payload
        """
        url = BASE_URL + USAGE_REPORT
        request_body = json.dumps(
            {
                "data": {
                    "timestamp": self.getTimestamp(),
                    "nonce": f"{NONCE}",
                    "reports": report_data,
                }
            }
        )
        # This is a device-specific request, which needs certain HTTP headers
        if not self.device_headers:
            self.createDeviceHeaders(pid, serial)
        # Send Request
        console.print("Submitting license usage report")
        response = json.loads(self.postData(url, request_body, self.device_headers))
        # Catch if the report upload fails. Most commonly this will happen if we
        # try to upload a duplicate report
        if response["status"] == "FAILED":
            console.print("[red]Request failed:")
            console.print(response["message"])
            return None
        # Return poll id, which is used to check task status & get task results
        poll_id = response["poll_id"]
        console.print(f"Request submitted. Poll ID: {poll_id}")
        return poll_id

    def removeDeviceLicense(self, pid, serial, hostname, remove_code):
        """
        Remove device license from Smart Licensing

        Returns Poll ID, used to query task status
        """
        url = BASE_URL + AUTH_REQUEST
        request_body = json.dumps(
            {
                "data": {
                    "timestamp": self.getTimestamp(),
                    "nonce": NONCE,
                    "licenses": [
                        {
                            "sudi": {
                                "udi_pid": f"{pid}",
                                "udi_serial_number": f"{serial}",
                            },
                            "hostname": f"{hostname}",
                            "keys": [],
                            "remove_code": f"{remove_code}",
                        }
                    ],
                }
            }
        )
        if not self.device_headers:
            self.createDeviceHeaders(pid, serial)
        # Send Request
        console.print("Submitting license removal request")
        response = self.postData(url, request_body, self.device_headers)
        # Return poll id, which is used to check task status & get task results
        poll_id = json.loads(response)["poll_id"]
        console.print(f"Request submitted. Poll ID: {poll_id}")
        return poll_id

    def getData(self, get_url, headers={}):
        """
        General function for HTTP GET requests with authentication headers

        Returns response text
        """
        headers = {**self.auth_token, **headers}
        resp = self.s.get(get_url, headers=headers, verify=False)
        if resp.status_code == 200:
            return resp.text
        if resp.status_code == 404:
            return None
        else:
            console.print("[red]Request FAILED. " + str(resp.status_code))
            console.print(resp.text)

    def postData(self, post_url, post_data, headers={}):
        """
        General function for HTTP POST requests with authentication headers & a data payload

        Returns response text
        """
        headers = {**self.auth_token, **headers}
        resp = self.s.post(post_url, headers=headers, data=post_data, verify=False)
        if resp.status_code >= 200 or resp.status_code <= 204:
            return resp.text
        else:
            console.print("[red]Request FAILED. " + str(resp.status_code))
            console.print(resp.text)
            console.print(post_data)

    def getTimestamp(self):
        """
        Returns current timestamp in milliseconds
        """
        return int(time.time() * 1000)
