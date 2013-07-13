import functools
import shlex
from twisted.words.protocols import irc
from twisted.internet import reactor, protocol

import brain

__all__ = ['bot_command', 'run_bot_with_settings']

COMMANDS = {}

def bot_command(*names, **options):
    def decorator(cmd):
        @functools.wraps(cmd)
        def inner(bot, message):
            result = cmd(bot, message)

            if isinstance(result, basestring):
                result = [result]
            elif result is None:
                result = []
            elif not hasattr(result, '__iter__'):
                result = [result]

            if options.get('reply', False):
                result = ('%s: %s' % (message.from_nick, r) for r in result)

            return result

        for name in names:
            COMMANDS[name] = {'handler': inner, 'options': options}
        return inner
    return decorator

class Bot(object):
    def __init__(self, my_brain, rules):
        self.brain = my_brain
        self.rules = rules

class Message(object):
    def __init__(self, args, from_nick, is_pm):
        # args[0] is the command name (without prefix), and args[1:] is the rest
        self.args = args
        self.from_nick = from_nick
        self.is_pm = bool(is_pm)

class IRCMessenger(irc.IRCClient, object):
    def __init__(self, factory, *args, **kwargs):
        super(IRCMessenger, self).__init__(*args, **kwargs)
        self.factory = factory
        self.should_dispatch = False
        self.nickname = 'TF2Bot'

    def __repr__(self):
        return 'IRCMessenger(nickname=%r)' % self.nickname

    def dataReceived(self, bytes):
        # print 'Got data: %r' % bytes
        return super(IRCMessenger, self).dataReceived(bytes)

    def send_message(self, channel, message):
        if isinstance(message, unicode):
            message = message.encode('utf-8')

        if channel == self.nickname:
            # No need to queue these
            self.msg(channel, message)

        # self.queue.append(message)
        self.msg(channel, message)

    def signedOn(self):
        self.factory.transport_connected(self)
        self.join(self.factory.settings['network']['channel'])

    def joined(self, channel):
        print '%s Joined %s' % (self.nickname, channel)

    def privmsg(self, user, channel, msg):
        if not self.should_dispatch:
            return

        user = user.split('!', 1)[0]
        is_pm = channel == self.nickname

        if is_pm:
            channel = user

        if not msg or not msg.startswith('!'):
            return

        self.factory.dispatch(user, channel, msg)

class IRCBotFactory(protocol.ClientFactory):
    def __init__(self, settings, my_brain):
        self.settings = settings
        self.brain = my_brain
        self.bot = Bot(my_brain, rules=settings['rules'])
        self.message_queue = []
        self.transports = []
        self.schedule_send_messages()

    def dispatch(self, user, channel, message):
        assert message.startswith('!'), \
          'Dispatch called with non-command message'

        split = shlex.split(message)
        command = split.pop(0)[1:]

        message = Message(split, user, channel != self.settings['network']['channel'])

        if command not in COMMANDS:
            print 'Saw invalid command %r, not in %r' % (
                command, sorted(COMMANDS.keys()),
            )
            return

        for outbound in COMMANDS[command]['handler'](self.bot, message):
            self.queue_message(message=outbound, channel=channel)

    def queue_message(self, message, channel=None):
        if channel is None:
            channel = self.settings['network']['channel']
        self.message_queue.append({'message': message, 'channel': channel})

    def send_messages(self, index):
        if self.message_queue and self.transports:
            index = (index+1) % len(self.transports)
            try:
                transport = self.transports[index]
                msg = self.message_queue.pop(0)
                transport.send_message(message=msg['message'], channel=msg['channel'])
            except IndexError:
                if index > 0:
                    return send_messages(index=0)
                else:
                    pass
        self.schedule_send_messages(index)

    def schedule_send_messages(self, index=-1):
        transports = len(self.transports) or 1
        reactor.callLater(
            60.0/self.settings['network']['messages per minute']/transports,
            self.send_messages,
            index=index
        )
    def transport_connected(self, transport):
        bot_name = self.bot_names.pop(0)
        if not self.transports:
            transport.should_dispatch = True
        self.transports.append(transport)
        transport.setNick(bot_name)

    def buildProtocol(self, addr):
        p = IRCMessenger(factory=self)
        return p

    def clientConnectionLost(self, connector, reason):
        reconnect_time = self.settings['network']['reconnect time']
        print 'Reconnecting in %i seconds...' % reconnect_time
        reactor.callLater(
            reconnect_time,
            connector.connect,
        )

    def clientConnectionFailed(self, connector, reason):
        reactor.stop()

def run_bot_with_settings(settings):
    factory = IRCBotFactory(settings, brain.make_brain(settings))
    factory.brain.dispatcher = factory
    factory.bot_names = settings['network']['bot names'][:]

    server = settings['network']['server']
    port = settings['network']['port']

    print 'Connecting to %s:%i...' % (server, port)
    for i in xrange(len(factory.bot_names)):
        reactor.callLater(
            i*settings['network']['reconnect time'],
            reactor.connectTCP,
            server,
            port,
            factory,
        )

    reactor.run()
