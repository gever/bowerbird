PilotStatus = new Mongo.Collection('pilot_status');
Pilots = new Mongo.Collection('pilots');

// map status codes to css styles
StatusMap = {
  'FLY':'status_flying',
  'LOK':'status_landed',
  'PUP':'status_pickedup',
  'FIN':'status_fin',
  'AID':'status_aid',
  'RZA':'status_assigned',
  'RZB':'status_assigned',
  'RZC':'status_assigned',
  'RZD':'status_assigned',
  'NOT':'status_nottracked',
  'UNK':'status_unknown'
};

// TODO: not sure this is needed anymore
Router.configure({
  layoutTemplate: 'main',
  notFoundTemplate: 'blank',
  loadingTemplate: 'blank'
});

Router.route('/', {
  name: 'home',
  template: 'messages'
});

Router.route('/log', {
  name: 'log',
  template: 'messages'
});

Router.route('/overview', function () {
  this.render('overview', {
    data: function () {
      return Pilots.find({});
    }
  });
});

Router.route('/pilotview/:pid', function () {
  this.render('pilotview', {
    data: function () {
      var p = Pilots.findOne({id: parseInt(this.params.pid)});
      // console.log("for " + this.params.pid + " found " + JSON.stringify(p) );
      return p;
    }
  });
});

/*
 * CLIENT SIDE
 */
if (Meteor.isClient) {
  Template.messages.helpers({
    'records' : function() {
      return PilotStatus.find();
      },
  });
  Template.overview.helpers({
    'pilots' : function() {
      // return Pilots.find({sort: {id:1}});
      return Pilots.find({}, {sort: {id: 1}});
    },
    'styling' : function(st) {
      return StatusMap[st];
    }
  });
  Template.pilotview.helpers({
    'styling' : function(st) {
      return StatusMap[st];
    },
    'pilotupdates' : function(pid) {
      var list = PilotStatus.find({pilotID:parseInt(pid)}, {sort: {date:1}});
      // console.log( "pilotupdates: with " + pid + ", found " + JSON.stringify(list) );
      return list;
    }
  });
}

/*
 * SERVER SIDE
 */
