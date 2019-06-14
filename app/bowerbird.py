#!/usr/bin/python
from http.server import BaseHTTPRequestHandler,HTTPServer
from socketserver import ThreadingMixIn
import os, cgi, sys, time, csv, re, pprint, socket, urllib.request, urllib.parse, urllib.error
from string import Template
from datetime import datetime
from datetime import timedelta
from tinydb import TinyDB, Query, where

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
db = TinyDB('./data/bb_database.json')
ptable = db.table('pilots')
dtable = db.table('drivers')

# find a pilot (and appropriate db reference for updates)
def get_pilot(pid):
    matches = ptable.search(where(LABEL_PID) == pid)
    if len(matches) > 0:
        return matches[0], matches
    return None

# pilot status record field names (trying to isolate from CSV dependencies a little bit)
LABEL_PNUM = 'Pilot#' # space gets removed when all column header spaces are removed in parse_pilot_record
LABEL_PID = "PilotID" # more easily parseable/codeable label for the Pilot Number
LABEL_STATUS = 'STATUS'
LABEL_FNAME = 'FirstName'
LABEL_LNAME = 'LastName'
LABEL_PHONE = 'Telephone'
LABEL_LAT = 'Lat'
LABEL_LON = 'Lon'
LABEL_EVENT = 'Event'
LABEL_COUNTRY = 'Country'
LABEL_CITY = 'City'
LABEL_STATE = 'State'
LABEL_PHONE = 'Telephone'
LABEL_EMAIL = 'Email'
LABEL_FAI = 'FAI'
LABEL_DOB = 'DOB'
LABEL_GLIDER = 'GliderModel'
LABEL_COLORS = 'Colors'
LABEL_SPONSOR = 'Sponsor'
LABEL_ISPAID = 'IsPaid'
LABEL_URL = 'URL'
LABEL_DRIVER = 'Driver'

# status file field separator
FIELD_SEP = "\n"

# pilot data file name (try real data first, then try for the sample data included in git)
PilotDataFiles = ['./data/pilot_list.csv', './data/pilot_list-SAMPLE.csv']

# driver data file name (try real data first, then try for the sample data included in git)
DriverDataFiles = ['./data/driver_list.csv', './data/driver_list-SAMPLE.csv']

# regular expressions used to parse message parts
SpotRE = re.compile( r'#(\d{1,3}) {1,}(\w\w\w)' )
SimpleRE = re.compile( r'#{,1}(\d{1,3}) {1,}(\w\w\w)' )
LatLonRE = re.compile( r'll=(\d{1,3}\.\d{1,5}),([-]\d{1,3}.\d{1,5})' )
SpotCheckRE = re.compile( r'FRM:' )
ErrorRE = re.compile( r'ERROR' )

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
        f.write(msg.join(' ') + "\n")
        f.flush()
    except:
        print('log:', msg)

# append a message to the log file
def log_error(*msg):
    try:
        with open(ErrorLogFilename, "a+") as f:
            f.write(msg.join(' ') + "\n")
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
    page_templates['reset_confirm'] = Template(open('./app/reset_confirm.html', 'r').read())
    page_templates['nav_link']      = Template(open('./app/nav_link.html', 'r').read())
    page_templates['nav_nonlink']   = Template(open('./app/nav_nonlink.html', 'r').read())
    page_templates['nav_bar']       = Template(open('./app/nav_bar.html', 'r').read())
    page_templates['nav_bar_admin'] = Template(open('./app/nav_bar_admin.html', 'r').read())
    page_templates['ups']           = Template(open('./app/update_status.html', 'r').read())
    page_templates['_index']        = Template(open('./index.html', 'r').read())

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
filter_pv = { # pilot view: show what the pilots need to see
        'AID': display_def(False),
        'LOK': display_def(True),
        'PUP': display_def(True),
        'FLY': display_def(True),
        'NOT': display_def(False, ''),
        }
filter_rv = { # retrieve view: show what the retrieve coordinator needs to see
        'LOK': display_def(True),
        'PUP': display_def(True),
        'AID': display_def(True),
        'GOL': display_def(True),
        'LZ1': display_def(True),
        'LZ2': display_def(True),
        'DRA': display_def(True),
        'DRB': display_def(True),
        'DRC': display_def(True),
        'DRD': display_def(True),
        'DRE': display_def(True),
        'DRF': display_def(True),
        'NOT': display_def(False, ''),
        }
