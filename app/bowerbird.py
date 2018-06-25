#!/usr/bin/python
from BaseHTTPServer import BaseHTTPRequestHandler,HTTPServer
from SocketServer import ThreadingMixIn
import os, cgi, sys, time, csv, re, pprint, socket, urllib
from string import Template
from datetime import datetime
from datetime import timedelta

#
# Bowerbird 3.0
# 
# note:
#   for maximum portability, this is a bare-metal solution of bowerbird.
#   not fancy, but functional. depends only on standard python libraries.
# to launch (on a server):
#   python2.7 app/bowerbird.py
#   
#### TODO LIST moved to bowerbird/todo.txt. note that a couple of inline todo items were left here AND copied to todo.txt

PilotStatus = {}

# pilot status record field names (trying to isolate from CSV dependencies a little bit)
LABEL_PNUM = 'Pilot #'
LABEL_PID = "PilotID" # more easily parseable/codeable label for the Pilot Number
LABEL_STATUS = 'STATUS'
LABEL_NAME = 'Name'
LABEL_LAT = 'Lat'
LABEL_LON = 'Lon'

# status file field separator
FIELD_SEP = "\n"

# pilot data file name (try real data first, then try for the sample data included in git)
PilotDataFiles = ['./data/pilot_list.csv', './data/pilot_list-SAMPLE.csv']

# regular expressions used to parse message parts
SpotRE = re.compile( r'#(\d{1,3}) {1,}(\w\w\w)' )
SimpleRE = re.compile( r'#{,1}(\d{1,3}) {1,}(\w\w\w)' )
LatLonRE = re.compile( r'll=(\d{1,3}\.\d{1,5}),([-]\d{1,3}.\d{1,5})' )
SpotCheckRE = re.compile( r'FRM:' )

LogFilename = "./status/bb_log.txt"

# NOTE: this is assuming PDT timezone!! (currently only applied to log times, not LastResetTime)
TimeDelta = timedelta(hours=7)

# tracking the last reset time
# TODO: convert to local time
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

# super simple html templating system
page_templates = {}

def load_templates():
	page_templates['std_page']      = Template(open('./app/std_page.html', 'r').read())
	page_templates['timer_page']    = Template(open('./app/timer_page.html', 'r').read())
	page_templates['std_tile']      = Template(open('./app/std_tile.html', 'r').read())
	page_templates['pilot_detail']  = Template(open('./app/pilot_detail.html', 'r').read())
	page_templates['reset_confirm'] = Template(open('./app/reset_confirm.html', 'r').read())
	page_templates['nav_link']      = Template(open('./app/nav_link.html', 'r').read())
	page_templates['nav_nonlink']   = Template(open('./app/nav_nonlink.html', 'r').read())
	page_templates['nav_bar']       = Template(open('./app/nav_bar.html', 'r').read())
	
def render_template(name, stuff):
	t = page_templates[name]
	return t.substitute(stuff)

# render a 'standard' header with links turned on or off
def render_nav_header(overview=True, logs=True):
	links = []

	if overview:
		links.append( render_template('nav_link', dict(dest='/', label='Overview')) )
	else:
		links.append( render_template('nav_nonlink', dict(label='Overview')) )

	if logs:
		links.append( render_template('nav_link', dict(dest='/logs', label='Logs')) )
	else:
		links.append( render_template('nav_nonlink', dict(label='Logs')) )

	stuff = '<td>|</td>'.join( links ) # TODO: get this scrap of html into a template...
	return page_templates['nav_bar'].substitute( dict(contents=stuff) )

# append a status update to a pilot's status file
def update_status_file(pid, sms):
	with open('./status/' + str(pid), 'a') as sfile:
		sfile.write( sms + FIELD_SEP + timestamp() + "\n")
		
# render a pilot status overview
def handle_overview(noun):
	tiles = ""
        # todo: how easy would it be to create sections based on either number range or event field in pilot db?
        # (so Open Race would be a separate table from Sprint Race which is separate from SuperClinic)
	for pid in sorted(PilotStatus):
		p = PilotStatus[pid]
		
		# don't display NOT label
		pstat = p[LABEL_STATUS]
		if 'NOT' in pstat:
			pstat = ''
		tiles += render_template('std_tile', {'pilot_id':pid, 'pilot_status':pstat})
	# can't use this until we have autorefresh as a template, not just in index.html
	# nav = render_nav_header(overview=False, logs=True)
	pg = render_template('std_page', {'content':tiles, 'nav':'', 'last_reset':LastResetTime.strftime(LastResetFormat)})
	return pg
	
# display all message logs
def handle_logs(noun):
	contents = None
	with open(LogFilename, "r") as f:
		contents = f.read()
	navr = render_nav_header(logs=False)
	pg = render_template('std_page', dict(content='<pre>' + contents + '</pre>', nav=navr, last_reset=LastResetTime.strftime(LastResetFormat)))
	return pg

# translate a row from the csv into a pilot status record
# TODO: abstract the pilot record fields from the csv column headers
# TODO: create an actual pilot object and stop being lazy
def parse_pilot_record(header, row):
	rec = {}
	rec['STATUS'] = 'NOT'	# set current status
	for i in range( len( header ) ):
		rec[header[i]] = row[i]
	rec[LABEL_PID] = rec[LABEL_PNUM]
	rec[LABEL_LAT] = 0.0	# 
	rec[LABEL_LON] = 0.0
	return rec

# load the csv file and parse out pilot records (filling up PilotStatus 'database')
def load_pilots():
	count = 0
	pdf = PilotDataFiles[1] # default to the sample data
	if os.path.isfile( PilotDataFiles[0] ):
		pdf = PilotDataFiles[0]
	with open(pdf, 'rb') as csvfile:
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
					PilotStatus[int(pstat[LABEL_PNUM])] = pstat
				except:
					print "Unexpected error:", sys.exc_info()[0]
					print "count", count, "row='%s'" % row
					return
			count += 1
	print "loaded", count, "pilots"
	
