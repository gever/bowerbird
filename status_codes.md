Here is an overview of the status codes that have been found to be useful. 
Specific codes "supported" (given a specific color-code) are defined in bowerbird.css.



**FLY**
Color: Red (#FF5050)
Definition: Should be set for each pilot who checks out to fly, so that they are tracked
by the organizers for both retrieve and safety.
Usage: Can either be set manually at check-out gate or in bulk at HQ.
Important to NOT set to "FLY" any pilots who are absent or choose not to fly.

**LOK**
Color: Light Yellow (#FFA)
Definition: Should be set by pilot when they Land OK.
Usage: Pilot satellite tracking device should be configured to send the LOK message,
although it can also be sent manually (but will not have the GPS coordinates).

**PUP**
Color: Green (#3C3)
Definition: Is set by the pilot or retrieve driver (or even another pilot) when a pilot
is Picked UP.
Usage: Once a pilot is "PUP" then HQ no longer needs to track them: they have both
landed safely and been picked up to be taken to HQ (or wherever they want to go).

**AID**
Color: Pink (#F6C)
Definition: Indicates that the pilot in question requires assistance (AID).
Usage: Pilot satellite tracking device should be set to send this message if they need assistance. Note
that this is separate from the SOS feature of the device (must be a specific message). Further, other
pilots who are helping can send this message for the pilot requiring aid - preferably via SMS, or via some
other form of communication with HQ.
Note: A pilot should not send their OWN "AID" message to try to get HQ attention for another pilot - this
tends to result in confusion and concern that there are multiple pilots requiring aid. Instead they should
use the MSG code.

**MSG**
Color: Medium Blue (#009eff)
Definition: If a pilot needs to communicate with HQ and has no ability to phone/radio. HQ must open the Log or
pilot status details to find out what it says.
Usage: The transmission still needs to be in a valid
format (with a pilot number and the MSG code), but the rest of the line can be a message (such as: I am with
pilot 404 who requires AID). Note that using a satellite tracking device means the GPS coordinates will also be sent.


**GOL**
Color: Tan (#c4c483)
Definition: Landed in Goal, but not yet confirmed in a vehicle (PUP).
Usage: Set by HQ/volunteer to track all of the pilots who are known to be in Goal, since 
many of them seem to believe they don't need to press "LOK" in that situation. 
Note: that these same pilots also likely will not send a PUP message once in a vehicle, but
they will certainly make some noise if they get left at goal! So any vehicle leaving Goal
should be sure to send PUP for all passengers.

**SPOT**
Color: Purple (#9595f9)
Definition: This was created for foreign pilots using the SPOT device, since it was
unable to send valid (parseable) messages to Bowerbird (the messages are
not sent via SMS, but rather an email so are larger than an SMS and the
required elements are not seen by the Bowerbird system).
Usage: HQ/Retrieve need to manually set these pilot's messages to "SPOT"
instead of "FLY" (once they are checked out on launch).

**ABS**
Color: Grey/Default (#DDD)
Definition: This is for any pilot who is known to be Absent (so they are not
inadvertently thought to be flying or mistakenly thought to have missed the
check-out gate). For example, when a pilot has withdrawn from the competition
(due to injury, or leaving early).
Usage: HQ/Retrieve need to manually set these pilot's messages to "ABS" 
instead of "FLY" (after any mass-update of the system is done).

**DNF**
Color: Grey/Default (#DDD)
Definition: This is for a pilot who may have checked-out on launch, but then
Did Not Fly.
Usage: After showing red/FLY, the status could directly be set to DNF 
(rather than LOK/PUP). HQ/Retrieve then knows that the pilot is safe and
does not require retrieve.

<RANDOM>
Color: Dark Blue
Definition: This is for any message that can be parsed and has a seemingly valid
pilot number, but with an unknown 3-digit code.
Usage: It is Blue so it is visually apparent. HQ/Retrieve needs to check the
specific message to try to figure out what the correct code should actually be.
(Sometimes the name is before the code, so <RANDOM> is the first three characters
of the pilot's name. Sometimes there is a detailed message the pilot is trying
to send to HQ.)

**ERR**
Color: Light Blue (#affbf9)
Definition: This is for when a valid pilot number was parsed, but the message
could not be interpreted. (Might be superceded by Dark Blue - will need further
testing to confirm.)
Usage: This might only be set manually by HQ/Retrieve - it helps to identify which pilots
need manual tracking (checking the Errors log for communication from them, for example). Similar
to SPOT (although these issues are typically not known in advance).

**<None>**
Color: Grey/Default (#DDD)
Definition: Previously used "NOT", but for visual simplicity the default state of the board when reset
is no status at all. This is the same as "not yet flying or checked in or anything".
Usage: Reset of the board each morning sets all pilots to no status. (Then either the wholesale FLY + ABS/SPOT adjustments
are made, or individually check-out pilots are updated.)
  
**FIN**
Color: Green text on White background (#3C3)
Definition: Previously this meant "done", but that was when people had to check-in at HQ even after PUP.
Usage: If an event decides to require that participants must perform some sort of check-in action
after PUP then this code would be used. Most comps have chosen to allow "PUP" to be sufficient with respect
to retrieve/safety, and submitting a tracklog is sufficient for confirming participation in the race that day.

**ASK**
Color: Bright Yellow (#FFF200)
Definition: ASK at HQ to find out what is up.
Usage: There is a problem with the Bowerbird/tracker configuration or pilot's usage. So pilot needs to come to HQ/Retrieve
to resolve.

**SMB**
Color: Orange (#ff9d00)
Definition: See Mary Beth
Usage: Uh-oh. You're in trouble now!
