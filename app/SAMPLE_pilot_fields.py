# pilot status record field names (trying to isolate from CSV dependencies a little bit)
LABEL_PNUM = 'Pilot#' # space gets removed when all column header spaces are removed in parse_pilot_record
LABEL_STATUS = 'STATUS'
LABEL_FNAME = 'FirstName'
LABEL_LNAME = 'LastName'
LABEL_PHONE = 'Telephone'
LABEL_LAT = 'Lat'
LABEL_LON = 'Lon'
LABEL_URL = 'URL' # satellite tracking page 
LABEL_TRACKER = 'Tracker' # ID for tracker such as Flymaster Live Tracker, or code for trackupload
LABEL_GLIDER_MFG = 'GliderManufacturer'
LABEL_GLIDER_MODEL = 'GliderModel'
LABEL_GLIDER_COLORS = 'Colors'
LABEL_GLIDER_RATING = 'Rating' # Glider EN rating
LABEL_EVENT = 'Event'
# the values below here are not explicitly listed in any HTML right now, i believe
LABEL_COUNTRY = 'Country'
LABEL_CITY = 'City'
LABEL_STATE = 'State'
LABEL_EMAIL = 'Email'
LABEL_FAI = 'FAI'
LABEL_DOB = 'DOB'
LABEL_SPONSOR = 'Sponsor'
LABEL_ISPAID = 'IsPaid'

