
#################################################
### THIS FILE WAS AUTOGENERATED! DO NOT EDIT! ###
#################################################
# file to edit: notebooks/3_upload_image.ipynb

import os
import random
import pandas as pd
import logging
import datetime
import re
import ast
import json
import tempfile
import numpy as np
from InstagramAPI import InstagramAPI
from scipy.spatial import distance
from colormath.color_diff import delta_e_cie2000
from colormath.color_conversions import convert_color
from colormath.color_objects import sRGBColor, LabColor
from matplotlib.pyplot import cm, imread, imshow
import sys
sys.path.append('src')
import lib


logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s %(name)-s %(levelname)-s : %(message)s')
fh = logging.FileHandler('logs/upload.log', encoding='utf-8')
fh.setLevel(logging.DEBUG)
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)
logger.addHandler(fh)


io_method = lib.DatabaseIO() #CsvIO
read_data = io_method.read_data
write_data = io_method.write_data
ig_username = lib.ig_username
ig_password = lib.ig_password
artefacts_path = 'artefacts'


def get_closest_color(candidates, last_uploaded, distance_metric=None, top_n=5, test=False):
    assert isinstance(candidates, pd.DataFrame), 'Candidates is not a dataframe'
    if distance_metric is None: distance_metric = delta_e_cie2000
    metadata_colors = candidates.dominant_color.tolist()
    target_color_rgb = get_target_color(test=test)
    target_color = convert_color(sRGBColor(*target_color_rgb), LabColor)

    top_idxs = pd.Series([distance_metric(convert_color(sRGBColor(*np.array(z)/255), LabColor), target_color) for z in metadata_colors])
    top_idxs = top_idxs.sort_values()[:top_n].index.tolist()
    return candidates.iloc[top_idxs], target_color_rgb

def get_target_color(n=150, test=False):
    season = get_season()
    index, last_color = read_data('color_meta').iloc[0]
    index += 1
    cmap = getattr(cm, get_season())(np.linspace(0, 1, 150))[:, :-1]
    t_index = n - (index % n) if index // n % 2 == 1 else index % n
    target_color = cmap[t_index]
    new_color_meta = pd.DataFrame([[index, target_color.tolist()]], columns=['index', 'last_color'])
    logger.info(f'New index: {index}, new color: {target_color}')
    if not test:
        write_data(new_color_meta, 'color_meta')
    return target_color

def get_season():
    doy = datetime.datetime.today().timetuple().tm_yday
    spring = range(80, 172)
    summer = range(172, 264)
    fall = range(264, 355)
    if doy in spring:
        season = 'spring'
    elif doy in summer:
        season = 'summer'
    elif doy in fall:
        season = 'autumn'
    else:
        season = 'winter'
    return season


def get_candidates(metadata: pd.DataFrame, uploaded, top_n=2, test=False):
    candidates = metadata[~metadata.shortcode.isin(uploaded.shortcode)]
    candidates = candidates[candidates.accepted_static & candidates.accepted_ml]
    candidates['taken_at_datetime'] = candidates.apply(ts_to_datetime, axis=1)
    candidates = candidates[candidates.taken_at_datetime + datetime.timedelta(days=3) < datetime.datetime.now()]
    last_uploaded = uploaded[uploaded.uploaded_at == uploaded.uploaded_at.max()].iloc[0]
    candidates, _ = get_closest_color(candidates, last_uploaded, top_n=top_n, test=test)
    return candidates


def get_credit(candidate: pd.Series):
    tagged_users = re.findall('(@[^\s\\\n]*)', candidate.caption)
    if not tagged_users:
        return f'@{candidate.username}'
    if len(tagged_users) == 1:
        return tagged_users[0]
    photo_prefixes = ['captured by', 'photo by', '📸', 'shot by', 'image by']
    pattern = f'({"|".join(photo_prefixes)}).{{0,5}}(@[^\s\\\n]*)'
    results = re.findall(pattern, candidate.caption, re.I)
    if len(results) == 1:
        return results[0][1]
    return ''


def ts_to_datetime(row):
    return datetime.datetime.fromtimestamp(row.taken_at_timestamp)


def upload(test=False, robocall=False):
    logger.info(f'{"#"*10} Uploading Image {"#"*10}')
    start_time = datetime.datetime.now()
    logger.info(f'Start time: {start_time}')

    uploaded_org = read_data('uploaded', parse_dates=['uploaded_at', 'taken_at_datetime'])
    uploaded = uploaded_org.copy()
    metadata = read_data('metadata', parse_dates=['scraped_at'])

    captions = open(f'{artefacts_path}/captions.txt', encoding='utf-8').read().splitlines()
    caption_idx = random.randint(0, len(captions) - 1)
    caption = captions[caption_idx]

    all_tags = open(f'{artefacts_path}/tags.txt', encoding='utf-8').read().splitlines()
    tag_idxs = random.sample(range(1, len(all_tags)), 15)
    tags = [all_tags[i].strip() for i in tag_idxs]

    candidates = get_candidates(metadata, uploaded, test=test)
    image_idx = random.randint(0, len(candidates)-1)
    candidate = candidates.iloc[image_idx]
    photo_path = f'ig_images/{candidate.username}/{candidate.shortcode}.jpg'

    credit = get_credit(candidate)

    caption_template = f"""{caption}
.
{f'📸Photo by: {credit}' if credit != '' else '📸Is this your photo? Send me a message!'}
.
.
.
{' '.join(tags)}
"""
    # comment to fix jupyter syntax highlighting """
    logger.info(f'\n{caption_template}')
    caption = caption_template

    s3 = lib.get_s3()
    if not test:
#         with tempfile.TemporaryDirectory() as directory:
        download_path = f'candidate_photo.jpg'
        s3.Bucket('taicapanbot').download_file(photo_path, download_path)
        logger.info('Uploading photo...')
        api = InstagramAPI(ig_username, ig_password)
        api.login()
        api.uploadPhoto(download_path, caption=caption)

        logger.info('Success!')

    logger.info('Updating upload history...')
    with pd.option_context('mode.chained_assignment', None):
        candidate.loc['uploaded_at'] = datetime.datetime.now()
        candidate.loc['uploaded_at'] = pd.to_datetime(candidate['uploaded_at'])
        candidate.loc['posted_tags'] = tags
        candidate.loc['posted_caption'] = caption
        candidate.loc['posted_credit'] = credit
    uploaded = uploaded.append(candidate, ignore_index=True)
    if not test:
        write_data(uploaded, 'uploaded')
    logger.info('Done.')

    end_time = datetime.datetime.now()
    logger.info(f'End time: {end_time}')
    logger.info(f'Duration: {end_time - start_time}')
    if robocall:
        return download_path
    else:
        os.remove(download_path)


if __name__ == "__main__":
    upload()