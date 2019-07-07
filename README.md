# InstaBot
Instabot is a full automated instagram bot with an Telegram interface using the Telegram Bot options. The bot will automatically scrape images, post images, scrape users and follow and unfollow users. Additionally it uses AI to select the images and create a nice instagram timeline.


## Setup
In the /artefacts folder, make sure the following files exist and have some values:
1. captions.txt
2. ig_users.txt
3. tags.txt

where captions.txt has one caption per line, ig_users.txt has one user per line and tags.txt has one tag per line. The hashtags should include the hashtag ('#').

Train both the image model and user model. Image model training is in scrape_image_data.py, and the user model is shortly described in train_user_model.py but requires some work on your end.
