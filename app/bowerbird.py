#!/usr/bin/python
from http.server import BaseHTTPRequestHandler,HTTPServer
import threading
import signal
from socketserver import ThreadingMixIn
import os, cgi, sys, time, csv, re, pprint, socket, urllib.request, urllib.parse, urllib.error
import traceback
from string import Template
from datetime import datetime
from datetime import timedelta
from tinydb import TinyDB, Query, where

MULTITHREADED = False

# load the maps api key
try:
    from gmk import *
except:
    from SAMPLE_gmk import *
    print("WARN: using SAMPLE_gmk")

######
#
# Bowerbird 3.0
#
# note:
#   for maximum portability, this is a bare-metal solution of bowerbird.
#   not fancy, but functional. depends only on standard python libraries.
#   updated to python3 compatibility.
#   now includes tinydb (as a subdirectory) from https://github.com/msiemens/tinydb
#
# to launch (on a server):
#   python3 app/bowerbird.py
#
######

## PilotStatus = {}

# create database and table manager objects
db_file = './data/bb_database.json'
db = None
ptable = None
dtable = None
citable = None
sttable = None
def reset_db():
    global db
    global ptable
    global dtable
    global citable
    # weird naming but stable is also a word so adding one more letter
    global sttable

    db = TinyDB( db_file )
    ptable = db.table('pilots')
    dtable = db.table('drivers')
    citable = db.table('contactinfo')
    sttable = db.table('staff')
reset_db()

# find a pilot (and appropriate db reference for updates)
def get_pilot(pid):
    matches = ptable.search(where(LABEL_PID) == pid)
    if len(matches) > 0:
        return matches[0], matches
    return None, None

def get_staff(staffRole):
    matches = sttable.search(where(LABEL_ROLE) == staffRole)
    if len(matches) > 0:
        return matches[0]
    return None

# find a driver (and appropriate db reference for updates)
# TODO: driver labels need LABEL_ definitions
def get_driver(did):
    driver_letter = did[-1]
    matches = dtable.search(where('Driver#') == driver_letter)
    if len(matches) > 0:
        return matches[0], matches
    return None, None

def get_contact_info_preset(presetIndex, model):
    matches = citable.search(where(LABEL_PRESETINDEX) == presetIndex)
    # Not sure how to pass the search() function multiple where() statements
    return list(filter(lambda x: (x[LABEL_DEVICEMODEL] == model), matches))

# get just the number part of the Flymaster Live Tracker field (LABEL_TRACKER)
# TODO this is just a brute force removal of the 2 char at start of tracker number (what a hack!)
def get_tracker_number(tracker):
    if tracker:
        return tracker[2:]
    else:
        return ''

# read pilot field definitions from the external python config file
try:
    from pilot_fields import *
except:
    from SAMPLE_pilot_fields import *
    print("WARN: using SAMPLE_pilot_fields")

LABEL_DRIVER = 'Driver'

#contact info labels
LABEL_PRESETINDEX = 'PresetIndex'
LABEL_CONTACTINFO = 'ContactInfo'
LABEL_DEVICEMODEL = 'Model'

#staff labels
LABEL_ROLE = "Role"
LABEL_STAFF_NAME = "Name"
LABEL_STAFF_PHONE = "Telephone"
LABEL_STAFF_PROVIDER = "TelephoneProvider"

# status file field separator
FIELD_SEP = "\n"

# pilot data file name (try real data first, then try for the sample data included in git)
PilotDataFiles = ['./data/pilot_list.csv', './data/pilot_list-SAMPLE.csv']

# driver data file name (try real data first, then try for the sample data included in git)
DriverDataFiles = ['./data/driver_list.csv', './data/driver_list-SAMPLE.csv']

# contact info data file name (try real data first, then try for the sample data included in git)
ContactInfoDataFiles = ['./data/contact_list.csv', './data/contact_list-SAMPLE.csv']

# staff info data file name (try real data first, then try for the sample data included in git)
StaffDataFiles = ['./data/staff_list.csv', './data/staff_list-SAMPLE.csv']

# regular expressions used to parse message parts
SpotRE = re.compile( r'#(\d{1,4}) {1,}(\w\w\w)' ) # used to check to see if a well-formed SPOT message has been received
SimpleRE = re.compile( r'#{,1}(\d{1,4}) {1,}(\w\w\w)' ) # used to check to see if a well-formed non-SPOT message has been received
SpotCheckRE = re.compile( r'FRM:' ) # used to identify a poorly formed SPOT message: need to check the next line for useful part
SpotLatLonRE = re.compile( r'LL=(\d{1,3}\.\d{1,5}),[\b]?([-]?\d{1,3}.\d{1,5})', re.IGNORECASE ) # used evaluate second line of multi-line SPOT message
LatLonRE = re.compile( r'(\d{1,3}\.\d{1,6}),\ ([-]?\d{1,3}.\d{1,6})' ) # used to extract variable-precision GPS coordinate
ErrorRE = re.compile( r'ERROR' )

# regular expression used to fix phone numbers
DigitsOnlyRE = re.compile( r'[^\d.]+' )

LogFilename = "./status/bb_log.txt"
ErrorLogFilename = "./status/bb_msg_errors.txt"

# NOTE: this is assuming PDT timezone!! (currently only applied to log times, not LastResetTime)
TimeDelta = timedelta(hours=7)

# tracking the last reset time
LastResetTime = datetime.utcnow()-TimeDelta
LastResetFormat = '%a %Y-%m-%d %I:%M %p'

def timestamp():
    return str(datetime.now()-TimeDelta)

# convert URL-like strings into anchor tags
def linkURL(s):
    val = re.sub(r'(https?://\S+)', r'<a href="\1" style="color:blue">\1</a>', s)
    return val

# append a message to the log file
def log(*msg):
    try:
        f = None
        if not os.access(LogFilename, os.R_OK):
            f = open(LogFilename, 'w')
        else:
            f = open(LogFilename, "a+")
        f.write(' '.join(msg) + "\n")
        f.flush()
    except:
        print('log:', msg)

# append a message to the log file
def log_error(*msg):
    try:
        with open(ErrorLogFilename, "a+") as f:
            f.write(' '.join(msg) + "\n")
            f.flush()
    except:
        print('log_error:', msg)

# super simple html templating system
page_templates = {}

