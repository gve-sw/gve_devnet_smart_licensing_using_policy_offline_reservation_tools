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

import os
from base64 import b64decode, decode

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel

from smartaccount import SmartAccount

# Load environment variables
load_dotenv()
DEVICE_SERIAL = os.getenv("DEVICE_SERIAL")
DEVICE_PID = os.getenv("DEVICE_PID")
DEVICE_HOSTNAME = os.getenv("DEVICE_HOSTNAME")

console = Console()


def run():
    """
    Process for performing an offline reservation for a Smart License

    This will print out & save a file locally with the device license data
    """
    sa = SmartAccount()

    console.print()
    console.print(
        Panel.fit(
            "Authenticate to Cisco SSO",
            title="Step 1",
        )
    )
    sa.getAuthToken()

    console.print()
    console.print(
        Panel.fit(
            "Locate Smart Account & Virtual Account IDs",
            title="Step 2",
        )
    )
    sa.getAccountIDs()

    console.print()
    console.print(
        Panel.fit(
            "Request License Authorization Code",
            title="Step 3",
        )
    )
    poll_id = sa.requestAuthCode(DEVICE_PID, DEVICE_SERIAL, DEVICE_HOSTNAME)

    console.print()
    console.print(
        Panel.fit(
            "Check Request Status",
            title="Step 4",
        )
    )
    poll_data = sa.getPollRequest(poll_id, "authorizations")

    # Parse license response
    if poll_data["data"]["authorizations"][0]["status"] == "FAILED":
        console.print("\n[red]Request failed. Error:")
        console.print(poll_data["data"]["authorizations"][0]["status_message"])
    else:
        license_key = b64decode(
            poll_data["data"]["authorizations"][0]["smart_license"]
        ).decode("utf-8")
        console.print("\nLicense Data:")
        console.print(f"{license_key}", markup=False, soft_wrap=True)
        # Save to local file & print next steps
        with open("lic.txt", "w") as a:
            a.write(license_key)
            console.print("\nLicense saved to: [bold]lic.txt")
        console.print(
            "\nPlease copy file to device & import with command: license smart import <bootflash|tftp>:lic.txt"
        )
        console.print(
            "Then run: license smart save usage all file <bootflash|tftp>:<filename>"
        )
        console.print("And run script #02 to upload usage report.")


if __name__ == "__main__":
    run()
