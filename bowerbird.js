PilotStatus = new Mongo.Collection('pilot_status');
Pilots = new Mongo.Collection('pilots');

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

Router.route('/pilotview', function () {
  this.render('pilotview', {
    data: function () {
      return Pilots.find({});
    }
  });
});
/* Router.route('/all'); */

Router.map( function () {
  this.route('all');
});
Router.map( function () {
  this.route('one');
});
Router.map( function () {
  this.route('admin');
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
  Template.pilotview.helpers({
    'pilots' : function() {
      return Pilots.find();
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
        msg += JSON.stringify(Pilots.findOne({id:12}), true, 2);
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
        var parts = pstat.msg.split(" ");
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
        var pilotMsg = parts[1];
        var pilotNotes = "";
        if (parts.length > 2)
          pilotNotes = parts.slice(2).join(" ");

        pstat.status = pilotMsg;
        pstat.pilotID = parseInt(pilotID);
        pstat.notes = pilotNotes;
        pstat.from = rawIn.From;
        pstat.date = new Date();

        // add a new record to the database
        PilotStatus.insert( pstat );

        // debug
        console.log("received and parsed:" + pstat.msg);
        console.log("pstat:" + pstat);

        this.response.writeHead( 200, {"Content-Type": "text/xml"} );
        this.response.end('<Response><Sms>Acknowledged - ' + pstat.from + '</Sms></Response>');
      });
  });
}