def handle_reset(noun):
	resp = "handling reset...\n"
	LastResetTime = datetime.today()
	
	# todo: rename status directory to archive/status-<timestamp>
	if os.access("./status", os.R_OK):
		newname = "./archive/status-" + str( int(time.time()) )
		resp += "backing up current status to " + newname + "\n"
		os.rename( "./status", newname )
	os.mkdir("./status")
	
	# initialize the PilotStatus 'database'
	load_pilots()

        # todo: write out timestamp so it can be shown on Overview page
        # or maybe whole string: "Last reset: <timestamp>"
        # then can just display that string on Overview?
	
	# todo: make initial pilot log files in status directory
	for pid in PilotStatus:
		p = PilotStatus[pid]
		update_status_file( pid, p[LABEL_STATUS] )
	resp += "\n\n" + "<p><a href='/'>Return to Overview</a>"
	return resp

def handle_reload():
	# todo: update pilot status from last message in status file directory
	for rec in PilotStatus:
		print "find a record for", rec[LABEL_PNUM]
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
			pid = int( match.group(1) )
			if pid in PilotStatus:
				code = match.group(2)
				pilot = PilotStatus[pid]
				pilot[LABEL_STATUS] = code.upper()
				update_status_file(pid, sms)
				return True
			else:
				log( "Unknown pilot id:" + str(pid) )
				return False
		except:
			print "parse_sms: unusable match on '%s'" % sms
			log( "Unusable match on '%s'" % sms)
			return False
	else:
		print "parse_sms: unable to parse '%s'" % sms
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
		category = urllib.unquote(category).decode('utf8')
		tiles = "<h2>Event/Type: " + category + "</h2>"

	for pid in sorted(PilotStatus):
		p = PilotStatus[pid]
		
		# if no category, let them know they need to pick one
		if not category:
			tiles = '<h3>You need to specify the Event (type) as defined in the CSV:<br/> http://bbtrack.me/type/Driver</h3>'
			break
		
		# filter for only those where Event = category that was passed in
		if p['Event'] != category:
			continue
		
		# don't display NOT label
		pstat = p[LABEL_STATUS]
		if 'NOT' in pstat:
			pstat = ''
		tiles += render_template('std_tile', {'pilot_id':pid, 'pilot_status':pstat})

	nav = render_nav_header(overview=True, logs=True)
	pg = render_template('std_page', {'content':tiles, 'nav':nav, 'last_reset':LastResetTime.strftime(LastResetFormat)})
	return pg

# basic pilotview page
def handle_pilotview(noun):
	pid = int(noun)
	pilot_details = PilotStatus[pid]
	# pilot_info = '<pre>%s</pre>' % pprint.pformat(pilot_details) # print everything we got!
	pilot_info = render_template('pilot_detail', pilot_details)
	# append the pilot log contents
	with open('./status/' + str(pid), 'r') as sfile:
		pilot_info += '<pre>' + sfile.read() + '</pre>'

	nav = render_nav_header(overview=True, logs=True)
	pg = render_template('std_page', {'content':pilot_info, 'nav':nav, 'last_reset':LastResetTime.strftime(LastResetFormat)})
	return pg


# beginnings of pilotadmin page
def handle_pilotadmin(noun):
	pid = int(noun)
	pilot_details = PilotStatus[pid]
	pilot_info = '<pre>%s</pre>' % pprint.pformat(pilot_details) # print everything we got!
	# append the pilot log contents
	with open('./status/' + str(pid), 'r') as sfile:
		pilot_info += '<pre>' + sfile.read() + '</pre>'

	nav = render_nav_header(overview=True, logs=True)
	pg = render_template('std_page', {'content':pilot_info, 'nav':nav, 'last_reset':LastResetTime.strftime(LastResetFormat)})
	return pg


# map a request path to a handler (that produces HTML)
request_map = {
	'overview' : handle_overview,
	'logs' : handle_logs,
	'reset' : handle_reset_confirm,
	'reset-request' : handle_reset,
	'pilotview' : handle_pilotview,
	'pilot' : handle_pilotview,
	'pilotadmin' : handle_pilotadmin,
	'categoryview' : handle_categoryview,
	'type' : handle_categoryview,
}

#
# the server
#
class myHandler(BaseHTTPRequestHandler):
	
	# handler for GET requests
	def do_GET(self):
		sendReply = False
		if self.path=="/":				# no path specified, give them index.html
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
				if verb in request_map:	# path with a special handler?
					mimetype='text/html'		# currently only handle one mime type
					self.send_response(200)
					self.send_header('Content-type',mimetype)
					self.end_headers()
					self.wfile.write( request_map[verb](noun) )
					return		# handler handled it
		try:
			if sendReply == True:
				# open the static file requested and send it
				f = open(os.curdir + os.sep + self.path) 
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
				self.wfile.write( twillio_response("Acknowledged") )
				log("Acknowledged.\n----------------------------\n")
			else:
				log("-- ERROR --\n----------------------------\n")
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
	print 'starting server'
	try:
		# Create a web server and define the handler to manage the incoming requests
		opts = getopts(sys.argv)
		port = 8080
		if '-port' in opts:
			port = int(opts['-port'])
		server = MyTCPServer(('', port), myHandler)
		print 'Started httpserver on port ' , port
		
		load_templates()
		
		# handle requests (one at a time)
		server.serve_forever()
	
	except KeyboardInterrupt:
		print 'Interrupt received, shutting down the web server'
		server.socket.close()