if (Meteor.isServer) {

  Meteor.startup(function () {
    // code to run on server at startup
    PilotStatus.allow({
      insert: function (userId, post) {
        return true;
      }
      // since there is no definition for update or delete,
      // those are automatically denied
    });

    Router.route('/reset-really', {where:'server'})
      .get(function() {
        // clean everything out of the databases...
        console.log('resetting status message database');
        PilotStatus.remove({});
      });

    Router.route('/reload-pilots', {where:'server'})
      .get(function() {
        // clean out and reload the pilot database
        Pilots.remove({});
        var text = Assets.getText('pilot_list.csv');
        var plist = Baby.parse(text, {header:true});
        console.log( "plist length: " + plist.data.length );
        // console.log( plist );
        var skipCount = 0;
        for(var i=0; i<plist.data.length; i++) {
          record = plist.data[i]
          if (record.hasOwnProperty('Name')) {
            record.id = parseInt(record.id, 10);

            // default current status to NOT currently tracked
            record.current_status = "NOT";

            // default current location to unknown
            record.current_lat = 0;
            record.current_lon = 0;

            Pilots.insert( record );
          } else {
            skipCount++;
          }
        }
        if (skipCount > 0) {
          console.log("Skipped " + skipCount + " incomplete records.");
        }
        // TODO: index the pilot records by id
        // console.log( Pilots.findOne({id:7}) );
        this.response.writeHead( 200, {"Content-Type": "text/text"} );
        this.response.end('Okey doke.');
      });

    // GET: dump a pilot status record
    Router.route('/debug/:pid', {where: 'server'})
      .get(function () {
        var msg = "";
        msg = "<html><head></head><body><pre>";
        msg += JSON.stringify(Pilots.findOne({id:parseInt(this.params.pid)}), true, 2);
        msg += "</pre></body></html>";
        this.response.writeHead( 200, {"Content-Type": "text/html"} );
        this.response.end(msg);
      });

    // POST: update pilot status
    Router.route('/ups', {where: 'server'})
      .get(function () {
        this.response.end('get request\n');
      })
      .post(function () {
        // TODO: check to make sure it's coming from Twilio...
        var rawIn = this.request.body;
        var pstat = {};

        if (rawIn.Body) {
          // save the raw, unparsed message (for possible later analysis)
          pstat.msg = rawIn.Body.trim();
          pstat.source = "sms";   // what we know so far
        } else {
          // early error detection
          var xml = '<Response><Sms>Found no text in status update.</Sms></Response>';
          return [500, {"Content-Type": "text/xml"}, xml];
        }

        // deconstruct and parse the message contents
        var parts = null;

        // first, let's see if we can find a pilot ID & message
        var pilotID = -1;
        var pilotMsg = null;
        if (pstat.msg.match(/^FRM/)) {
          // SPOT message - somewhere there's a hashtag...
          //   followed by digits
          //   followed by a three letter status token
          parts = pstat.msg.match(/#([0-9]+) ([A-Z|a-z]{3})/);
          if (parts && parts.length != 3) {
            // every message must have at least a pilot ID and status token
            var xml = '<Response><Sms>Unparsable message body:\'' + pstat.msg + '\'</Sms></Response>';
            console.log( xml );
            return [500, {"Content-Type": "text/xml"}, xml];
          }
          pilotID = parseInt( parts[1] );
          pilotMsg = parts[2].toUpperCase();
        } else {
          // DeLorme or handcrafted message
          parts = pstat.msg.split(" ");
          if (parts.length < 2) {
            // every message must have at least a pilot ID and status token
            var xml = '<Response><Sms>Unparsable message body:\'' + pstat.msg + '\'</Sms></Response>';
            console.log( xml );
            return [500, {"Content-Type": "text/xml"}, xml];
          }

          var wip = String(parts[0]);
          if (wip.substring(0,1) == "#") {
            pilotID = parseInt( wip.substring(1) );
          } else {
            pilotID = parseInt( wip );
          }
          pilotMsg = parts[1].toUpperCase();
        }

        // second, look for lat/lon on LOK and PUP messages
        var got_ll_update = false;
        var pilotNotes = "";
        if ((pilotMsg == "LOK") || (pilotMsg == "PUP")) {
          var ll = pstat.msg.match(/([-]*[0-9]+\.[0-9]+),[ ]*([-]*[0-9]+\.[0-9]+)/);
          if ((ll != null) && (ll.length == 3)) {
            console.log("ll = " + ll.length + ", " + JSON.stringify(ll)); 
            pstat.current_lat = parseFloat(ll[1]);
            pstat.current_lon = parseFloat(ll[2]);
            got_ll_update = true;
          }
          if (parts.length > 2)
            pilotNotes = parts.slice(2).join(" ");
        }

        pstat.current_status = pilotMsg;
        pstat.pilotID = pilotID;
        pstat.notes = pilotNotes;
        pstat.from = rawIn.From;
        pstat.date = new Date();

        // add a new record to the status database
        PilotStatus.insert( pstat );

        // update the corresponding record to show latest status
        if (got_ll_update) {
          Pilots.update(
            { id: pstat.pilotID },
            { $set: {
              current_status: pstat.current_status,
              date: pstat.date,
              current_lat: pstat.current_lat,
              current_lon: pstat.current_lon
              }
            });
        } else {
          Pilots.update(
            { id: pstat.pilotID },
            { $set: {
              current_status: pstat.current_status,
              date: pstat.date
              }
            });
        }

        // debug
        // console.log("pstat:" + pstat);
        console.log("received and parsed:" + pstat.msg);

        this.response.writeHead( 200, {"Content-Type": "text/xml"} );
        this.response.end('<Response><Sms>Acknowledged - ' + pstat.from + '</Sms></Response>');
      });
  });
}

