Here is an overview of the status codes that have been found to be useful. 
Specific codes "supported" (given a specific color-code) are defined in XXX.

FLY
Color: Red
Definition: Should be set for each pilot who checks out to fly, so that they are tracked
by the organizers for both retrieve and safety.
Usage: Can either be set manually at check-out gate or in bulk at HQ.
Important to NOT set to "FLY" any pilots who are absent or choose not to fly.

LOK
Color: Yellow
Definition: Should be set by pilot when they Land OK.
Usage: Pilot satellite tracking device should be configured to send the LOK message,
although it can also be sent manually (but will not have the GPS coordinates).

PUP
Color: Green
Definition: Is set by the pilot or retrieve driver (or even another pilot) when a pilot
is Picked UP.
Usage: Once a pilot is "PUP" then HQ no longer needs to track them: they have both
landed safely and been picked up to be taken to HQ (or wherever they want to go).

SPOT
Color: Purple
Definition: This was created for foreign pilots using the SPOT device, since it was
unable to send valid (parseable) messages to Bowerbird (the messages are
not sent via SMS, but rather an email so are larger than an SMS and the
required elements are not seen).
Usage: HQ/Retrieve need to manually set these pilot's messages to "SPOT"
instead of "FLY" (once they are checked out on launch).

ABS
Color: Grey
Definition: This is for any pilot who is known to be Absent (so they are not
inadvertently thought to be flying or mistakenly thought to have missed the
check-out gate). For example, when a pilot has withdrawn from the competition
(due to injury, or leaving early).
Usage: HQ/Retrieve need to manually set these pilot's messages to "ABS" 
instead of "FLY" (after any mass-update of the system is done).

DNF
Color: Grey
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

ERR
Color: Light Blue
Definition: This is for when a valid pilot number was parsed, but the message
could not be interpreted. (Might be superceded by Dark Blue - will need further
testing to confirm.)
