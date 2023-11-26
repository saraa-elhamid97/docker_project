import requests
import telebot
from loguru import logger
import os
import time
from telebot.types import InputFile
import boto3

class Bot:

    def __init__(self, token, telegram_chat_url):
        # create a new instance of the TeleBot class.
        # all communication with Telegram servers are done using self.telegram_bot_client
        self.telegram_bot_client = telebot.TeleBot(token)

        # remove any existing webhooks configured in Telegram servers
        self.telegram_bot_client.remove_webhook()
        time.sleep(0.5)

        # set the webhook URL
        self.telegram_bot_client.set_webhook(url=f'{telegram_chat_url}/{token}/', timeout=60)
        logger.info(f'Telegram Bot information\n\n{self.telegram_bot_client.get_me()}')

    def send_text(self, chat_id, text):
        self.telegram_bot_client.send_message(chat_id, text)

    def send_text_with_quote(self, chat_id, text, quoted_msg_id):
        self.telegram_bot_client.send_message(chat_id, text, reply_to_message_id=quoted_msg_id)

    def is_current_msg_photo(self, msg):
        return 'photo' in msg

    def download_user_photo(self, msg):
        """
        Downloads the photos that sent to the Bot to `photos` directory (should be existed)
        :return:
        """
        if not self.is_current_msg_photo(msg):
            raise RuntimeError(f'Message content of type \'photo\' expected')

        file_info = self.telegram_bot_client.get_file(msg['photo'][-1]['file_id'])
        data = self.telegram_bot_client.download_file(file_info.file_path)
        folder_name = file_info.file_path.split('/')[0]

        if not os.path.exists(folder_name):
            os.makedirs(folder_name)

        with open(file_info.file_path, 'wb') as photo:
            photo.write(data)

        return file_info.file_path

    def send_photo(self, chat_id, img_path):
        if not os.path.exists(img_path):
            raise RuntimeError("Image path doesn't exist")

        self.telegram_bot_client.send_photo(
            chat_id,
            InputFile(img_path)
        )

    def handle_message(self, msg):
        """Bot Main message handler"""
        logger.info(f'Incoming message: {msg}')
        self.send_text(msg['chat']['id'], f'Your original message: {msg["text"]}')


class QuoteBot(Bot):
    def handle_message(self, msg):
        logger.info(f'Incoming message: {msg}')

        if msg["text"] != 'Please don\'t quote me':
            self.send_text_with_quote(msg['chat']['id'], msg["text"], quoted_msg_id=msg["message_id"])


class ObjectDetectionBot(Bot):
    def handle_message(self, msg):
        logger.info(f'Incoming message: {msg}')
        images_bucket = os.environ['BUCKET_NAME']
        try:
            if self.is_current_msg_photo(msg):
                photo_path = self.download_user_photo(msg)
                photo_name = photo_path.split('/')[1]
                # Upload the file to S3
                s3 = boto3.client('s3')
                s3.upload_file(photo_path, images_bucket, photo_name)
                # Make a request to the object detection service
                response = requests.post(f"http://yolo5:8081/predict?imgName={photo_name}")
                predictions = response.json()['labels']
                detected_objects = {}
                for predict in predictions:
                    object_name = predict['class']
                    if object_name in detected_objects:
                        detected_objects[object_name] += 1
                    else:
                        detected_objects[object_name] = 1
                text = 'Detected objects:\n' + '\n'.join(f'{key}: {value}' for key, value in detected_objects.items())
                self.send_text(msg['chat']['id'], {text})
            elif msg["text"] == '/start':
                welcome_msg = ('Welcome to the "Image Prediction World". \nIn order to start the prediction please '
                               'send me a photo.')
                self.send_text(msg['chat']['id'], welcome_msg)
            else:
                msg_to_use = ("Sorry, I can only predict objects in photos.\nSend me a photo and I will show you the "
                              "real magic.")
                self.send_text_with_quote(msg['chat']['id'], msg_to_use, quoted_msg_id=msg["message_id"])
        except Exception as e:
            logger.error(f'Error processing message: {e}')
            error_message = "An error occurred while processing your request. Please try again later."
            self.send_text(msg['chat']['id'], error_message)