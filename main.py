import logging
import json
import subprocess
import re
import shutil
from time import sleep
from random import choice
from pathlib import Path
from datetime import datetime, timedelta
from argparse import ArgumentParser

import requests
from dynaconf import settings
import undetected_chromedriver as uc

from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip


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


def get_video(day):
    video_dir = Path(settings.get('VIDEOS', 'videos')).resolve()
    video_dir.mkdir(parents=True, exist_ok=True)
    logger.debug('video dir: %s', video_dir)
    return video_dir / '{}.mp4'.format(day)


def get_video_raw(day=None):
    video_dir = Path(settings.get('VIDEOS_RAW', 'videos_raw')).resolve()
    logger.debug('raw video dir: %s', video_dir)
    videos = [x for x in video_dir.iterdir() if x.is_file()]
    if videos:
        return choice(videos)
    return None


def get_browser():
    options = uc.ChromeOptions()
    options.add_argument('user-data-dir=' + settings.get('SELENIUM_DIR', 'data/selenium'))
    if settings.get('SELENIUM_HEADLESS', False):
        options.add_argument('--no-sandbox')
        options.add_argument('--headless')
    browser = uc.Chrome(options=options)
    browser.implicitly_wait(5)
    return browser


def runalyze_login(browser, username, password):
    browser.get('https://runalyze.com/dashboard')
    sleep(2)
    try:
        browser.find_element_by_xpath('/html/body/div[1]/div/a').click()
        sleep(2)
    except:
        logger.debug('no cookies')
    if browser.current_url.find('dashboard') > 0:
        return
    browser.find_element_by_xpath('//*[@id="username"]').send_keys(username)
    browser.find_element_by_xpath('//*[@id="password"]').send_keys(password)
    browser.find_element_by_xpath('/html/body/div[2]/div/div[2]/form/div[2]/input[3]').click()
    sleep(2)


def runalyze_search(browser, start_date):
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


def runalyze_iter(username, password, start_date):
    """
    iterate over my running units with selenium
    return [now, datime, distance[km], duration[sec]]
    """
    browser = get_browser()
    runalyze_login(browser, username, password)
    for item in runalyze_search(browser, start_date):
        yield item
    browser.close()


def txt_clip(text, pos=0.1, size=100, color='white'):
    txt_clip = TextClip(text, fontsize=size, color=color, stroke_color='black', stroke_width=3.5, font='Noto-Sans-Black')
    txt_clip = txt_clip.set_position(("center", pos), relative=True)
    return txt_clip


def tiktok_allowed_agents():
    regex = re.compile(r'(?:User-agent: (\w+)+\n)|(?:(Allow: /)\n)')

    reply = requests.get('https://www.tiktok.com/robots.txt')
    assert reply.status_code == 200

    results = regex.findall(reply.text)
    limit = results.index(('', 'Allow: /'))

    return [item[0] for index, item in enumerate(results) if index < limit]


def tiktok_login(browser):
    browser.get('https://www.tiktok.com/foryou')
    while True:
        try:
            browser.find_element_by_xpath('//*[@id="main"]/div[1]/div/div[3]/div[4]/span/span/img')
            break
        except:
            sleep(2)
    logger.info('login to tiktok')


