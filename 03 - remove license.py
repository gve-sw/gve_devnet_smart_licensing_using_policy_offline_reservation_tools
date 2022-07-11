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
    Process for removing a device license reservation
    """
    # Get License removal code:
    console.print(
        "\nTo remove a device license reservation, we need a device removal code."
    )
    console.print("This can be collected from the device with the following command: ")
    console.print("[bold]router# license smart authorization return local online")
    console.print("\nPlease enter device removal code:")
    remove_code = (input("> ")).strip()
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
            "Send License Removal Request",
            title="Step 3",
        )
    )
    poll_id = sa.removeDeviceLicense(
        DEVICE_PID, DEVICE_SERIAL, DEVICE_HOSTNAME, remove_code
    )

    console.print()
    console.print(
        Panel.fit(
            "Check Request Status",
            title="Step 4",
        )
    )
    status = sa.getPollRequest(poll_id, "authorizations")

    # The removal task doesn't give us much status, except whether or not the removal failed or succeeded
    for device in status["data"]["authorizations"]:
        console.print(
            f"Device: {device['sudi']['udi_pid']} - SN: {device['sudi']['udi_serial_number']}"
        )
        if device["error_code"] == None:
            console.print(f"[green]Status: {device['status']}")
        else:
            console.print(
                f"[red]Error: {device['error_code']} - {device['status_message']}"
            )


if __name__ == "__main__":
    run()
