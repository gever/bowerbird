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
LABEL_GLIDER_MFG = 'GliderManufacturer'
LABEL_GLIDER_MODEL = 'GliderModel'
LABEL_GLIDER_COLORS = 'Colors'
LABEL_GLIDER_RATING = 'Rating' # Glider EN rating
LABEL_SPONSOR = 'Sponsor'
LABEL_ISPAID = 'IsPaid'
LABEL_URL = 'URL' # satellite tracking page 
LABEL_TRACKER = 'Tracker' # ID for tracker such as Flymaster Live Tracker
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
