import logging
import json
from time import sleep
from pathlib import Path
from datetime import datetime, timedelta
from argparse import ArgumentParser

from dynaconf import settings
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from chromedriver_autoinstaller import install as chromedriver_installer

logger = logging.getLogger(__name__)


def get_data(day=-1):
    data_file = Path(settings.get('DATA_FILE', 'data.json'))
    if data_file.is_file():
        try:
            with data_file.open() as f:
                data = [[datetime.strptime(item[0], '%Y-%m-%d %H:%M:%S'), datetime.strptime(item[1], '%Y-%m-%d %H:%M:%S')] + item[2:] for item in json.load(f)]
                if day - 1 in range(len(data)):
                    return data[day - 1]
                return data
        except Exception as e:
            logger.error('broken data file: %s', str(e))
    return []


def save_data(data):
    data_file = Path(settings.get('DATA_FILE', 'data.json'))
    data.sort(key=lambda x: x[1])
    with data_file.open('w') as f:
        json.dump(data, f, default=str)


def get_current_day():
    start_day = datetime.strptime(settings.START_DAY, '%Y-%m-%d').date()
    return (datetime.now().date() - start_day).days + 1


def get_total_km(day=None):
    data = get_data()
    if day:
        data = data[:day]
    return sum([item[2] for item in data])


def get_raw_video(day=None):
    video_dir = Path(settings.get('RAW_VIDEO', 'raw_video'))
    videos = [x for x in video_dir.iterdir() if x.is_file()]
    print(videos)


def iter_runalyze(username, password, start_date):
    """
    iterate over my running units with selenium
    return [now, datime, distance[km], duration[sec]]
    """
    chromedriver_installer()
    options = Options()
    # options.add_argument("user-data-dir=selenium")
    browser = webdriver.Chrome(options=options)
    browser.implicitly_wait(5)
    browser.get('https://runalyze.com/login')
    sleep(5)
    try:
        browser.find_element_by_xpath('/html/body/div[1]/div/a').click()
        sleep(2)
    except:
        print('no ...')
    # elem = browser.find_element_by_class_name('login_email')
    # elem = browser.find_element_by_name('username')
    browser.find_element_by_xpath('//*[@id="username"]').send_keys(username)
    browser.find_element_by_xpath('//*[@id="password"]').send_keys(password)
    browser.find_element_by_xpath('/html/body/div[2]/div/div[2]/form/div[2]/input[3]').click()
    sleep(2)

    browser.get('https://runalyze.com/my/search')
    sleep(2)
    elem = browser.find_element_by_xpath('//*[@id="date-from"]')
    elem.clear()
    elem.send_keys(start_date.strftime("%d.%m.%Y"))
    browser.find_element_by_xpath('//*[@id="search_legend_0"]/div[50]/input').click()
    sleep(2)

    table = browser.find_element_by_xpath('//*[@id="searchResult"]/table')
    for row in table.find_elements_by_xpath(".//tr"):
        row_data = [td.text for td in row.find_elements_by_xpath(".//td")]
        if row_data[0] == '':
            continue
        minutes, secends = row_data[6].split(':')
        yield [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            datetime.strptime(row_data[0] + row_data[16], '%d.%m.%Y%H:%M'),
            float(row_data[3].split()[0].replace(',', '.')),
            int(minutes) * 60 + int(secends)
        ]
    browser.close()


def update():
    """update my running data"""
    logger.info('start update')
    data = get_data()
    start_day = datetime.strptime(settings.START_DAY, '%Y-%m-%d').date()
    day = get_current_day()
    logger.info('update day %i %s', day, start_day)
    if len(data) < day:
        logger.info('check for new data')
        offset = start_day + timedelta(days=len(data) - 1)
        for item in iter_runalyze(settings.SPORT_USER, settings.SPORT_PASS, offset):
            logger.info('add new date item for %s', item[1])
            data.append(item)
    else:
        logger.info('nothing to do')
    save_data(data)


def status():
    data = get_data()
    print('days: ', len(data))
    print('total:', sum([item[2] for item in data]), 'km')
    print('total:', timedelta(seconds=sum([item[3] for item in data])))


def create(day=None):
    logger.info('create video')
    if not day:
        day = get_current_day()
    data = get_data(day)
    total = get_total_km(day)
    video_file = get_raw_video(day)
    print(video_file)


def uploade():
    logger.info('upload video')


def bot():
    logger.info('running bot')
    while True:
        try:

            for i in range(60 * 60):
                sleep(1)
        except Exception as e:
            logger.error(str(e))


def parse_args():
    parser = ArgumentParser(description='Automate my 10 day running reports')
    parser.add_argument('-v', '--verbose', action='count', help='verbose level... repeat up to three times.')
    parser.add_argument('action', nargs='?', choices=['update', 'status', 'create', 'uploade', 'bot'])
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
        'status': status,
        'create': create,
        'uploade': uploade,
        'bot': bot,
    }
    parser, args = parse_args()
    setup_logger(args.verbose)

    if args.action in funcs:
        funcs[args.action]()
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