def load_templates():
    page_templates['std_page']      = Template(open('./app/std_page.html', 'r').read())
    page_templates['timer_page']    = Template(open('./app/timer_page.html', 'r').read())
    page_templates['std_tile']      = Template(open('./app/std_tile.html', 'r').read())
    page_templates['super_tile']    = Template(open('./app/super_tile.html', 'r').read())
    page_templates['std_tabletile'] = Template(open('./app/std_tabletile.html', 'r').read())
    page_templates['pilot_detail']  = Template(open('./app/pilot_detail.html', 'r').read())
    page_templates['pilot_short']   = Template(open('./app/pilot_short.html', 'r').read())
    page_templates['pilot_status']  = Template(open('./app/pilot_status.html', 'r').read())
    page_templates['pilot_help']    = Template(open('./app/pilot_help.html', 'r').read())
    page_templates['reset_confirm'] = Template(open('./app/reset_confirm.html', 'r').read())
    page_templates['nav_link']      = Template(open('./app/nav_link.html', 'r').read())
    page_templates['nav_nonlink']   = Template(open('./app/nav_nonlink.html', 'r').read())
    page_templates['nav_bar']       = Template(open('./app/nav_bar.html', 'r').read())
    page_templates['nav_bar_admin'] = Template(open('./app/nav_bar_admin.html', 'r').read())
    page_templates['ups']           = Template(open('./app/ups_manual.html', 'r').read())
    page_templates['update']        = Template(open('./app/update_status.html', 'r').read())
    page_templates['_index']        = Template(open('./index.html', 'r').read())
    page_templates['admin']         = Template(open('./admin.html', 'r').read())
    page_templates['chart']         = Template(open('./chart.html', 'r').read())
    page_templates['device_table']  = Template(open('./app/device_message_table.html', 'r').read())
    page_templates['sos_detail']    = Template(open('./app/sos_detail.html', 'r').read())

def render_template(name, stuff):
    t = page_templates[name]
    return t.safe_substitute(stuff)

# render a 'standard' header
def render_nav_header():
    return page_templates['nav_bar'].substitute()

# render an 'admin' header
def render_nav_admin_header():
    return page_templates['nav_bar_admin'].substitute()

# append a status update to a pilot's status file
def update_status_file(pid, sms):
    with open('./status/' + str(pid), 'a') as sfile:
        sfile.write( sms + FIELD_SEP + timestamp() + "\n")

# define which status tags are displayed on a given view
def display_def(display, alt=None): # little helper func
    # if display is false, and alt is set, the alt text is shown
    # if display is false, and alt is None, the previous status is shown
    # if display is true, the current status is shown
    # pilot: if the status is not listed in the filter, it is NOT shown
    # retrieve: if the status is not listed in the filter, it is NOT shown (*only* show LOK, AID, GOL, DR*)
    # admin: if the status is not listed in the filter, it is shown
    class obj:
        def __init__(self, **args):
            for i in args:
                self.__setattr__(i, args[i])
    return obj(display=display, alt=alt)
# NOTE: filter_pv is not currently used in pilot overview
filter_pv = { # pilot view: show what the pilots need to see
        'LOK': display_def(True),
        'PUP': display_def(True),
        'AID': display_def(True),
        'MSG': display_def(True),
        'FLY': display_def(True),
        'FIN': display_def(True),
        'FNL': display_def(True),
        'TST': display_def(True),
        'NOT': display_def(False, ''),
        }
filter_rv = { # retrieve view: show what the retrieve coordinator needs to see
        'LOK': display_def(True),
        'PUP': display_def(True),
        'AID': display_def(True),
        'MSG': display_def(True),
        'FLY': display_def(False, ''),
        'DNF': display_def(False, ''),
        'GOL': display_def(True),
        'LZ1': display_def(True),
        'LZ2': display_def(True),
        'NOT': display_def(False, ''),
        'TST': display_def(False, ''), # adding a bunch of False cases since default not working
        'FIN': display_def(False, ''),
        'FNL': display_def(False, ''),
        'URL': display_def(False, ''),
        'GPS': display_def(False, ''),
        }
filter_av = { # admin view: show all current status
        'NOT': display_def(False, ''),
        }

def get_last_pilot_status(pilot):
    if not 'status_history' in pilot:
        return ''
    else:
        if len(pilot['status_history']) > 1:
            return pilot['status_history'][-2]
        else:
            return ''

def filter_status(pilot, flt):
    status = pilot[LABEL_STATUS]
    if status in flt:
        f = flt[status]
        if f.display:
            return (True, status)
        else:
            return (True, f.alt)
    return (True, status)

# render a pilot status overview
def handle_pilot_overview(noun):
    tiles = ""
    # TODO.txt: how easy would it be to create sections based on either number range or event field in pilot db?
    # (so Open Race would be a separate table from Sprint Race which is separate from SuperClinic, but on same page)
    for p in sorted(ptable.all(), key=lambda i: int(i[LABEL_PID])):
        # don't display NOT label
        # disabled filtering: processed, status = filter_status(p, filter_pv)   # p[LABEL_STATUS]
        processed = True
        status = p[LABEL_STATUS]
        tracker = p[LABEL_TRACKER]
        tracker_number = get_tracker_number(tracker)
        if not processed:
            status = ''
        tiles += render_template('std_tile', {'pilot_id':p[LABEL_PID], 'pilot_status':status, 'tracker_number':tracker_number})
    pg = render_template('std_page', {'refresh':0, 'content':tiles, 'nav':'', 'adminnav':'', 'preamble':'', 'last_reset':LastResetTime.strftime(LastResetFormat)})
    return pg

# render admin view of pilot status (like handle_pilot_overview, but with a different status filter
# and pilot detail seen when clicking on tile)
def handle_admin_overview(noun):
    tiles = ""
    # TODO.txt: how easy would it be to create sections based on either number range or event field in pilot db?
    # (so Open Race would be a separate table from Sprint Race which is separate from SuperClinic), but on same page
    for p in sorted(ptable.all(), key=lambda i: int(i[LABEL_PID])):
        # don't display NOT label
        processed, status = filter_status(p, filter_av)   # p[LABEL_STATUS]
        tracker_number = get_tracker_number(p[LABEL_TRACKER])

        tiles += render_template('super_tile', {'pilot_id':p[LABEL_PID], 'pilot_status':status, 'tracker_number':tracker_number})
    nav = render_nav_header()
    adminnav = render_nav_admin_header()
    preamble = 'Clicking on a tile will reveal all known info about that pilot.'
    pg = render_template('std_page', {'title':'Admin', 'refresh':1, 'content':tiles, 'nav':nav, 'adminnav':adminnav, 'preamble':preamble, 'last_reset':LastResetTime.strftime(LastResetFormat)})
    return pg

