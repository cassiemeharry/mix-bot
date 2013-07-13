from os import path
import yaml

def _deep_merge(original, update_with):
    result = {}
    all_keys = set(original.keys()) | set(update_with.keys())
    for key in all_keys:
        if key not in original:
            result[key] = update_with[key]
        elif key not in update_with:
            result[key] = original[key]
        elif isinstance(original[key], dict) and isinstance(update_with[key], dict):
            result[key] = _deep_merge(original[key], update_with[key])
        else:
            result[key] = update_with[key]
    return result

class SettingsError(ValueError):
    pass

DEFAULT_BASE_SETTINGS = {
    'rules': {
        'picking': 'random',
        'mode': 'highlander',
    },
    'network': {
        'port': 6667,
        'reconnect time': 15,
        'messages per minute': 20,
    },
    'database': {
        'type': 'sqlite',
        'name': 'bot.sqlite',
    },
}

HIGHLANDER_SETTINGS = {
    'rules': {
        'mode': 'highlander',
        'class limits': {
            'scout': 1,
            'soldier': 1,
            'pyro': 1,
            'demo': 1,
            'heavy': 1,
            'engineer': 1,
            'medic': 1,
            'sniper': 1,
            'spy': 1,
        },
        'valid classes': (
            'scout',
            'soldier',
            'pyro',
            'demo',
            'heavy',
            'engineer',
            'medic',
            'sniper',
            'spy',
        )
    },
}

SIXES_SETTINGS = {
    'rules': {
        'mode': 'sixes',
        'class limits': {
            'scout': 2,
            'soldier': 2,
            'demo': 1,
            'medic': 1,
        },
        'valid classes': (
            'scout',
            'soldier',
            'demo',
            'medic',
        )
    },
}

def validate_settings(settings):
    mode = settings['rules']['mode']
    if mode == 'highlander':
        settings['rules']['class limits'] = HIGHLANDER_SETTINGS['rules']['class limits']
        settings['rules']['valid classes'] = HIGHLANDER_SETTINGS['rules']['valid classes']
    elif mode == 'sixes':
        settings['rules']['class limits'] = SIXES_SETTINGS['rules']['class limits']
        settings['rules']['valid classes'] = SIXES_SETTINGS['rules']['valid classes']
    elif mode == 'custom':
        if 'class limits' not in settings['rules']:
            raise SettingsError('Custom pick mode requires rules -> class limits to be configured')
        if 'valid classes' not in settings['rules']:
            settings['rules']['valid classes'] = sorted(settings['rules']['class limits'].keys())
    else:
        raise SettingsError('Invalid setting rules -> mode, must be one of "highlander", "sixes", or "custom", not "%s"' % mode)

    picking = settings['rules']['picking']
    if picking == 'random':
        pass
    elif picking == 'captain':
        raise SettingsError("Captain picking isn't supported yet")
    else:
        raise SettingsError('Invalid setting rules -> picking, must be one of "random" or "captain", not "%s"' % picking)

    return settings

def load_settings(filename=None):
    if filename is None:
        filename = path.abspath(path.join(path.dirname(__file__), '..', 'settings.yml'))

    with open(filename) as f:
        settings = yaml.load(f)

    settings = _deep_merge(DEFAULT_BASE_SETTINGS, settings)
    settings = validate_settings(settings)

    return settings
