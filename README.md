# bowerbird
a pilot status tracking system

## overview
- uses messages from pilots to keep track of where they are and what their status is (flying, landed OK, picked up, etc)

- status is conveyed by specific three-letter codes (FLY, LOK, PUP, SOS, ABS)

- messages can come from satellite tracking devices (such as Delorme InReach or SPOT) or via properly formatted text message.

- the system automatically responds to messages received, so pilots have a confirmation that their status has been updated.

- requires twilio to send/receive text messages.

## set up

### Hosting 
First, you need a hosting platform for Bowerbird. It is designed to be run as it's own web service, so that it is super lightweight and portable. This project contains virtually everything needed to get up-and-running on a standard Linux platform: just add internet connectivity! Note that we have been using the standard Debian distribution on a Google Cloud Platform Compute Engine VM Instance (details provided below).

Specifically, it uses:
- Python 3
- nginx (as a simple web server front-end to work around an issue with AT&T - OPTIONAL, but users may not be able to connect to bowerbird via the AT&T cellular data network using Chrome)
- tinydb (which is integrated into this project, but you should be aware that it is use)

#### Hosting details
The Google Cloud Platform (cloud.google.com) Compute Engine VM Instance configuration we have been using (without issue) is:
- Region: It doesn't seem to matter, although you might want to pick one closest to where you are
- Machine type: micro (1 shared vCPU, 0.6 GB memory, f1-micro) [the smallest option]
- Boot disk: New 10 GB standard persistent disk, with Debian GNU/Linux image on default machine type [the default]
- Firewalls: Turn on for all traffic [this is NOT the default!]
- All other options are the defaults when creating a VM Instance

#### Hosting configuration
When using Google Cloud Platform the Linux VM is set up with almost everything needed. There are just a few actions needed to complete the hosting machine configuration:

- URL: You need to set up a custom domain pointed to the VM Instance External IP. This is the URL that your users will visit to use Bowerbird. For example, we use http://bbtrack.me which is currently pointed to 104.196.127.59.
- Bowerbird: Create /usr/bowerbird, then clone this project from this repo into /usr/bowerbird using Git
- Nginx: https://docs.nginx.com/nginx/admin-guide/installing-nginx/installing-nginx-open-source/#installing-a-prebuilt-debian-package-from-the-official-nginx-repository
- Bowerbird part 2: Copy bowerbird.service from /usr/bowerbird into /etc/systemd/system (using sudo) and enable it (sudo systemctl enable bowerbird)
- Nginx part 2: Edit /etc/nginx/sites-available/default, in the server section, comment out the line "try files $uri $uri/ =404;"
and instead include the following two lines:
`proxy_pass http://localhost:8080;
include /etc/nginx/proxy_params;`
- Nginx part 3: If your server is getting hammered by bots, you might want to update /etc/nginx/sites-available/default to whitelist ONLY the valid Bowerbird pages and requests (all others will be rejected by nginx). We found this necessary since the bot hammering corrupted the json db and crashed bowerbird. A sample default file is included here (default-nginx). To refresh the config while live use `nginx -s reload`
- Be sure that both the bowerbird and nginx services are enabled and started (sudo systemctl enable bowerbird, etc)
- Restart your server (to make sure everything is really working and will continue to do so)

#### Hosting notes
Bowerbird runs as a service automatically (through bowerbird.service) on port 8080 (specified in app/bowerbird.py). Nginx runs as a web server automatically on port 80 (specified in the standard nginx configuration), passing requests through to Bowerbird (per /etc/nginx/sites-enabled/default).

If you do not want to use nginx as a proxy, then update bowerbird.service to explicitly launch bowerbird on port 80 ("app/bowerbird.py -port 80") and do not set nginx as a proxy (in /etc/nginx/sites-available/default).

Do you see "Welcome to nginx!"? You might need to restart your server after getting all the files in place.
Do you see "This site can’t be reached"? Your server might be down (or your DNS A record is misconfigured). Did you remember to do the "Bowerbird part 2" step above?
WARNING: In Google Cloud Compute Engine if you "Stop" your VM instance and you are using an ephemeral External IP address your VM instance will get a NEW External IP address when it starts up again. You can keep your ephemeral External IP address by doing a restart or reboot.