# render retrieve view of pilot status (like handle_pilot_overview, but with a different status filter
# and the display of the driver info status field INSTEAD of pilot_info - if assigned)
def handle_retrieve_overview(noun):
    tiles = ""
    # TODO.txt: how easy would it be to create sections based on either number range or event field in pilot db?
    # (so Open Race would be a separate table from Sprint Race which is separate from SuperClinic), but on same page
    for p in sorted(ptable.all(), key=lambda i: int(i[LABEL_PID])):
        # filter the status by the retrieve view filter
        processed, status = filter_status(p, filter_rv)   # p[LABEL_STATUS]

        # if driver assigned, show that instead pilot status
        if status in ['PUP', 'LOK', 'GOL', 'LZ1', 'LZ2', 'SPOT']:
            driver_status = p[LABEL_DRIVER]
            # only use it if it's actually set
            if driver_status and (driver_status != 'DR0'):
                status = driver_status
            elif (driver_status == 'DR0' or driver_status == None) and (status == 'PUP'):
                status = ''
            # if DR0 and not PUP, just use real status as status (since DR0 is our only way to "unset" a driver)

        # render the tile
        tracker_number = get_tracker_number(p[LABEL_TRACKER])
        tiles += render_template('super_tile', {'pilot_id':p[LABEL_PID], 'pilot_status':status, 'tracker_number':tracker_number})
    nav = render_nav_header()
    adminnav = render_nav_admin_header()
    preamble = 'Clicking on a tile will reveal details about that pilot.'
    pg = render_template('std_page', {'title':'Retrieve', 'refresh':1, 'content':tiles, 'nav':nav, 'adminnav':adminnav, 'preamble':preamble, 'last_reset':LastResetTime.strftime(LastResetFormat)})
    return pg

def contact_info_help_row(preset_label, send_message, recipient_list):
    recipient_contact_info = '<ul class="bare">'

    for recipient in recipient_list:
        recipient_contact_info += "<li>{}</li>".format(recipient["ContactInfo"])
    recipient_contact_info += '</ul>'

    row = "<tr><td>{0}</td><td>{1}</td><td>{2}</td></tr>\n".format(preset_label, send_message, recipient_contact_info)

    return row


# simple list of all pilots, currently in alphabetical order (Last Name)
# TODO.txt: make the list sortable by headers
def handle_listview( noun ):
    # this is pretty ugly...
    table = '<table>'

    # from a pid, pull a name
    def pid_name( pid ):
        p = get_pilot( pid )
        return p['FirstName'] + p['LastName']

    # not worrying about performance here...
    for p in sorted(ptable.all(), key=lambda i: i[LABEL_LNAME]):
        tracker_number = p[LABEL_TRACKER] if p[LABEL_TRACKER] else ''
        table += '<tr><td>' + p['FirstName'] + '</td><td>' + p['LastName'] + '</td>' + render_template('std_tabletile', {'pilot_id':p[LABEL_PID], 'pilot_status':p[LABEL_STATUS]}) + '<td>' + tracker_number + '</td>' + "</tr>\n"
    table += '</table>'
    nav = render_nav_header()
    pg = render_template('std_page', {'title':'List', 'refresh':1, 'content':table, 'nav':nav, 'preamble':'', 'adminnav':'', 'last_reset':LastResetTime.strftime(LastResetFormat)})
    return pg

# based on handle_listview: shows list of drivers, instead of pilots.
# instead of pilot status, for each driver show which pilots are currently assigned to them
# TODO.txt: make the list sortable by headers
def handle_driverview( noun ):
    # this is pretty ugly...
    # not worrying about performance here...
    table = '<table class="driverlist">'
    table += '<tr><td class="driverlist">Van#</td><td class="driverlist">ID</td><td class="driverlist">Max</td><td class="driverlist">Name</td><td class="driverlist">Rig</td><td class="driverlist">Tracker</td><td class="driverlist">Phone</td><td class="driverlist">Status</td><td class="driverlist">Pilots Assigned</td></tr>'
    for d in sorted(dtable.all(), key=lambda d: d['Driver#']):
        table += '<tr class="driverlist">'
        # find all the pilots assigned to this driver
        plist = ""
        for p in ptable.all():
            if (LABEL_DRIVER in p) and p[LABEL_DRIVER]:
                if p[LABEL_DRIVER].startswith('DR'+d['Driver#']):
                    # plist += p[LABEL_PID] + " "
                    tracker_number = get_tracker_number(p[LABEL_TRACKER])
                    status = p[LABEL_STATUS] if p[LABEL_STATUS] else 'NOT'
                    plist += render_template('std_tile', {'pilot_id':p[LABEL_PID], 'pilot_status':status, 'tracker_number':tracker_number})
        # TODO.txt: make driver # clickable (to get full status details like pilotview)
        table += '<td class="drivernum">{}</td><td id="status_DR{}" class="drivernum">{}</td><td class="driverlist">{}</td><td class="driverlist">{}</td><td class="driverlist">{}</td><td class="driverlist">{}</td><td class="driverlist">{}</td><td class="driverlist">{}</td><td class="driverlist">{}</td>'.format(d['Van#'],d['Driver#'], d['Driver#'], d['MaxPilots'], d['FirstName'], d['RigName'], d['Tracker'],d['Telephone'], d[LABEL_STATUS], plist)
        # table += '<tr><td>'+d['Driver#']+'</td><td>' + d['FirstName'] + '</td><td>' + d['LastName'] + '</td>' + "</tr>\n"
        table += '</tr>'
    table += '</table>'
    nav = render_nav_header()
    adminnav = render_nav_admin_header()
    pg = render_template('std_page', {'title':'Drivers', 'refresh':1, 'content':table, 'nav':nav, 'preamble':'', 'adminnav':adminnav, 'last_reset':LastResetTime.strftime(LastResetFormat)})
    return pg

# display all message logs
def handle_logs(noun):
    contents = None
    with open(LogFilename, "r") as f:
        contents = f.read()
    navr = render_nav_header()
    adminnavr = render_nav_admin_header()
    preamble = 'Logs are helpful if a message appears to have been sent but wasn\'t properly attributed or interpreted. You might find that the message was sent using the wrong pilot number or an unrecognizable status.'
    pg = render_template('std_page', dict(title='Logs', refresh=1, content='<pre>' + contents + '</pre>', nav=navr, adminnav=adminnavr, preamble=preamble, last_reset=LastResetTime.strftime(LastResetFormat)))
    return pg