def tiktok_uploade(browser, path, text):
    browser.get('https://www.tiktok.com/upload?lang=en')
    uploade = browser.find_elements_by_class_name('upload-btn-input')[0]
    uploade.send_keys(str(path))
    while True:
        try:
            browser.find_element_by_xpath('//*[@id="main"]/div[2]/div/div[2]/div[3]/div[3]/div[2]/div[1]/img[8]')
            break
        except:
            sleep(2)
    sleep(1)
    caption = browser.find_element_by_xpath('//*[@id="main"]/div[2]/div/div[2]/div[3]/div[1]/div[1]/div[2]/div/div[1]/div/div/div/div/div/div')
    caption.send_keys(text)
    sleep(1)
    browser.find_element_by_xpath('//*[@id="main"]/div[2]/div/div[2]/div[3]/div[6]/button[2]').click()
    sleep(2)


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
        for item in runalyze_iter(settings.SPORT_USER, settings.SPORT_PASS, offset):
            if not any([item[1] == itemm[1] for itemm in data]):
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
    if not day:
        day = get_current_day()
    video_file = get_video(day)
    if video_file.is_file():
        logger.info('video already create')
        return False
    data = get_data(day)
    total = get_total_km(day)
    raw_video = get_video_raw(day)
    logger.info('create video for day=%i, date=%s, total=%fkm, raw_video=%s', day, data[1], total, raw_video)

    if raw_video is None:
        logger.info('Exit no raw video')
        return False

    tmp_file = Path('tmp.mp4').resolve()
    subprocess.run(['ffmpeg', '-i', str(raw_video), '-metadata:s:v', 'rotate="0"', '-c:v', 'libx264', '-crf', '23', '-acodec', 'copy', '-y', str(tmp_file)])
    raw_video.unlink()

    clip = VideoFileClip(str(tmp_file))
    clip = clip.subclip(0, 14.9)
    frame = clip.get_frame(2)
    if frame.shape[0] < frame.shape[1]:
        logger.info('rotate clip')
        clip = clip.rotate(-90)
    frame = clip.get_frame(2)
    video = CompositeVideoClip([
        clip,
        txt_clip('Day', 0.09, 100).set_start(0).set_duration(2),
        txt_clip(str(day), 0.11, 450).set_start(0.5).set_duration(1.5),

        txt_clip('of', 0.09, 100).set_start(3).set_duration(2),
        txt_clip('100', 0.11, 450).set_start(3).set_duration(2),
        txt_clip('days running', 0.38, 100).set_start(3).set_duration(2),

        txt_clip('today', 0.09, 100).set_start(6).set_duration(2),
        txt_clip(str(data[2]), 0.14, 350).set_start(6.5).set_duration(1.5),
        txt_clip('km', 0.4, 80).set_start(6).set_duration(2),

        txt_clip('total', 0.09, 100).set_start(8).set_duration(2),
        txt_clip(str(total), 0.14, 350).set_start(8.5).set_duration(1.5),
        txt_clip('km', 0.4, 80).set_start(8).set_duration(2),

        txt_clip('remaining', 0.09, 100).set_start(10).set_duration(2),
        txt_clip(str(100 - day), 0.14, 350).set_start(10.5).set_duration(1.5),
        txt_clip('days', 0.4, 80).set_start(10).set_duration(2),
    ])
    video.write_videofile(str(video_file))
    return True


def uploade(day=None):
    if not day:
        day = get_current_day()
    video_file = get_video(day)
    if not video_file.is_file():
        logger.info('no video for current day')
        return False
    logger.info('upload video to tiktok')
    browser = get_browser()
    tiktok_login(browser)
    tiktok_uploade(browser, video_file, 'Day {} of 100 days running. #running #100DayChallenge #fyp #loveyoutiktok'.format(day))
    sleep(1)
    browser.close()
    return True


def login():
    browser = get_browser()
    tiktok_login(browser)
    sleep(1)
    browser.close()


def bot():
    logger.info('running bot')
    while True:
        try:
            current_day = get_current_day()
            update()
            if create(current_day):
                uploade(current_day)
            for i in range(60 * 60):
                sleep(1)
        except Exception as e:
            logger.error(str(e))


def clear_browser():
    path = Path('selenium-data').resolve()
    shutil.rmtree(path)


def parse_args():
    parser = ArgumentParser(description='Automate my 10 day running reports')
    parser.add_argument('-v', '--verbose', action='count', help='verbose level... repeat up to three times.')
    parser.add_argument('action', nargs='?', choices=['update', 'status', 'create', 'uploade', 'bot', 'clear', 'login'])
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
        'clear': clear_browser,
        'login': login,
    }
    parser, args = parse_args()
    setup_logger(args.verbose)

    if args.action in funcs:
        funcs[args.action]()
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