filter_av = { # admin view: show all current status
        'NOT': display_def(False, ''),
        }

def get_last_pilot_status(pilot):
    if not 'status_history' in pilot:
        return ''
    else:
        return pilot['status_history'][-1]

def filter_status(pilot, flt):
    status = pilot[LABEL_STATUS]
    if status in flt:
        f = flt[status]
        if f.display:
            return (True, status)
        elif f.alt:
            return (True, f.alt)
        else:
            return (True, get_last_pilot_status(pilot))
    return (False, status)

# render a pilot status overview
def handle_pilot_overview(noun):
    tiles = ""
    # TODO.txt: how easy would it be to create sections based on either number range or event field in pilot db?
    # (so Open Race would be a separate table from Sprint Race which is separate from SuperClinic)
    for p in sorted(ptable.all(), key=lambda i: i[LABEL_PID]):
        # don't display NOT label
        processed, status = filter_status(p, filter_pv)   # p[LABEL_STATUS]
        if not processed:
            status = ''
        tiles += render_template('std_tile', {'pilot_id':p[LABEL_PID], 'pilot_status':status})
    pg = render_template('std_page', {'content':tiles, 'nav':'', 'preamble':'', 'last_reset':LastResetTime.strftime(LastResetFormat)})
    return pg

# render admin view of pilot status
def handle_admin_overview(noun):
    tiles = ""
    # TODO.txt: how easy would it be to create sections based on either number range or event field in pilot db?
    # (so Open Race would be a separate table from Sprint Race which is separate from SuperClinic)
    for p in sorted(ptable.all(), key=lambda i: i[LABEL_PID]):
        # don't display NOT label
        processed, status = filter_status(p, filter_av)   # p[LABEL_STATUS]
        tiles += render_template('std_tile', {'pilot_id':p[LABEL_PID], 'pilot_status':status})
    adminnav = render_nav_admin_header()
    preamble = 'Clicking on a tile will reveal all known info about that pilot.'
    pg = render_template('std_page', {'content':tiles, 'nav':adminnav, 'preamble':preamble, 'last_reset':LastResetTime.strftime(LastResetFormat)})
    return pg

def handle_listview( noun ):
    # this is pretty ugly...
    table = '<table>'

    # from a pid, pull a name
    def pid_name( pid ):
        p = get_pilot( pid )
        return p['FirstName'] + p['LastName']

    # not worrying about performance here...
    for p in sorted(ptable.all(), key=lambda i: i[LABEL_PID]):
        table += '<tr><td>' + p['FirstName'] + '</td><td>' + p['LastName'] + '</td>' + render_template('std_tabletile', {'pilot_id':p[LABEL_PID], 'pilot_status':p[LABEL_STATUS]}) + "</tr>\n"
    table += '</table>'
    nav = render_nav_header()
    adminnav = render_nav_admin_header()
    pg = render_template('std_page', {'content':table, 'nav':nav, 'preamble':'', 'adminnav':adminnav, 'last_reset':LastResetTime.strftime(LastResetFormat)})
    return pg

# display all message logs
def handle_logs(noun):
    contents = None
    with open(LogFilename, "r") as f:
        contents = f.read()
    adminnavr = render_nav_admin_header()
    preamble = 'Logs are helpful if a message appears to have been sent but wasn\'t properly attributed or interpreted. You might find that the message was sent using the wrong pilot number or an unrecognizable status.'
    pg = render_template('std_page', dict(content='<pre>' + contents + '</pre>', nav=adminnavr, preamble=preamble, last_reset=LastResetTime.strftime(LastResetFormat)))
    return pg

# display all message errors (subset of logs)
def handle_error_logs(noun):
    contents = None
    with open(ErrorLogFilename, "r") as f:
        contents = f.read()
    adminnavr = render_nav_admin_header()
    preamble = 'Errors are only those log entries that were not successfully processed. These are the most important items to review regularly. Often these have missing or unknown pilot numbers, or incorrectly formatted messages.'
    pg = render_template('std_page', dict(content='<pre>' + contents + '</pre>', nav=adminnavr, preamble=preamble, last_reset=LastResetTime.strftime(LastResetFormat)))
    return pg