def handle_assign_random_location(noun):
    import random

    scale = 1.5
    launch_lat = 47.804345
    launch_lon = -120.038548
    for p in ptable.all():
        chg = { LABEL_LAT:launch_lat + (random.random() * scale) - (scale/2.0),
                LABEL_LON:launch_lon + (random.random() * scale) - (scale/2.0) }
        ptable.update(chg, where(LABEL_PID) == p[LABEL_PID])
    return "ok."

def handle_map(noun):
    import json
    import random
    pins = []

    scale = 0.0005
    def jitter(v):
        return v + (random.random() * scale) - (scale/2.0)

    # TODO: handle various noun commands/filters, e.g. 'drivers', or 'LOK'
    if not noun:
        noun = 'all'

    avg_lat = 0.0
    avg_lon = 0.0
    count = 0
    pg = ""
    if noun == 'all':
        for p in ptable.all():
            p_lat = float(p[LABEL_LAT])
            p_lon = float(p[LABEL_LON])
            p_color = 'yellow'
            p_status = p[LABEL_STATUS]

            if p_status == 'PUP':
                p_color = 'green'
            elif p_status == 'AID':
                p_color = 'pink'
            if p[LABEL_DRIVER] and p[LABEL_DRIVER] != 'DR0':
                p_color = 'purple'

            # no lat/lon? you don't show up on the map
            if p_lat == 0.0 or p_lon == 0.0:
                continue

            # average out the lat/lon to find the center of the cluster of pins
            count = count + 1
            avg_lat += float(p_lat)
            avg_lon += float(p_lon)

            rec = {'id':p[LABEL_PID], 'lat':jitter(p_lat), 'lon':jitter(p_lon), 'status':p_status, 'color':p_color}
            pins.append( rec )
        avg_lat = avg_lat / count
        avg_lon = avg_lon / count
        pg = render_template('chart', dict(data=json.dumps(pins), lat=avg_lat, lon=avg_lon, MAP_API_KEY=MAP_API_KEY) )
    return pg

# display all message errors (subset of logs)
def handle_error_logs(noun):
    contents = None
    with open(ErrorLogFilename, "r") as f:
        contents = f.read()
    navr = render_nav_header()
    adminnavr = render_nav_admin_header()
    preamble = 'Errors are only those log entries that were not successfully processed. These are the most important items to review regularly. Often these have missing or unknown pilot numbers, or incorrectly formatted messages.'
    pg = render_template('std_page', dict(title='Errors', refresh=1, content='<pre>' + contents + '</pre>', nav=navr, adminnav=adminnavr, preamble=preamble, last_reset=LastResetTime.strftime(LastResetFormat)))
    return pg

def check_for(d, key):
    return d[key] if key in d else ''

# translate a row from the csv into a pilot status record
# TODO.txt: abstract the pilot record fields from the csv column headers
def parse_pilot_record(header, row):
    rec = {}
    rec[LABEL_TRACKER] = ''
    rec[LABEL_DRIVER] = None
    for i in range( len( header ) ):
        clean = header[i].replace(" ", "") # strip out spaces
        if clean == 'Status' or clean == 'status' or clean == 'STATUS':
            clean = LABEL_STATUS # need to have a known, exact value for the status index
        rec[clean] = row[i]
    rec[LABEL_PID] = rec[LABEL_PNUM]
    rec[LABEL_LAT] = 0.0    #
    rec[LABEL_LON] = 0.0
    try:
        if (rec[LABEL_STATUS] is None) or (rec[LABEL_STATUS] == ''):
            rec[LABEL_STATUS] = 'NOT'   # set current status only if it is NOT explicitly set via pilot_list.csv
    except KeyError:
        rec[LABEL_STATUS] = 'NOT' # if column is completely missing from pilot_list.csv
    rec[LABEL_EVENT] = rec[LABEL_EVENT].replace(" ","") # strip interior spaces

    # pilot status record field names must correspond to those in pilot_fields.py!!
    rec['LABEL_PNUM'] = check_for(rec,LABEL_PNUM)
    rec['LABEL_PID'] = check_for(rec,LABEL_PID)
    rec['LABEL_STATUS'] = check_for(rec,LABEL_STATUS)
    rec['LABEL_FNAME'] = check_for(rec,LABEL_FNAME)
    rec['LABEL_LNAME'] = check_for(rec,LABEL_LNAME)
    rec['LABEL_PHONE'] = check_for(rec,LABEL_PHONE)
    rec['LABEL_EVENT'] = check_for(rec,LABEL_EVENT)
    rec['LABEL_COUNTRY'] = check_for(rec,LABEL_COUNTRY)
    rec['LABEL_CITY'] = check_for(rec,LABEL_CITY)
    rec['LABEL_STATE'] = check_for(rec,LABEL_STATE)
    rec['LABEL_EMAIL'] = check_for(rec,LABEL_EMAIL)
    rec['LABEL_FAI'] = check_for(rec,LABEL_FAI)
    rec['LABEL_DOB'] = check_for(rec,LABEL_DOB)
    rec['LABEL_GLIDER_MFG'] = check_for(rec,LABEL_GLIDER_MFG)
    rec['LABEL_GLIDER_MODEL'] = check_for(rec,LABEL_GLIDER_MODEL)
    rec['LABEL_GLIDER_COLORS'] = check_for(rec,LABEL_GLIDER_COLORS)
    rec['LABEL_GLIDER_RATING'] = check_for(rec,LABEL_GLIDER_RATING)
    rec['LABEL_SPONSOR'] = check_for(rec,LABEL_SPONSOR)
    rec['LABEL_ISPAID'] = check_for(rec,LABEL_ISPAID)
    rec['LABEL_URL'] = check_for(rec,LABEL_URL)
    rec['LABEL_TRACKER'] = check_for(rec,LABEL_TRACKER)

    return rec

def parse_driver_record(header, row):
    rec = {}
    for i in range( len( header ) ):
        clean = header[i].replace(" ", "") # strip out spaces
        rec[clean] = row[i]
    rec[LABEL_STATUS] = ''
    rec[LABEL_LAT] = 0.0    #
    rec[LABEL_LON] = 0.0
    return rec

def parse_contact_info_record(header, row):
    rec = {}
    for i in range( len( header ) ):
        clean = header[i].replace(" ", "") # strip out spaces
        rec[clean] = row[i]
    return rec

def parse_staff_record(header, row):
    rec = {}
    for i in range ( len( header ) ):
        clean = header[i].replace(" ", "") # strip out spaces
        rec[clean] = row[i]
    return rec

