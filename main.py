# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from apscheduler.schedulers.background import BackgroundScheduler
from scrap_request import load_url_from_queue, get_content_page
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor
import time
import logging
import sys
import traceback
import argparse

formatter = logging.Formatter(
    "[%(name)s][%(levelname)s][PID %(process)d][%(asctime)s] %(message)s",
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("Scrap_Ufal")
level_debug = logging.DEBUG
logger.setLevel(level_debug)
file_handler = logging.StreamHandler()
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)



if __name__ == '__main__':
    executors = {
        'default': ThreadPoolExecutor(5),
        'processpool': ProcessPoolExecutor(5)
    }

    job_defaults = {
        'coalesce': False,
        'max_instances': 3
    }

    # logScheduller = logging.getLogger('Scrap_Ufal.Scheduler--')
    # logScheduller.setLevel(level_debug)

    scheduler = BackgroundScheduler(logger=logger, executors=executors, job_defaults=job_defaults)
    parser = argparse.ArgumentParser(description="Set a Url to crawler")
    parser.add_argument('-u', '--url', type=str,
                        help="Url to search notas_empenhos")

    parser.add_argument('-b', '--batch', type=int, choices=range(1, 21),
                        help="How many urls will be loaded inside the queue")

    args = parser.parse_args()
    if not args.url:
        raise Exception("Url not passed, please set a url in arguments")
    
    url = args.url
    batch = args.batch

    url_on_queue = lambda: load_url_from_queue(int(batch))

    try:
        visited_links = [url]
        #get_content_page(url, visited_links=visited_links)
        url_on_queue()
    except Exception as e:
        traceback.print_exc()
        logger.debug("Error on load content on url passed")
        sys.exit(1)

    scheduler.add_job(url_on_queue, trigger='interval', seconds=11)
    scheduler.start()

    try:
        while True:
            time.sleep(1000)

    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()