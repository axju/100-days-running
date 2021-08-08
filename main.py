import logging
import json
from time import sleep
from pathlib import Path
from datetime import datetime
from argparse import ArgumentParser

from dynaconf import settings
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from chromedriver_autoinstaller import install as chromedriver_installer

logger = logging.getLogger(__name__)


def iter_running_units(username, password, start_date):
    """
    iterate over my running units with selenium
    return [now, datime, distance[km], duration[sec]]
    """
    chromedriver_installer()
    options = Options()
    options.add_argument("user-data-dir=selenium")
    browser = webdriver.Chrome(options=options)
    browser.implicitly_wait(5)
    browser.get('https://connect.garmin.com/signin/')
    sleep(2)
    try:
        browser.find_element_by_xpath('/html/body/div/div/div/footer/div[3]/div/div/div/div/div[2]/button[1]').click()
        sleep(1)
    except:
        print('no ...')
    elem = browser.find_element_by_class_name('login_email')
    elem.send_keys(username)

    if False:
        yield [datetime.now()]


def update():
    """update my running data"""
    logger.info('start update')
    data_file = Path(settings.get('DATA_FILE', 'data.json'))
    data = []
    if data_file.is_file():
        with data_file.open() as f:
            data = json.load(f)

    start_day = datetime.strptime(settings.START_DAY, '%Y-%m-%d')
    for item in iter_running_units(settings.SPORT_USER, settings.SPORT_PASS, start_day):
        data.append(item)

    with data_file.open('w') as f:
        json.dump(data, f)


def create():
    logger.info('create video')


def uploade():
    logger.info('upload video')


def parse_args():
    parser = ArgumentParser(description='Automate my 10 day running reports')
    parser.add_argument('-v', '--verbose', action='count', help='verbose level... repeat up to three times.')
    parser.add_argument('action', nargs='?', choices=['update', 'create', 'uploade'])
    args = parser.parse_args()
    return parser, args


def setup_logger(level=0, logger=''):
    '''setup the root logger'''
    logger = logging.getLogger(logger)
    levels = [logging.WARNING, logging.INFO, logging.DEBUG]
    level = levels[min(len(levels) - 1, level or 0)]
    logger.setLevel(level)
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))
    logger.addHandler(ch)


def main():
    funcs = {
        'update': update,
        'create': create,
        'uploade': uploade,
    }
    parser, args = parse_args()
    setup_logger(args.verbose)

    if args.action in funcs:
        funcs[args.action]()
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
