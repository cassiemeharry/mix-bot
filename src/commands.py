from network import bot_command

@bot_command('list')
def player_list(bot, message):
    return 'Players added: %s' % ', '.join(bot.brain.players_added())

@bot_command('add')
def add(bot, message):
    classes = [c for c in message.args if c in bot.rules['valid classes']]
    if not classes:
        return
    bot.brain.player_set_added_classes(message.from_nick, classes)
    return player_list(bot, message)

@bot_command('remove')
def remove(bot, message):
    bot.brain.player_remove(message.from_nick)
    return player_list(bot, message)

@bot_command('list-classes')
def list_classes(bot, message):
    valid_classes = bot.rules['valid classes']
    template = '%%%is: %%s' % (max(len(c) for c in valid_classes) + 1)
    added = bot.brain.players_by_class()
    for cls in valid_classes:
        yield template % (cls, ', '.join(added.get(cls, [])))

@bot_command('can-pick?', 'can-pick', reply=True)
def can_pick(bot, message):
    return 'Yes' if bot.brain.can_pick() else 'No'

@bot_command('pick')
def pick(bot, message):
    if not bot.brain.can_pick():
        yield "Picking can't start right now"
    elif bot.rules['picking'] == 'random':
        teams = bot.brain.random_pick()
        team_colors = {'red': '4', 'blu': '2'}
        for team_name, player_mapping in teams.items():
            players = []
            for player, cls in sorted(player_mapping.items(), key=lambda pair: (bot.rules['valid classes'].index(pair[1]), pair[0])):
                bot.brain.player_remove(player)
                players.append('%s: %s' % (player, cls))
            yield '\x03%i%s Team\x03: %s' % (team_colors[team_name], team_name, ', '.join(players))
    else:
        yield 'Captain picking not implemented yet, sorry :('

@bot_command('need')
def need(bot, message):
    return bot.brain.classes_needed()
