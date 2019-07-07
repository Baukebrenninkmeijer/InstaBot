from src.scrape_image_data import *
from src.user_data_aggregation import *
from src.upload_image import *
from src.move_to_s3 import *
from src.bot import telegram_bot
import schedule
import traceback
import multiprocessing
import time

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s %(name)-s %(levelname)-s : %(message)s')
fh = logging.FileHandler('logs/runner.log', encoding='utf-8')
fh.setLevel(logging.DEBUG)
fh.setFormatter(formatter)
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)
logger.addHandler(fh)

output_template = f'''
{"#"*40}
#
#       {{}}
#
{"#"*40}
'''
#'''

def insta_scheduler():
    schedule.every().day.at("08:00").do(upload).tag('upload')
    schedule.every().day.at("12:00").do(upload).tag('upload')
    schedule.every().day.at("19:00").do(upload).tag('upload')

    schedule.every().day.at('09:00').do(update_followers).tag('update_followers')
    schedule.every().day.at('10:00').do(update_followers).tag('update_followers')
#     schedule.every(5).hours.do(like_random_posts).tag('like_random_posts')
    schedule.every().week.do(scrape_new_users).tag('scrape users')
    schedule.every().day.at("02:00").do(retrieve_data).tag('retrieve_data')
    schedule.every().day.at("02:30").do(sync_ig_images_to_s3).tag('sync_ig_images_to_s3')
    schedule.every().day.at("02:15").do(retrieve_additional_information).tag('retrieve additional information')
    schedule.every().day.at("02:30").do(check_responses_of_follows).tag('check responses of follows')
    logger.info(output_template.format('Starting Instabot Service'))

    while True:
        try:
            ts = datetime.datetime.now()
            if ts.minute == 0 and ts.second == 0:
                logger.info(f'Service still running...')
            schedule.run_pending()
        except KeyboardInterrupt:
            logger.info(output_template.format('Exiting Instabot Service'))
            exit()
        except Exception as e:
            logger.info(f'{traceback.format_exc()}')
        time.sleep(1)
        

if __name__ == '__main__':
    telegram_bot_proc = multiprocessing.Process(name='telegram_bot', target=telegram_bot)
    insta_scheduler_proc = multiprocessing.Process(name='insta_scheduler', target=insta_scheduler)
    telegram_bot_proc.start()
    insta_scheduler_proc.start()