# load a csv file into a database table using a special parsing function
def load_csv_into( table, filename, record_parser_func ):
    count = 0
    with open(filename, 'r') as csvfile:
        header_row = None
        csv_r = csv.reader(csvfile)
        for row in csv_r:
            if header_row == None:
                # save the first row for column names
                header_row = row
            else:
                # save this pilot in the server-side pilot status 'database'
                try:
                    pstat = record_parser_func(header_row, row)
                    table.insert(pstat)
                except:
                    print("Unexpected error:", sys.exc_info()[0])
                    print("Unexpected error:", sys.exc_info()[1])
                    print("count", count, "row='%s'" % row)
                    return
            count += 1
    log("loaded", count, "records into", table.name)

def handle_reset(noun):
    resp = "<pre>"
    resp += "handling reset...\n"
    LastResetTime = datetime.today()

    # rename status directory to archive/status-<timestamp>
    if os.access("./status", os.R_OK):
        new_name = "./archive/status-" + str(int(time.time()))
        resp += "backing up current status to " + new_name + "\n"
        os.rename( "./status", new_name )
    os.mkdir("./status")

    # save the current database contents, start fresh
    # db.storage.write()
    if os.access( db_file, os.R_OK ):
        new_name = './archive/db_archive-' + str(int(time.time()))
        resp += 'backing up database to ' + new_name + "\n"
        os.rename( db_file, new_name )
    reset_db()

    # initialize the database from the CSV
    # load the pilot records
    df = PilotDataFiles[1] # default to the sample data
    if os.path.isfile( PilotDataFiles[0] ):
        df = PilotDataFiles[0]
    load_csv_into( ptable, df, parse_pilot_record )

    # load the driver records
    df = DriverDataFiles[1]
    if os.path.isfile( DriverDataFiles[0] ):
        df = DriverDataFiles[0]
    load_csv_into( dtable, df, parse_driver_record )

    # load the contact info records
    df = ContactInfoDataFiles[1]
    if os.path.isfile( ContactInfoDataFiles[0] ):
        df = ContactInfoDataFiles[0]
    load_csv_into( citable, df, parse_contact_info_record )

    # load the staff records
    df = StaffDataFiles[1]
    if os.path.isfile( StaffDataFiles[0] ):
        df = StaffDataFiles[0]
    load_csv_into( sttable, df, parse_staff_record )


    resp += "\n\n" + "<p><a href='/'>Return to Overview</a></p>"
    resp += "</pre>"
    return resp

def handle_reload():
    # TODO.txt: verify that database is "live"
    return "handling reload"

def twillio_response(msg):
    resp = """<?xml version="1.0" encoding="UTF-8"?><Response><Message>
    <Body>%s</Body></Message></Response>""" % msg
    return resp

# the global database write lock to avoid simultaneous writes
# dblock = threading.Lock()
def protected_db_update(table, ref):
    if not MULTITHREADED:
        table.write_back( ref )
    else:
        try:
            dblock.acquire()
            table.write_back( ref )
        finally:
            dblock.release()

# parse a received SMS message
def parse_sms(sms):
    match = None
    ll_match = None

    # is this a driver assignment message? look for (approx) ^DR[A..I]\b[1..9][0..9][0..9]
    if sms.startswith('DR'):
        # it's a driver assignment
        parts = sms.split(' ')
        driver_id = parts[0]
        pilot, dbref = get_pilot(parts[1])
        if pilot:
            # this is the driver for this pilot
            pilot[LABEL_DRIVER] = driver_id

            # ptable.write_back( dbref )
            protected_db_update( ptable, dbref )

            log( "Assigned %s to %s %s" % (driver_id, pilot[LABEL_PID], pilot[LABEL_FNAME]) )
            return True
        else:
            # let's assume it's a driver status message
            # TODO: pull out lat/lon... like how pilots are parsed
            driver, dbref = get_driver(driver_id)
            if driver:
                driver[LABEL_STATUS] = parts[1]

                # dtable.write_back( dbref )
                protected_db_update( dtable, dbref )

                log( "Driver %s status %s" % (driver_id, driver[LABEL_STATUS]))
                return True
            else:
                log( "Problem updating driver status: %s" % (sms) )
                log_error( "Problem updating driver status: %s" % (sms) )
                return False

    if re.search( SpotCheckRE, sms ):
        # SPOT message
        match = re.search( SpotRE, sms )
    else:
        # check if valid message format
        match = re.search( SimpleRE, sms )

    if match != None:
        # see if we can find something that looks like a lat/lon in the message...
        ll_match = re.search( LatLonRE, sms )
        if not ll_match:
            ll_match = re.search( SpotLatLonRE, sms) # multi-line SPOT messages need special handling

        try:
            pid = match.group(1)
            pilot, dbref = get_pilot(pid)
            if pilot:
                code = match.group(2).upper()

                # TODO.txt: got a pilot and a code, check for pilot first or last name in sms

                # update the status field
                pilot[LABEL_STATUS] = code

                # update lat/lon if we got them
                if ll_match:
                    pilot[LABEL_LAT] = ll_match.groups()[0]
                    pilot[LABEL_LON] = ll_match.groups()[1]

                # save the raw message (in the pilot record)
                if not 'history' in pilot:
                    pilot['history'] = []
                pilot['history'].append(sms)

                # keep a list of previous statuses
                if not 'status_history' in pilot:
                    pilot['status_history'] = []
                pilot['status_history'].append(code)

                # save to the db
                # ptable.write_back( dbref )
                protected_db_update( ptable, dbref )

                # save to the status text file
                update_status_file(pid, sms)
                return True
            else:
                log( "Unknown pilot id:" + str(pid) )
                return False
        except Exception as e:
            # print("parse_sms: unusable match on '%s'" % sms)
            import traceback
            log( "Unusable match on '%s'" % sms)
            log( "Exception details: %s" % sys.exc_info()[1] )
            log( "Exception details: %s" % traceback.print_tb(sys.exc_info()[2]) )
            return False
    else:
        # print("parse_sms: unable to parse '%s'" % sms)
        log( "Unable to parse '%s'" % sms )
        return False

    return True

# reset confirmation handling (/reset)
def handle_reset_confirm(noun):
    # 911 this probably isn't the right way to do this...
    # TODO.txt move all the HTML out into a template
    data = '<pre>Warning: this will reset the system for a new day of competition, the current status and message history of each pilot will be archived and set back to defaults.<p>Do you wish to continue? <a href="/reset-request">Absolutely</a> // <a href="/admin.html">Nope</a></pre>'
    #data = render_template('reset_confirm', {'unused':'nothing'})
    pg = render_template('std_page', {'refresh':0, 'content':data, 'nav':'', 'adminnav':'', 'preamble':'', 'last_reset':LastResetTime.strftime(LastResetFormat)})
    return pg

