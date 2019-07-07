## Disclaimer: This is a public version of my own private repository. I've chosen not to release that version because it includes a lot of instagram data and files of my own production environment like scraping timestamps. If you have any questions, feel free to contact me. 

# InstaBot
Instabot is a full automated instagram bot with an Telegram interface using the Telegram Bot options. The bot will automatically scrape images, post images, scrape users and follow and unfollow users. Additionally it uses machine learning  and some smart techniques to select the images and create a nice instagram timeline.

The idea of this bot came from the following blogpost: https://medium.com/@chrisbuetti/how-i-eat-for-free-in-nyc-using-python-automation-artificial-intelligence-and-instagram-a5ed8a1e2a10



## Setup
In the /artefacts folder, make sure the following files exist and have some values:
1. captions.txt
2. ig_users.txt
3. tags.txt

where captions.txt has one caption per line, ig_users.txt has one user per line and tags.txt has one tag per line. The hashtags should include the hashtag ('#').

Train both the image model and user model. Image model training is in scrape_image_data.py, and the user model is shortly described in train_user_model.py but requires some work on your end.
