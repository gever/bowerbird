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

def get_pilot(pid):
    matches = ptable.search(where(LABEL_PID) == pid)
    if len(matches) > 0:
        return matches[0]
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

# status file field separator
FIELD_SEP = "\n"

# pilot data file name (try real data first, then try for the sample data included in git)
PilotDataFiles = ['./data/pilot_list.csv', './data/pilot_list-SAMPLE.csv']

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
def log(msg):
    try:
        with open(LogFilename, "a+") as f:
            f.write(msg+"\n")
            f.flush()
    except:
        print('log:', msg)

# append a message to the log file
def log_error(msg):
    try:
        with open(ErrorLogFilename, "a+") as f:
            f.write(msg+"\n")
            f.flush()
    except:
        print('log_error:', msg)

# super simple html templating system
page_templates = {}

def load_templates():
    page_templates['std_page']      = Template(open('./app/std_page.html', 'r').read())
    page_templates['timer_page']    = Template(open('./app/timer_page.html', 'r').read())
    page_templates['std_tile']      = Template(open('./app/std_tile.html', 'r').read())
    page_templates['std_tabletile'] = Template(open('./app/std_tabletile.html', 'r').read())
    page_templates['pilot_detail']  = Template(open('./app/pilot_detail.html', 'r').read())
    page_templates['reset_confirm'] = Template(open('./app/reset_confirm.html', 'r').read())
    page_templates['nav_link']      = Template(open('./app/nav_link.html', 'r').read())
    page_templates['nav_nonlink']   = Template(open('./app/nav_nonlink.html', 'r').read())
    page_templates['nav_bar']       = Template(open('./app/nav_bar.html', 'r').read())
    page_templates['ups']           = Template(open('./app/update_status.html', 'r').read())

def render_template(name, stuff):
    t = page_templates[name]
    return t.safe_substitute(stuff)

# render a 'standard' header with links turned on or off
def render_nav_header(overview=True, logs=True):
    links = []

    if overview:
        links.append( render_template('nav_link', dict(dest='/', label='Overview')) )
    else:
        links.append( render_template('nav_nonlink', dict(label='Overview')) )
        links.append( render_template('nav_link', dict(dest='/list', label='List')) )

    if logs:
        links.append( render_template('nav_link', dict(dest='/logs', label='Logs')) )
        links.append( render_template('nav_link', dict(dest='/errors', label='Errors')) )
    else:
        links.append( render_template('nav_nonlink', dict(label='Logs')) )
        links.append( render_template('nav_link', dict(dest='/errors', label='Errors')) )

        links.append( render_template('nav_link', dict(dest='/list', label='List')) )
    stuff = '<td>|</td>'.join( links ) # TODO: get this scrap of html into a template...
    return page_templates['nav_bar'].substitute( dict(contents=stuff) )

# append a status update to a pilot's status file
def update_status_file(pid, sms):
    with open('./status/' + str(pid), 'a') as sfile:
        sfile.write( sms + FIELD_SEP + timestamp() + "\n")

# render a pilot status overview
def handle_overview(noun):
    tiles = ""
    # TODO: how easy would it be to create sections based on either number range or event field in pilot db?
    # (so Open Race would be a separate table from Sprint Race which is separate from SuperClinic)
    for p in sorted(ptable.all(), key=lambda i: i[LABEL_PID]):
        # don't display NOT label
        pstat = p[LABEL_STATUS]
        if 'NOT' in pstat:
            pstat = ''
        tiles += render_template('std_tile', {'pilot_id':p[LABEL_PID], 'pilot_status':pstat})
    # can't use this until we have autorefresh as a template, not just in index.html
    # nav = render_nav_header(overview=False, logs=True)
    pg = render_template('std_page', {'content':tiles, 'nav':'', 'last_reset':LastResetTime.strftime(LastResetFormat)})
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
    nav = render_nav_header(overview=True, logs=True)
    pg = render_template('std_page', {'content':table, 'nav':nav, 'last_reset':LastResetTime.strftime(LastResetFormat)})
    return pg

