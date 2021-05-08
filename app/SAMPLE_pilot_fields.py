# pilot status record field names (trying to isolate from CSV dependencies a little bit)
# NOTE: you can have spaces in the column headers, but must remove them when shown in here!

# every record MUST have a pilot number!
LABEL_PNUM = 'Pilot#' # space gets removed when all column header spaces are removed in parse_pilot_record
LABEL_PID = 'Pilot#' # need to duplicate this label setting until we figure out why setting from PNUM isn't working

# the following two column headers are special - do not change them
LABEL_EVENT = 'Event' # this is used if you have multiple events/classes in the comp (Open and Sprint)
LABEL_STATUS = 'STATUS' # this can be used to set all pilots to a specific status every morning (e.g., FLY)

# the following columns are used in various places and strongly recommended to be included. 
LABEL_FNAME = 'FirstName'
LABEL_LNAME = 'LastName'
LABEL_PHONE = 'Telephone'
LABEL_URL = 'URL' # satellite tracking page 
LABEL_TRACKER = 'Tracker' # ID for tracker such as Flymaster Live Tracker, or code for trackupload
LABEL_GLIDER_MFG = 'GliderManufacturer'
LABEL_GLIDER_MODEL = 'GliderModel'
LABEL_GLIDER_COLORS = 'Colors'
LABEL_GLIDER_RATING = 'Rating' # Glider EN rating
LABEL_EMAIL = 'Email'

# the values below here are not explicitly listed in any HTML right now, but can be referenced by Admin
LABEL_COUNTRY = 'Country'
LABEL_CITY = 'City'
LABEL_STATE = 'State'
LABEL_FAI = 'FAI'
LABEL_DOB = 'DOB'
LABEL_SPONSOR = 'Sponsor'
LABEL_ISPAID = 'IsPaid'

# the following variables are used by the software and should never be modified!!
LABEL_LAT = 'Lat'
LABEL_LON = 'Lon'

