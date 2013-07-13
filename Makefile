run: install
	sh -c '. bin/activate; ./bin/bot'

install: virtualenv requirements settings.yml
	@echo ''
	@echo '* Ok, now "make run" to run the bot, or run "./bin/bot" within the Python virtual environment yourself (with ". bin/activate")'

settings.yml: settings.yml.sample
	cp settings.yml.sample settings.yml
	@echo "* You may wish to edit this file to configure the bot"

requirements: virtualenv requirements.txt
	sh -c '. bin/activate; pip install -r requirements.txt | grep -v "Requirement already satisfied" | grep -v "Cleaning up..." || true'

virtualenv:
	[ -f bin/activate ] || virtualenv .