If you need to do work on your server you'll either need to use sudo for all changes, or set up a kludge (as I've done) with a 'bowerbird' group that all project participants are part of and manually set the /usr/bowerbird files to group 'bowerbird' with umask 002.

To check that the bowerbird and nginx services are properly enabled, use "sudo systemctl list-unit-files"

### Bowerbird Server Directories
Before starting the Bowerbird server, make sure you have the following directories in the directory where bowerbird is running (/usr/bowerbird):
- ./status (this is where pilot status messages are recorded)
- ./data (where you will put the pilot information and the tinydb JSON record is stored)
- ./archive (when you restart the server, this is where the previous status messages are saved)

### Twilio
Once you create your Twilio account, you will need to create a new
phone number. That number will be the one you share with pilots and competition
staff to update and check pilot status via SMS.

You will need to configure the number with a "webhook". The webhook is a URL
that is hit when a new message is received. Look in the "Phone Numbers" section
of the Twilio dashboard under Manage Numbers / Active Numbers. Scoll down to the
"Messaging" section and add the bowerbird URL (https://bowerbird.host.com/ups) to the
'A MESSAGE COMES IN' webhook. Make sure you select HTTP POST. The '/ups' on the
end of the bowerbird URL is the python code in bowerbird that knows how to parse
and respond to messages.

### SMS Forwarding
The Delorme InReach works great with Twilio (which uses a VOIP number, since it sends real SMS messages. However, SPOT can not send
messages to a VOIP number. Therefore, an actual cell phone number must be set up to receive the SPOT messages
and forward them to the Twilio number. It is recommended that the phone be used for nothing else, so that it is always on/available for forwarding incoming SPOT messages. Note that you will need to install the cell phone SIM card in a working
cell phone, and then configure an SMS forwarder to forward the incoming messages to the Twilio number. Be sure to set up
an exception, so that the SMS forwarder does NOT forward messages coming FROM the Twilio number.

### Contact information in system
There are different details about contact information for retrieves, non life threatening injuries, and SOS events that each pilot must enter into their satellite trackers.
Entering contact information into the contact info CSV file will create customized details on how to set up the SPOT and Delorme InReach for each pilot.
The contact information consists of 
- PresetIndex
  * 1 - (OK) message
  * 2 - (HELP) message
  * 3 - (Custom) Pick up or PUP message
  * SOS - Not a preset message but instead involves setting up special details in each pilot's SPOT or InReach account details
- ContactInfo
  * email
  * phone number  
    + SPOT requires knowing which provider is associated with a phone number so be sure to add that for SPOT entries. For example: `5551234567 (ATT)` or `5551237654 (Verizon)`
    + InReach wants a `+` sign at the beginning of the phone number so: `+15551234567`
- Model
  * spot
  * inreach


### Pilot information in system
Every pilot in the competition needs to have an entry in the pilot data CSV file. Currently, the only columns looked at in the CSV are:
- 'Pilot #' (unique numerical identifier for each pilot)
- 'Name' (first and last in a single field)

All of the rest of the fields will be displayed in the pilot status detail view (by clicking on a pilot tile in the main view), so we suggest the following additional (but not required) fields that will make it easier to find mobile numbers and so forth:
- 'Phone #' (whatever needs to be dialed to make the pilot's phone ring)
- 'Wing Colors'
- 'USHPA / FAI #'

## System Administration
### Load Pilot data
- Transfer pilot_list.csv to server
- Stop the server (sudo systemctl stop bowerbird)
- Make sure the new pilot_list.csv is in the data directory
- Restart the server (sudo systemctl start bowerbird)
- Do a reset (http://bbtrack.me/reset)

NOTE: The csv parser is not very robust. Review your data before upload. Currently lines without pilot numbers are not acceptable, for example.

### Reset to start the day
- Do a reset (http://bbtrack.me/reset)

NOTE: It's helpful to make a custom pilot_list.csv with the special status for each pilot for the daily reset, and potentially a second one with everyone set to "FLY" as appropriate. See HowToUse.html for more guidelines.

## Usage
Actual usage of the system is now fully documented in HowToUse.html.