# basic category ("Event") overview page
def handle_categoryview(category):
    tiles = ""
    # TODO.txt - this requires the category ("Event") to have no spaces so it can be specified in the URL
    # NOTE: nav will be hard-coded since it's easier for people that way
    if category:
        preamble = '<h2>Event/Type: ' + category + '</h2>'
        for p in sorted(ptable.all(), key=lambda i: int(i[LABEL_PID])):
            # filter for only those where Event = category that was passed in
            if p['Event'] != category:
                continue

            # don't display NOT label
            pstat = p[LABEL_STATUS]
            if 'NOT' in pstat:
                pstat = ''
            tracker_number = get_tracker_number(p[LABEL_TRACKER])
            tiles += render_template('std_tile', {'pilot_id':p[LABEL_PID], 'pilot_status':pstat, 'tracker_number':tracker_number})
    else:
        preamble = '<h3>You need to specify the Event (type) as defined in the CSV:<br/> http://bbtrack.me/type/Open</h3>'

    nav = render_nav_header()
    pg = render_template('std_page', {'title':category, 'refresh':1, 'content':tiles, 'nav':nav, 'adminnav':'', 'preamble':preamble, 'last_reset':LastResetTime.strftime(LastResetFormat)})
    return pg

# basic pilotview page
def handle_pilotview(noun):
    pid = noun
    pilot_details, dbref = get_pilot(pid)
    proxy = pilot_details.copy()    # make a copy because the pilot_details object is a db thing
    proxy['MAP_API_KEY'] = MAP_API_KEY  # tuck in the maps api key
    pilot_info = render_template('pilot_detail', proxy)
    proxy = None # make sure our temp dict gets freed up

    # append the pilot log contents
    try:
        with open('./status/' + str(pid), 'r') as sfile:
            pilot_info += '<pre>' + sfile.read() + '</pre>'
    except FileNotFoundError:
        pilot_info += '<pre>(no status updates)</pre>'

    nav = render_nav_header()
    pg = render_template('std_page', {'title':pid, 'refresh':0, 'content':pilot_info, 'nav':nav, 'adminnav':'', 'preamble':'', 'last_reset':LastResetTime.strftime(LastResetFormat)})
    return pg


# beginnings of pilotadmin page
def handle_pilotadmin(noun):
    pid = noun
    pilot_details, dbref = get_pilot(pid)
    pilot_info = render_template('pilot_detail', pilot_details)
    # append the pilot log contents
    try:
        with open('./status/' + str(pid), 'r') as sfile:
            pilot_info += '<pre>' + sfile.read() + '</pre>'
    except FileNotFoundError:
        pilot_info += '<pre>(no status updates)</pre>'

    # show 'em everything we've got on the pilot
    pilot_info += '<pre>%s</pre>' % pprint.pformat(pilot_details) # print everything we got!

    nav = render_nav_header()
    adminnav = render_nav_admin_header()
    pg = render_template('std_page', {'title':pid, 'refresh':0, 'content':pilot_info, 'nav':nav, 'adminnav':adminnav, 'preamble':'', 'last_reset':LastResetTime.strftime(LastResetFormat)})
    return pg

# For now this is a partial view that's being embedded within a page that wants status
def handle_pilotstatus(noun):
    pid = noun
    pilot_details, dbref = get_pilot(pid)

    history_formatted = ""
    sep = "<br />"
    if 'history' in pilot_details:
        log('starting list of history')
        history_formatted = sep.join(pilot_details["history"])
    else:
        history_formatted = '(no status updates)'

    pg = render_template('pilot_status', {"PilotStatus": history_formatted})
    return pg