# display all message logs
def handle_logs(noun):
    contents = None
    with open(LogFilename, "r") as f:
        contents = f.read()
    navr = render_nav_header(logs=False)
    pg = render_template('std_page', dict(content='<pre>' + contents + '</pre>', nav=navr, last_reset=LastResetTime.strftime(LastResetFormat)))
    return pg

# display all message errors (subset of logs)
def handle_error_logs(noun):
    contents = None
    with open(ErrorLogFilename, "r") as f:
        contents = f.read()
    navr = render_nav_header(logs=True)
    pg = render_template('std_page', dict(content='<pre>' + contents + '</pre>', nav=navr, last_reset=LastResetTime.strftime(LastResetFormat)))
    return pg

# translate a row from the csv into a pilot status record
# TODO: abstract the pilot record fields from the csv column headers
# TODO: create an actual pilot object and stop being lazy
def parse_pilot_record(header, row):
    rec = {}
    for i in range( len( header ) ):
        cleanheader = header[i].replace(" ", "") # strip out spaces
        if cleanheader == 'Status' or cleanheader == 'status':
            cleanheader = LABEL_STATUS # need to have a known, exact value for the status index
        rec[cleanheader] = row[i]
    rec[LABEL_PID] = rec[LABEL_PNUM]
    rec[LABEL_LAT] = 0.0    #
    rec[LABEL_LON] = 0.0
    try:
        if (rec[LABEL_STATUS] is None) or (rec[LABEL_STATUS] == ''):
            rec[LABEL_STATUS] = 'NOT'   # set current status only if it is NOT explicitly set via pilot_list.csv
    except KeyError:
        rec[LABEL_STATUS] = 'NOT' # if column is completely missing from pilot_list.csv
    return rec

# load the csv file and parse out pilot records (filling up 'database')
def load_pilots():
    count = 0
    pdf = PilotDataFiles[1] # default to the sample data
    if os.path.isfile( PilotDataFiles[0] ):
        pdf = PilotDataFiles[0]
    with open(pdf, 'r') as csvfile:
        header_row = None
        csv_r = csv.reader(csvfile)
        for row in csv_r:
            if header_row == None:
                # save the first row for column names
                header_row = row
            else:
                # save this pilot in the server-side pilot status 'database'
                try:
                    pstat = parse_pilot_record(header_row, row)
                    ptable.insert(pstat)
                except:
                    print("Unexpected error:", sys.exc_info()[0])
                    print("count", count, "row='%s'" % row)
                    return
            count += 1
    print("loaded", count, "pilots")

def handle_reset(noun):
    # TODO: use a page template to format this output (lots of html fragments in here)
    resp = "handling reset...\n"
    LastResetTime = datetime.today()

    # initialize the database from the CSV
    db.purge_tables()
    load_pilots()

    resp += "\n\n" + "<p><a href='/'>Return to Overview</a></p>"
    return resp

def handle_reload():
    # TODO: verify that database is "live"
    return "handling reload"

def twillio_response(msg):
    resp = """<?xml version="1.0" encoding="UTF-8"?><Response><Message>
    <Body>%s</Body></Message></Response>""" % msg
    return resp

# parse a received SMS message
def parse_sms(sms):
    match = None
    ll_match = None
    if re.search( SpotCheckRE, sms ):
        # SPOT message
        match = re.search( SpotRE, sms )
        ll_match = re.search( LatLonRE, sms )
    else:
        match = re.search( SimpleRE, sms )

    if match != None:
        try:
            pid = match.group(1)
            pilot = get_pilot(pid)
            if pilot:
                code = match.group(2)

                # update the status field
                pilot[LABEL_STATUS] = code.upper()

                # save the raw message (in the pilot record)
                if not 'history' in pilot:
                    pilot['history'] = []
                pilot['history'].append(sms)

                # save to the db
                ptable.write_back( matches )

                update_status_file(pid, sms)
                return True
            else:
                log( "Unknown pilot id:" + str(pid) )
                return False
        except:
            # print("parse_sms: unusable match on '%s'" % sms)
            log( "Unusable match on '%s'" % sms)
            return False
    else:
        # print("parse_sms: unable to parse '%s'" % sms)
        log( "Unable to parse '%s'" % sms )
        return False

    return True

