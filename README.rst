100 Day Running
===============

https://github.com/Zulko/moviepy/issues/401


fix audio: https://github.com/Zulko/moviepy/issues/876#issuecomment-442212509

[default]
START_DAY = '2021-07-31'
SPORT_USER = 'username'
SPORT_PASS = '...'
SELENIUM_HEADLESS = false

sudo apt install ffmpeg imagemagick libatlas-base-dev

sudo apt-get install chromium-browser
sudo apt-get install libminizip1 libwebpmux2 libgtk-3-0


Create the file

.. code-block:: bash

  $ sudo nano /etc/systemd/system/100-days-running.service

with

.. code-block:: init

  [Unit]
  Description=100 days running
  After=multi-user.target

  [Service]
  User=axju
  Group=axju
  WorkingDirectory=/home/axju/projects/100-days-running
  ExecStart=/home/axju/projects/100-days-running/venv/bin/python main.py -v bot
  Restart=always
  RestartSec=60

  [Install]
  WantedBy=multi-user.target

Then enable and start it

.. code-block:: bash

  $ sudo systemctl start 100-days-running
  $ sudo systemctl status 100-days-running
  $ sudo journalctl -u 100-days-running
  $ sudo systemctl enable 100-days-running
  $ sudo systemctl daemon-reload
