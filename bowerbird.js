PilotStatus = new Mongo.Collection('pilot_status');

Router.configure({
  layoutTemplate: 'blank',
  notFoundTemplate: 'blank',
  loadingTemplate: 'blank'
});

/*
 * CLIENT SIDE
 */
if (Meteor.isClient) {
  Template.messages.helpers({
    'records' : function() {
      return PilotStatus.find();
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
        // clean everything out of the database...
        PilotStatus.remove({});
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