# reset confirmation handling (/reset)
def handle_reset_confirm(noun):
    # 911 this probably isn't the right way to do this...
    # TODO move all the HTML out into a template
    data = '<pre>Warning: this will reset the system for a new day of competition, the current status and message history of each pilot will be archived and set back to defaults.<p>Do you wish to continue? <a href="/reset-request">Absolutely</a> // <a href="/overview">Nope</a></pre>'
    #data = render_template('reset_confirm', {'unused':'nothing'})
    pg = render_template('std_page', {'content':data, 'nav':'', 'last_reset':LastResetTime.strftime(LastResetFormat)})
    return pg

# basic category ("Event") overview page
def handle_categoryview(category):
    if category:
        tiles = "<h2>Event/Type: " + category + "</h2>"
        for p in sorted(ptable.all(), key=lambda i: i[LABEL_PID]):
            # filter for only those where Event = category that was passed in
            if p['Event'] != category:
                continue

            # don't display NOT label
            pstat = p[LABEL_STATUS]
            if 'NOT' in pstat:
                pstat = ''
            tiles += render_template('std_tile', {'pilot_id':pid, 'pilot_status':pstat})
    else:
        tiles = '<h3>You need to specify the Event (type) as defined in the CSV:<br/> http://bbtrack.me/type/Driver</h3>'

    nav = render_nav_header(overview=True, logs=True)
    pg = render_template('std_page', {'content':tiles, 'nav':nav, 'last_reset':LastResetTime.strftime(LastResetFormat)})
    return pg

# basic pilotview page
def handle_pilotview(noun):
    pid = noun
    pilot_details = get_pilot(pid)
    pilot_info = render_template('pilot_detail', pilot_details)
    #pilot_info += '<pre>%s</pre>' % pprint.pformat(pilot_details) # print everything we got!
    # append the pilot log contents
    with open('./status/' + str(pid), 'r') as sfile:
        pilot_info += '<pre>' + sfile.read() + '</pre>'

    nav = render_nav_header(overview=True, logs=True)
    pg = render_template('std_page', {'content':pilot_info, 'nav':nav, 'last_reset':LastResetTime.strftime(LastResetFormat)})
    return pg


# beginnings of pilotadmin page
def handle_pilotadmin(noun):
    pid = noun
    pilot_details = get_pilot(pid)
    pilot_info = '<pre>%s</pre>' % pprint.pformat(pilot_details) # print everything we got!
    # append the pilot log contents
    with open('./status/' + str(pid), 'r') as sfile:
        pilot_info += '<pre>' + sfile.read() + '</pre>'

    nav = render_nav_header(overview=True, logs=True)
    pg = render_template('std_page', {'content':pilot_info, 'nav':nav, 'last_reset':LastResetTime.strftime(LastResetFormat)})
    return pg

# testing interface for status updates
def handle_ups(noun):
    return render_template('ups', {})

# map a GET request path to a handler (that produces HTML)
request_map = {
    'overview' : handle_overview,
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
}

#
# the server
#
class myHandler(BaseHTTPRequestHandler):

    # handler for GET requests
    def do_GET(self):
        sendReply = False
        if self.path=="/":              # no path specified, give them index.html
            self.path="/index.html"
            mimetype='text/html'
            sendReply = True
        else:
            # determine mimetype for static assets
            if self.path.endswith(".html"):
                mimetype='text/html'
                sendReply = True
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
                self.send_error(404, twillio_response('Unparsable message: "%s"' % self.path).encode() )


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
