
#################################################
### THIS FILE WAS AUTOGENERATED! DO NOT EDIT! ###
#################################################
# file to edit: notebooks/5_move_to_s3.ipynb

import os
import logging
import sys
sys.path.append('src')
import lib


logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s %(name)-s %(levelname)-s : %(message)s')
fh = logging.FileHandler('logs/move_img_to_s3.log', encoding='utf-8')
fh.setLevel(logging.INFO)
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)
logger.addHandler(fh)


def sync_to_s3(local_directory, aws_region='eu-west-1', bucket_name='taicapanbot', create_bucket=False, delete_after=False):
    if not os.path.isdir(local_directory):
        raise ValueError('target_dir %r not found.' % local_directory)
    s3 = lib.get_s3()
    for root, dirs, files in os.walk(local_directory):
        for filename in files:
            local_path = f'{root}/{filename}'.replace('\\', '/')
            s3_path = f'{local_path}'.replace('\\', '/')

            logger.debug('Searching "%s" in "%s"' % (s3_path, bucket_name))
            try:
                s3.Object(bucket_name, s3_path).load()
                logger.deubg("Path found on S3! Skipping %s..." % s3_path)
            except:
                logger.debug("Uploading %s..." % s3_path)
                root = root.replace('\\', '/')
                s3.Object(bucket_name, s3_path).put(Body=open(f'{local_path}', 'rb'))

            if delete_after:
                os.remove(local_path)


def sync_ig_images_to_s3():
    sync_to_s3('ig_images', aws_region='eu-west-1', bucket_name='taicapanbot', delete_after=True)
