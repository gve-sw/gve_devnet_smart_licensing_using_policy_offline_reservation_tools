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

import json
import os
import sys
import xml.etree.ElementTree as ET
from base64 import b64decode, decode

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel

from smartaccount import LICENSE_TAG, SmartAccount

# Load environment variables
load_dotenv()
DEVICE_SERIAL = os.getenv("DEVICE_SERIAL")
DEVICE_PID = os.getenv("DEVICE_PID")
DEVICE_HOSTNAME = os.getenv("DEVICE_HOSTNAME")
LICENSE_TAG = os.getenv("LICENSE_TAG")

console = Console()


def parseXML():
    """
    Read in XML usage report & locate HSEC license info

    Returns report payload to upload to Smart Licensing Portal
    """
    # Build base report structure
    # We'll only be uploading one device report here, but a report payload
    # contains a list of reports, so we could upload multiple devices.
    report_payloads = [{}]
    # Each payload needs device info, like PID & serial number
    sudi_info = {
        "sudi": {"udi_pid": f"{DEVICE_PID}", "udi_serial_number": f"{DEVICE_SERIAL}"}
    }
    # SUDI info is attached to report object first
    report_payloads[0] = {**sudi_info}
    # Then create a list of usage reports.
    report_payloads[0]["usage"] = []
    # Now we'll open the usage.txt file & parse the XML to assemble usage report payload
    with open("usage.txt", "r") as a:
        tree = ET.parse(a).getroot()
    # Each XML item is an individual license usage report, so we'll need to parse the actual
    # report payload from each item
    for item in tree.findall("./RUMReport"):
        usage_item = json.loads(item.text)
        payload = json.loads(usage_item["payload"])
        # Find licenses in report that match target license tag
        if payload["meta"]["entitlement_tag"] == LICENSE_TAG:
            signature = usage_item["signature"]
            # Payload attached just match EXACTLY to what we receive from the device usage report
            # So because of python/json parsing - we need to remove any spaces & escape quotes.
            # If this isn't exact, then payload signature will be invalid & report will be rejected
            escaped_payload = json.dumps(payload).replace('"', '"').replace(" ", "")
            # Add the new payload & signature info to the usage list
            report_payloads[0]["usage"].append(
                {"payload": escaped_payload, "signature": signature}
            )

    return report_payloads


def run():
    """
    Process for uploading a license usage report to Smart Licensing

    This will print out & save a file locally with the Smart License usage ACK data,
    which must be uploaded to the device
    """
    sa = SmartAccount()
    console.print()
    console.print(
        Panel.fit(
            "Parse XML usage report",
            title="Step 1",
        )
    )
    # Prompt the user to confirm the usage file has been saved locally
    console.print(
        "[bold]Please ensure the usage report is saved in this directory as: usage.txt"
    )
    input("Press Enter when file is ready.")
    report_payloads = parseXML()
    console.print(f"\nFound {len(report_payloads[0]['usage'])} items to upload.")

    console.print()
    console.print(
        Panel.fit(
            "Authenticate to Cisco SSO",
            title="Step 2",
        )
    )
    sa.getAuthToken()

    console.print()
    console.print(
        Panel.fit(
            "Locate Smart Account & Virtual Account IDs",
            title="Step 3",
        )
    )
    sa.getAccountIDs()

    console.print()
    console.print(
        Panel.fit(
            "Upload License Usage Report",
            title="Step 4",
        )
    )
    poll_id = sa.sendUsageReport(report_payloads, DEVICE_PID, DEVICE_SERIAL)
    if not poll_id:
        sys.exit(1)

    console.print()
    console.print(
        Panel.fit(
            "Check Request Status",
            title="Step 5",
        )
    )
    poll_data = sa.getPollRequest(poll_id, "acknowledgements")

    # Parse acknowledgement response
    ack_data = b64decode(
        poll_data["data"]["acknowledgements"][0]["smart_license"]
    ).decode("utf-8")
    console.print("\nLicense ACK Data:")
    console.print(f"{ack_data}", markup=False, soft_wrap=True)
    # Save to local file & print out next steps
    with open("ACK.txt", "w") as a:
        a.write(ack_data)
        console.print("\nACK saved to: [bold]ACK.txt")
    console.print(
        "\nPlease copy file to device & import with command: license smart import <bootflash|tftp>:ACK.txt"
    )


if __name__ == "__main__":
    run()
