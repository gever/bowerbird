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
- Bowerbird part 2: Copy bowerbird.service from /usr/bowerbird into /etc/systemd/system

#### Hosting notes
Bowerbird runs as a service automatically (through bowerbird.service) on port 8080 (specified in app/bowerbird.py). Nginx runs as a web server automatically on port 80 (specified in the standard nginx configuration), passing requests through to Bowerbird (per /etc/nginx/sites-enabled/default).

### Bowerbird Server Directories
Before starting the Bowerbird server, make sure you have the following directories in the directory where bowerbird is running:
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

### Pilot information in system
Every pilot in the competition needs to have an entry in the pilot data CSV file. Currently, the only columns looked at in the CSV are:
- 'Pilot #' (unique numerical identifier for each pilot)
- 'Name' (first and last in a single field)

All of the rest of the fields will be displayed in the pilot status detail view (by clicking on a pilot tile in the main view), so we suggest the following additional (but not required) fields that will make it easier to find mobile numbers and so forth:
- 'Phone #' (whatever needs to be dialed to make the pilot's phone ring)
- 'Wing Colors'
- 'USHPA / FAI #'

## Usage
Actual usage of the system is now fully documented in HowToUse.html.
