# mix-bot

A replacement bot for the various TF2 pick-up game IRC channels.

### Features

  * Both 6's and Highlander picking, as well as custom class limits.
  * The bot refuses to start picking until a pick is possible.

#### Planned Features

  * Mumble integration, to send a link to each player along with the TF2 server info.
  * Captain picking, with choices limited to prevent an impossible pick situation.
  * Class- and captain-restrictions.
  * PUG histories, possibly influencing the random pick mode to create more even teams.

## Installation

This bot is self-contained. Assuming a Linux server and Python 2.7, all that needs to be done is to `cd` into this directory and run `make install`. This will set up the virtual environment and install any other necessary dependencies, as well as creating the `settings.yml` file if necessary.

### Prerequisites

You will need to install the Python package [`virtualenv`][venv]. On Ubuntu or Debian Linux systems, this can be installed with `sudo apt-get install python-virtualenv`. Other distributions may have their own packages. Otherwise you can install it from the [official site][venv install].

### Configuration

The bot's configuration is stored in `settings.yml`. The default file is documented and relatively straightforward. You'll want to change the `network -> channel` and `network -> bot names` settings before firing up the bot. You'll also want to configure the `servers` list.

If the channel is dedicated to sixes, you'll want to change that part in `rules -> mode`.

### Run it

Once that is set up, simply `make run` to run the bot. You should probably do this in a `tmux` or `screen` session so the bot doesn't die when you disconnect from the server it's installed on.

[venv]: http://www.virtualenv.org/
[venv install]: http://www.virtualenv.org/en/latest/#installation