def handle_pilothelp(noun):
    pid = noun
    pilot_details, dbref = get_pilot(pid)
    pilot_info = render_template('pilot_short', pilot_details)
    nav = render_nav_header()

    pilot_name = '{} {}'.format(pilot_details[LABEL_FNAME], pilot_details[LABEL_LNAME])
    pilot_id = pilot_details[LABEL_PID]
    pilot_phone = pilot_details[LABEL_PHONE]
    pilot_email = pilot_details[LABEL_EMAIL]

    pilot_help_details = {}
    pilot_help_details["PilotInfo"] = pilot_info
    pilot_help_details[LABEL_PID] = pilot_id
    pilot_help_details["nav"] = nav
    pilot_sos_info = "Pilot #{} {}, Ph {}".format(pilot_id, pilot_name, pilot_phone)

    safety_director = get_staff("SafetyDirector")
    meet_organizer = get_staff("MeetOrganizer")

    # TODO: Figure out where to put information related to the competition
    location_name = "Woodrat Mtn, Ruch, OR USA"

    pilot_help_details["SosSection"] = render_template('sos_detail', {"PilotInfo": pilot_sos_info,
        "SafetyDirector": safety_director[LABEL_STAFF_NAME], "SafetyDirectorPhone": safety_director[LABEL_STAFF_PHONE],
        "SafetyDirectorPhoneProvider": safety_director[LABEL_STAFF_PROVIDER],
        "MeetOrganizer": meet_organizer[LABEL_STAFF_NAME], "MeetOrganizerPhone": meet_organizer[LABEL_STAFF_PHONE],
        "MeetOrganizerPhoneProvider": meet_organizer[LABEL_STAFF_PROVIDER],
        "Location": location_name
        })

    def phone_number_cleaner(pn):
      # look for "+1" at beginning of phone number and delete it so SPOT message configuration works
      # note that international numbers are on their own - SPOT probably can't send to them anyway....
      if pn.startswith('+1'):
        pn = pn[2:]
        pn = pn + ' (Your Provider)'
      elif pn.startswith('1'):
        pn = pn[1:]
        pn = pn + ' (Your Provider)'
      else:
        pn = pn[0:]
        pn = pn + ' (Your Provider)'
      return pn

    def phone_number_fixer(pn):
      # first remove any non-numeric characters (will this strip a + at the start? maybe so....)

      #log("pn start:", pn)
      pn_digits = re.sub( DigitsOnlyRE, '', pn )
      #log("pn_digits after RE:", pn_digits)

      # confirm there should be a "+1" at beginning of phone number for Inreach
      # note that international numbers are on their own - they should what to do ....
      if pn_digits.startswith('+1'):
        pn_digits = pn_digits
      elif pn_digits.startswith('1'):
        pn_digits = '+' + pn_digits
      else:
        # we are assuming US
        pn_digits = '+1' + pn_digits
      return pn_digits

    pilot_phone_cleaned = phone_number_fixer(pilot_phone)
    pilot_contact_info_inreach = [dict(ContactInfo=pilot_email), dict(ContactInfo=pilot_phone_cleaned)]
    pilot_contact_info_spot = [dict(ContactInfo=pilot_email), dict(ContactInfo=phone_number_cleaner(pilot_phone_cleaned))]

    # get all info for preset 1
    preset_one_label_inreach = "1 (LOK)"
    preset_one_label_spot = "Check-in/OK"
    preset_one_message = "#{} LOK {} {}".format(pilot_id, pilot_name, pilot_phone)
    preset_one_contact_info_inreach = get_contact_info_preset('1', 'inreach')
    preset_one_contact_info_inreach.extend(pilot_contact_info_inreach)
    preset_one_contact_info_spot = get_contact_info_preset('1', 'spot')
    preset_one_contact_info_spot.extend(pilot_contact_info_spot)
    preset_one_inreach = contact_info_help_row(preset_one_label_inreach, preset_one_message, preset_one_contact_info_inreach)
    preset_one_spot = contact_info_help_row(preset_one_label_spot, preset_one_message, preset_one_contact_info_spot)

    # get all info for preset 2
    preset_two_label_inreach = "2 (AID)"
    preset_two_label_spot = "HELP"
    preset_two_message = "#{} AID {} {} requires assistance".format(pilot_id, pilot_name, pilot_phone)
    preset_two_contact_info_inreach = get_contact_info_preset('2', 'inreach')
    preset_two_contact_info_inreach.extend(pilot_contact_info_inreach)
    preset_two_contact_info_spot = get_contact_info_preset('2', 'spot')
    preset_two_contact_info_spot.extend(pilot_contact_info_spot)
    preset_two_inreach = contact_info_help_row(preset_two_label_inreach, preset_two_message, preset_two_contact_info_inreach)
    preset_two_spot = contact_info_help_row(preset_two_label_spot, preset_two_message, preset_two_contact_info_spot)

    # get all info for preset 3
    preset_three_label_inreach = "3 (PUP)"
    preset_three_label_spot = "Custom"
    preset_three_message = "#{} PUP {} {} has a ride".format(pilot_id, pilot_name, pilot_phone)
    preset_three_contact_info_inreach = get_contact_info_preset('3', 'inreach')
    preset_three_contact_info_inreach.extend(pilot_contact_info_inreach)
    preset_three_contact_info_spot = get_contact_info_preset('3', 'spot')
    preset_three_contact_info_spot.extend(pilot_contact_info_spot)
    preset_three_inreach = contact_info_help_row(preset_three_label_inreach, preset_three_message, preset_three_contact_info_inreach)
    preset_three_spot = contact_info_help_row(preset_three_label_spot, preset_three_message, preset_three_contact_info_spot)

    pilot_help_details["InreachTable"] = render_template('device_table', {'Rows': preset_one_inreach + preset_two_inreach + preset_three_inreach})
    pilot_help_details["SpotTable"] = render_template('device_table', {'Rows': preset_one_spot + preset_two_spot + preset_three_spot})
    pg = render_template('pilot_help', pilot_help_details)
    return pg

# testing interface for status updates (emulates twilio)
def handle_ups(noun):
    adminnav = render_nav_admin_header()
    return render_template('ups', {'nav':adminnav})

# web interface for updating pilot status and driver assignments
def handle_web_update(feedback):
    nav = render_nav_header()
    adminnav = render_nav_admin_header()
    return render_template('update', {'nav':nav, 'adminnav':adminnav, 'feedback':feedback})

# alt path to admin (since removing from navigation: security through obscurity)
def handle_admin(noun):
    nav = render_nav_header()
    adminnav = render_nav_admin_header()
    return render_template('admin', {'nav':nav, 'adminnav':adminnav})

# render the default home page
def handle_index(noun):
    nav = render_nav_header()
    return render_template('_index', {'nav':nav})

# map a GET request path to a handler (that produces HTML)
request_map = {
    'overview' : handle_pilot_overview,
    'enchilada' : handle_admin_overview,
    'retrieve' : handle_retrieve_overview,
    'logs' : handle_logs,
    'errors' : handle_error_logs,
    'reset' : handle_reset_confirm,
    'reset-request' : handle_reset,
    'pilotview' : handle_pilotview,
    'pilot' : handle_pilotview,
    'pilothelp' : handle_pilothelp,
    'pilotadmin' : handle_pilotadmin,
    'pilotstatus' : handle_pilotstatus,
    'categoryview' : handle_categoryview,
    'type' : handle_categoryview,
    'list' : handle_listview,
    'drivers' : handle_driverview,
    'ups' : handle_ups, # remember: GET and POST are different chunks of code
    'update' : handle_web_update, # remember: GET and POST are different chunks of code
    'admin' : handle_admin,
    'map' : handle_map,
    'randomize' : handle_assign_random_location,
    '_index' : handle_index,
}

