# bowerbird
a pilot status tracking system

## overview
- uses messages from pilots to keep track of where they are and what their status is (flying, landed OK, picked up, etc)

- status is conveyed by specific three-letter codes (FLY, LOK, PUP, SOS, ABS)

- messages can come from satellite tracking devices (such as Delorme InReach or SPOT) or via properly formatted text message.

- the system automatically responds to messages received, so pilots have a confirmation that their status has been updated.

- requires twilio to send/receive text messages.

## set up
### Twilio

### Pilot information in system

### Pilot message configuration
- rather than assuming all pilots will successfully set up their satellite tracking devices correctly, the organizer's time is likely better spent manually setting up devices for every pilot who has not completed a successful test prior to registration.

### Pilot message testing

## usage
### Organizer / Retrieve Coordinator / Safety Director
#### At least a week before the event
- Set up and configure Bowerbird and Twilio
- Communicate device set up to the participants
- Once the system is working make sure everyone tests their device configuration

#### Immediately before the event
- Arrange a time for all participants to come have their devices checked and configured if needed
- Post informational signs with the important numbers and example messages
- Be aware that the message format is sensitive, and many pilots will enter their messsages incorrectly

#### Every morning of the event
- Clear the pilot status messages

#### Before pilots launch
- Have a volunteer on launch that track pilot "check out"
- As each pilot checks out, send the message
FLY #732 Peter Pilot 415-555-1212
- The pilot number will display "FLY" in red, indicating the pilot is in the air
- Note: if cell coverage is poor the messages can be sent later, but this is a critical element of the pilot tracking!

#### As pilots land
- The board will change to "LOK" in yellow as each pilot lands
- The pilot's location can be viewed on the map by clicking the GPS coordinators
- The pilot's location should also appear on the XCFind map
- The Retrieve Coordinator should notify the retrieve driver in the area that a pilot will need pick-up
- Note that the pilot may send an additional LOK message if they move to a different location for pick-up

#### As pilots are picked up
- The board will change to "PUP" in green as each pilot is picked-up
- At that point they should be taken care of and need no more attention

### Pilots / Competitors
#### On launch
- Make sure tracking device is on and tracking
- "Check out" with the appropriate volunteer

#### On landing
- Send the "Landed OK" message (either via satellite tracker or cell phone)
- Example format:
LOK #732 Peter Pilot 415-555-1212

#### After packing up and getting to an appropriate place to be picked up
- Send ANOTHER "Landed OK" message
- This ensures the retrieve driver knows where to find you

#### After getting a ride
- Send the "Picked Up" message (either via satellite tracker or cell phone)
- Example format:
PUP #732 Peter Pilot 415-555-1212
- This lets organizer and retrieve driver know you know you are safe and longer need a ride
- The ride can be in an official retrieve vehicle, with a friend, or public transportation

#### After submitting your tracklog
- You will not be scored until your tracklog has been received by the scorekeeper
- After submitting your tracklog make sure that your pilot number is "green" on the tracking board
-- A tracking board is displayed by the scorekeeper
-- The tracking board is also visible online

- If you are NOT "green" on the tracking board, but you are safely back, then you MUST send the "Picked Up" message via cell phone
- Example format:
PUP #732 Peter Pilot 415-555-1212

