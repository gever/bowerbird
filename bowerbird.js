PilotStatus = new Mongo.Collection('pilot_status');

/*
 * CLIENT SIDE
 */
if (Meteor.isClient) {
  // counter starts at 0
  Session.setDefault('counter', 0);

  Template.hello.helpers({
    counter: function () {
      return Session.get('counter');
    }
  });

  Template.hello.events({
    'click button': function () {
      // increment the counter when button is clicked
      Session.set('counter', Session.get('counter') + 1);
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
        // TODO: check to make sure it's coming from Twilio...
        return true;
      }
      // since there is no definition for update or delete,
      // those are automatically denied
    });

    // POST: update pilot status
    Router.route('/ups', {where: 'server'})
      .get(function () {
        this.response.end('get request\n');
      })
      .post(function () {
        var rawIn = this.request.body;
        var pstat = {};

        if (rawIn.Body) {
          pstat.msg = rawIn.Body;
          pstat.source = "sms";
        } else {
          var xml = '<Response><Sms>Found no text in status update.</Sms></Response>';
          return [500, {"Content-Type": "text/xml"}, xml];
        }
        pstat.from = rawIn.From;
        pstat.date = new Date();

        PilotStatus.insert( pstat );

        console.log("jabba:"+pstat.msg);

        this.response.writeHead( 200, {"Content-Type": "text/xml"} );
        this.response.end('<Response><Sms>Acknowledged - %s</Sms></Response>' % (pstat.from));
      });
  });
}