#
# the server
#
static_pages = {}
class myHandler(BaseHTTPRequestHandler):
    # handler for GET requests
    def do_GET(self):
        sendReply = False
        if self.path=="/":              # no path specified, give them index.html
            self.path = "./index.html"  # TODO.txt: fix, kind of a no-no to change the request path in place

        # determine mimetype for static assets
        if self.path.endswith(".html"):
            sendReply = False
            if not self.path.startswith('.'):
                self.path = '.' + self.path
            if not self.path in static_pages:   # TODO.txt: this is pretty hacky too...
                static_pages[self.path] = Template(open(self.path, 'r').read())
            t = static_pages[self.path]
            nav = render_nav_header()
            adminnav = render_nav_admin_header()
            pg = t.safe_substitute({'nav':nav,'adminnav':adminnav})
            mimetype='text/html'
            self.send_response(200)
            self.send_header('Content-type',mimetype)
            self.end_headers()
            self.wfile.write( pg.encode() )
            return   # handled it
        elif self.path.endswith(".css"):
            mimetype='text/css'
            sendReply = True
        elif self.path.endswith(".jpg"):
            mimetype='image/jpg'
            sendReply = True
        elif self.path.endswith(".gif"):
            mimetype='image/gif'
            sendReply = True
        elif self.path.endswith(".js"):
            mimetype='application/javascript'
            sendReply = True
        elif self.path.endswith(".ico"):
            mimetype='image/x-icon'
            sendReply = True
        elif self.path.endswith(".txt"):
            mimetype = 'text/text'
            sendReply = True
        elif self.path.endswith(".json"):
            mimetype = 'text/text'
            sendReply = True
        else:
            time_now = datetime.now()
            parts = self.path.split('/')
            del parts[0]
            noun = None
            verb = parts[0]
            if len(parts) == 2:
                noun = parts[1]
            # print "verb=", verb, "noun=", noun
            if verb in request_map: # path with a special handler?
                mimetype='text/html'        # currently only handle one mime type
                self.send_response(200)
                self.send_header('Content-type',mimetype)
                self.end_headers()
                self.wfile.write( request_map[verb](noun).encode() )
                print('total request time:', str(datetime.now() - time_now))
                return      # handler handled it
        try:
            if sendReply == True:
                # open the static file requested and send it
                f = open(os.curdir + os.sep + self.path, 'rb')
                self.send_response(200)
                self.send_header('Content-type',mimetype)
                self.end_headers()
                self.wfile.write(f.read())
                f.close()
            else:
                self.send_error(404, 'Unknown file type request: %s' % self.path)
                return
        except IOError:
            self.send_error(404,'File Not Found: %s' % self.path)

    # handler for POST requests
    # TODO: a lot of duplicate code blocks in the POST processing
    def do_POST(self):
        if self.path=="/ups":
            # parse the "form" submitted by Twilio
            form = cgi.FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ={'REQUEST_METHOD':'POST',
                    'CONTENT_TYPE':self.headers['Content-Type'],
            })

            good_form = False
            raw_msg = ''
            if ('From' in form) and ('Body' in form):
                good_form = True
                raw_msg = form['Body'].value
                raw_msg = raw_msg.upper()

            # now, we try to parse what we got.
            if good_form and parse_sms( raw_msg ):
                log( timestamp() )
                log( "/ups:" + linkURL( raw_msg ) + ' // ' + form['From'].value )

                self.send_response(200)
                self.send_header('Content-type','text/xml')
                self.end_headers()
                self.wfile.write( twillio_response("Acknowledged").encode() )
                log("Acknowledged.\n----------------------------\n")
            else:
                log("-- ERROR --\n----------------------------\n")
                log_error( timestamp() )
                log_error( "/ups:" + linkURL( raw_msg ) + ' // ' + form['From'].value )
                log_error("-- ERROR --\n----------------------------\n")
                # self.send_error(404, twillio_response('Unparsable message: "%s"' % self.path).encode() )
                self.send_error(404, twillio_response('Unparsable message: "%s"' % self.path) )

        if self.path=="/pupdate":
            # parse the form submitted via /update
            form = cgi.FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ={'REQUEST_METHOD':'POST',
                    'CONTENT_TYPE':self.headers['Content-Type'],
            })

            good_form = False
            raw_msg = ''
            if ('From' in form) and ('Pilot' in form) and ('Message' in form):
                good_form = True
                raw_msg = form['Pilot'].value + ' ' + form['Message'].value
                raw_msg = raw_msg.upper()

            # now, we try to parse what we got.
            if good_form and parse_sms( raw_msg ):
                log( timestamp() )
                log( "/pupdate:" + linkURL( raw_msg ) + ' // ' + form['From'].value )

                self.send_response(200)
                self.send_header('Content-type','text/html')
                self.end_headers()
                feedback = "<span style=\"color:red\">Success! Want to do another?</span>"
                self.wfile.write( handle_web_update(feedback).encode() )
            else:
                # not logging errors since providing immediate feeback to submitter
                self.send_response(200)
                self.send_header('Content-type','text/html')
                self.end_headers()
                self.wfile.write ( "Oops. That did not work. Maybe an invalid pilot number? Be sure to fill in Who are you!<br/><br/>Use your browser BACK button and please try again.".encode() )

        if self.path=="/assign":
            # parse the form submitted via /update
            form = cgi.FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ={'REQUEST_METHOD':'POST',
                    'CONTENT_TYPE':self.headers['Content-Type'],
            })

            good_form = False
            raw_msg = ''
            if ('From' in form) and ('Pilot' in form) and ('Driver' in form):
                good_form = True
                raw_msg = 'DR' + form['Driver'].value + ' ' + form['Pilot'].value
                raw_msg = raw_msg.upper()

            if good_form and parse_sms( raw_msg ):
                log( timestamp() )
                log( "/assign:" + linkURL( raw_msg ) + ' // ' + form['From'].value )

                self.send_response(200)
                self.send_header('Content-type','text/html')
                self.end_headers()
                feedback = "<span style=\"color:red\">Success! Want to do another?</span>"
                self.wfile.write( handle_web_update(feedback).encode() )
            else:
                # not logging errors since providing immediate feedback to submitter
                self.send_response(200)
                self.send_header('Content-type','text/html')
                self.end_headers()
                self.wfile.write ( "Oops. That did not work. Maybe an invalid pilot number?<br/><br/>Use your browser BACK button and please try again.".encode() )


class MyTCPServer(ThreadingMixIn, HTTPServer):
    def server_bind(self):
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(self.server_address)

# parse command line arguments
def getopts(argv):
    opts = {}  # Empty dictionary to store key-value pairs.
    while argv:  # While there are arguments left to parse...
        if argv[0][0] == '-':  # Found a "-name value" pair.
            opts[argv[0]] = argv[1]  # Add key and value to the dictionary.
        argv = argv[1:]  # Reduce the argument list by copying it starting from index 1.
    return opts

server = None

# centralizing the shutdown/cleanup handling
def cleanup(sig, frame):
    global server
    global db
    if server:
        print('Interrupt received, shutting down the web server')
        server.socket.close()
        print('server closed')
        server = None
    if db:
        print('Closing database')
        db.close()
        print('database closed')
        db = None
    print('Exiting.')
    sys.exit(0)

if __name__ == '__main__':
    print('starting server')
    try:
        # set up signal handling
        signal.signal(signal.SIGINT, cleanup)   # typically sent by systemctl
        signal.signal(signal.SIGHUP, cleanup)   # just in case
        signal.signal(signal.SIGQUIT, cleanup)  # just in case

        # Create a web server and define the handler to manage the incoming requests
        opts = getopts(sys.argv)
        port = 8080
        if '-port' in opts:
            port = int(opts['-port'])
        if not MULTITHREADED:
            server = HTTPServer(('', port), myHandler)
        else:
            server = MyTCPServer(('', port), myHandler)
        print('Started httpserver on port ' , port)

        load_templates()
        log("let's get this party started")

        # handle requests (one at a time)
        server.serve_forever()
    finally:
        # shouldn't be needed...
        cleanup(signal.SIGINT, None)
