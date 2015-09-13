PilotStatus = new Mongo.Collection('pilot_status');
Pilots = new Mongo.Collection('pilots');

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

Router.configure({
  layoutTemplate: 'main',
  notFoundTemplate: 'blank',
  loadingTemplate: 'blank'
});

/* Router.map( function () {
  this.route('home', {
    path: '/',
    template: 'messages'
  });
}); */

Router.route('/', {
  name: 'home',
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
    }
  });
}

/*
 * SERVER SIDE
 */
if (Meteor.isServer) {
  var latlon_re = /[-]*[0-9]+\.[0-9]+/g;

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
    Router.route('/reload-pilots-obsolete', {where:'server'})
      .get(function() {
        // clean out and reload the pilot database
        Pilots.remove({});
        var text = Assets.getText('pilots.json');
        // console.log( text );
        var plist = JSON.parse( text );
        console.log( "plist length: " + plist.length );
        // console.log( plist );
        for(var i=0; i<plist.length; i++) {
          Pilots.insert( plist[i] );
        }
        Pilots.insert( plist );
        console.log( "jabba 2" );
        console.log( Pilots.findOne({}) );
        console.log( "jabba 3" );
        this.response.writeHead( 200, {"Content-Type": "text/text"} );
        this.response.end('Okey doke.');
      });

    Router.route('/debug', {where: 'server'})
      .get(function () {
        var msg = "";
        msg = "<html><head></head><body><pre>";
        msg += JSON.stringify(Pilots.findOne({id:7}), true, 2);
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
          pstat.msg = rawIn.Body;
          pstat.source = "sms";
        } else {
          var xml = '<Response><Sms>Found no text in status update.</Sms></Response>';
          return [500, {"Content-Type": "text/xml"}, xml];
        }

        // deconstruct and parse the message contents
        // var parts = pstat.msg.split(" ");
        var parts = pstat.msg.trim().split(" ");
        if (parts.length < 2) {
          var xml = '<Response><Sms>Unparsable message body:\'' + pstat.msg + '\'</Sms></Response>';
          return [500, {"Content-Type": "text/xml"}, xml];
        }
        var wip = String(parts[0]);
        var pilotID = -1;
        if (wip.substring(0,1) == "#") {
          pilotID = parseInt( wip.substring(1) );
        } else {
          pilotID = parseInt( wip );
        }
        var pilotMsg = parts[1].toUpperCase();

        // look for lat/lon on LOK messages
        var ll = pstat.msg.match(latlon_re);
        console.log("ll = " + ll.length + ", " + JSON.stringify(ll)); 
        var got_ll_update = false;
        if (ll.length == 2) {
          console.log( "Jabba!" );
          pstat.current_lat = parseFloat(ll[0]);
          pstat.current_lon = parseFloat(ll[1]);
          got_ll_update = true;
        }
        var pilotNotes = "";
        if (parts.length > 2)
          pilotNotes = parts.slice(2).join(" ");

        pstat.current_status = pilotMsg;
        pstat.pilotID = parseInt(pilotID);
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
              date: new Date(),
              current_lat: pstat.current_lat,
              current_lon: pstat.current_lon
              }
            });
        } else {
          Pilots.update(
            { id: pstat.pilotID },
            { $set: {
              current_status: pstat.current_status,
              date: new Date()
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