# translate a row from the csv into a pilot status record
# TODO.txt: abstract the pilot record fields from the csv column headers
def parse_pilot_record(header, row):
    rec = {}
    for i in range( len( header ) ):
        clean = header[i].replace(" ", "") # strip out spaces
        if clean == 'Status' or clean == 'status':
            clean = LABEL_STATUS # need to have a known, exact value for the status index
        rec[clean] = row[i]
    rec[LABEL_PID] = rec[LABEL_PNUM]
    rec[LABEL_LAT] = 0.0    #
    rec[LABEL_LON] = 0.0
    rec[LABEL_DRIVER] = None
    try:
        if (rec[LABEL_STATUS] is None) or (rec[LABEL_STATUS] == ''):
            rec[LABEL_STATUS] = 'NOT'   # set current status only if it is NOT explicitly set via pilot_list.csv
    except KeyError:
        rec[LABEL_STATUS] = 'NOT' # if column is completely missing from pilot_list.csv
    return rec

def parse_driver_record(header, row):
    rec = {}
    for i in range( len( header ) ):
        clean = header[i].replace(" ", "") # strip out spaces
        rec[clean] = row[i]
    rec[LABEL_STATUS] = 'NAP'
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
    resp = "handling reset...\n"
    LastResetTime = datetime.today()

    # rename status directory to archive/status-<timestamp>
    if os.access("./status", os.R_OK):
        newname = "./archive/status-" + str( int(time.time()) )
        resp += "backing up current status to " + newname + "\n"
        os.rename( "./status", newname )
    os.mkdir("./status")

    # initialize the database from the CSV
    db.purge_tables()

    # load the pilot records
    df = PilotDataFiles[1] # default to the sample data
    if os.path.isfile( PilotDataFiles[0] ):
        df = PilotDataFiles[0]
    load_csv_into( ptable, df, parse_pilot_record )

    # load_pilots()
    df = DriverDataFiles[1]
    if os.path.isfile( DriverDataFiles[0] ):
        df = DriverDataFiles[0]
    load_csv_into( dtable, df, parse_driver_record )

    # load the driver records

    resp += "\n\n" + "<p><a href='/'>Return to Overview</a></p>"
    return resp

def handle_reload():
    # TODO.txt: verify that database is "live"
    return "handling reload"

def twillio_response(msg):
    resp = """<?xml version="1.0" encoding="UTF-8"?><Response><Message>
    <Body>%s</Body></Message></Response>""" % msg
    return resp

# parse a received SMS message
def parse_sms(sms):
    match = None
    ll_match = None
    # TODO: is this a driver assignment message? look for (approx) ^DR[A..I]\b[1..9][0..9][0..9]
    if sms.startswith('DR'):
        # it's a driver assignment
        # TODO: DR* messages update the ride_status field
        parts = sms.split(' ')
        driver = sms[0]
        pilot, dbref = get_pilot(sms[1])
        if pilot:
            pilot[LABEL_DRIVER] = driver
            ptable.write_back( dbref )

    if re.search( SpotCheckRE, sms ):
        # SPOT message
        match = re.search( SpotRE, sms )
        ll_match = re.search( LatLonRE, sms )
    else:
        match = re.search( SimpleRE, sms )

    if match != None:
        try:
            pid = match.group(1)
            pilot, dbref = get_pilot(pid)
            if pilot:
                code = match.group(2).upper()

                # TODO: got a pilot and a code, check for pilot first or last name in sms

                # update the status field
                pilot[LABEL_STATUS] = code

                # save the raw message (in the pilot record)
                if not 'history' in pilot:
                    pilot['history'] = []
                pilot['history'].append(sms)

                # keep a list of previous statuses
                if not 'status_history' in pilot:
                    pilot['status_history'] = []
                pilot['status_history'].append(sms)

                # save to the db
                ptable.write_back( matches )

                # save to the status text file
                update_status_file(pid, sms)
                return True
            else:
                log( "Unknown pilot id:" + str(pid) )
                return False
        except:
            # print("parse_sms: unusable match on '%s'" % sms)
            log( "Unusable match on '%s'" % sms)
            log( "Exception details: %s" % sys.exc_info()[1] )
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
    pg = render_template('std_page', {'content':data, 'nav':'', 'preamble':'', 'last_reset':LastResetTime.strftime(LastResetFormat)})
    return pg

# basic category ("Event") overview page
def handle_categoryview(category):
    tiles = ""
    # 911 TODO - this requires the category ("Event") to have no spaces so it can be specified in the URL
    # NOTE: nav will be hard-coded since it's easier for people that way
    if category:
        preamble = '<h2>Event/Type: ' + category + '</h2>'
        for p in sorted(ptable.all(), key=lambda i: i[LABEL_PID]):
            # filter for only those where Event = category that was passed in
            if p['Event'] != category:
                continue

            # don't display NOT label
            pstat = p[LABEL_STATUS]
            if 'NOT' in pstat:
                pstat = ''
            tiles += render_template('std_tile', {'pilot_id':p[LABEL_PID], 'pilot_status':pstat})
    else:
        preamble = '<h3>You need to specify the Event (type) as defined in the CSV:<br/> http://bbtrack.me/type/Open</h3>'

    nav = render_nav_header()
    pg = render_template('std_page', {'content':tiles, 'nav':nav, 'preamble':preamble, 'last_reset':LastResetTime.strftime(LastResetFormat)})
    return pg

# basic pilotview page
def handle_pilotview(noun):
    pid = noun
    pilot_details, dbref = get_pilot(pid)
    pilot_info = render_template('pilot_detail', pilot_details)
    # pilot_info += '<pre>%s</pre>' % pprint.pformat(pilot_details) # print everything we got!
    # append the pilot log contents

    try:
        with open('./status/' + str(pid), 'r') as sfile:
            pilot_info += '<pre>' + sfile.read() + '</pre>'
    except FileNotFoundError:
        pilot_info += '<pre>(no status updates)</pre>'

    nav = render_nav_header()
    pg = render_template('std_page', {'content':pilot_info, 'nav':nav, 'preamble':'', 'last_reset':LastResetTime.strftime(LastResetFormat)})
    return pg


# beginnings of pilotadmin page
def handle_pilotadmin(noun):
    pid = noun
    pilot_details, dbref = get_pilot(pid)
    pilot_info = '<pre>%s</pre>' % pprint.pformat(pilot_details) # print everything we got!
    # append the pilot log contents
    with open('./status/' + str(pid), 'r') as sfile:
        pilot_info += '<pre>' + sfile.read() + '</pre>'

    adminnav = render_nav_admin_header()
    pg = render_template('std_page', {'content':pilot_info, 'nav':adminnav, 'preamble':'', 'last_reset':LastResetTime.strftime(LastResetFormat)})
    return pg

# testing interface for status updates
def handle_ups(noun):
    adminnav = render_nav_admin_header()
    return render_template('ups', {'nav':adminnav})

# render the default home page
def handle_index(noun):
    nav = render_nav_header()
    return render_template('_index', {'nav':nav})

# map a GET request path to a handler (that produces HTML)
request_map = {
    'overview' : handle_pilot_overview,
    'enchilada' : handle_admin_overview,
    'logs' : handle_logs,
    'errors' : handle_error_logs,
    'reset' : handle_reset_confirm,
    'reset-request' : handle_reset,
    'pilotview' : handle_pilotview,
    'pilot' : handle_pilotview,
    'pilotadmin' : handle_pilotadmin,
    'categoryview' : handle_categoryview,
    'type' : handle_categoryview,
    'list' : handle_listview,
    'ups' : handle_ups, # remember: GET and POST are different chunks of code
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
            self.path = "./index.html"  # TODO: fix, kind of a no-no to change the request path in place

        # determine mimetype for static assets
        if self.path.endswith(".html"):
            sendReply = False
            if not self.path.startswith('.'):
                self.path = '.' + self.path
            if not self.path in static_pages:   # TODO: this is pretty hacky too...
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
        else:
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
    def do_POST(self):
        if self.path=="/ups":
            # parse the "form" submitted by Twilio
            form = cgi.FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ={'REQUEST_METHOD':'POST',
                    'CONTENT_TYPE':self.headers['Content-Type'],
            })

            raw_msg = form['Body'].value
            log( timestamp() )
            log( "/ups:" + linkURL( raw_msg ) + ' // ' + form['From'].value )
            # pprint.pprint(form)
            if parse_sms( raw_msg ):
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

if __name__ == '__main__':
    print('starting server')
    try:
        # Create a web server and define the handler to manage the incoming requests
        opts = getopts(sys.argv)
        port = 8080
        if '-port' in opts:
            port = int(opts['-port'])
        server = MyTCPServer(('', port), myHandler)
        print('Started httpserver on port ' , port)

        load_templates()

        # handle requests (one at a time)
        server.serve_forever()

    except KeyboardInterrupt:
        print('Interrupt received, shutting down the web server')
        server.socket.close()
