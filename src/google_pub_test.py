import os
from google.cloud import pubsub_v1

credentials_path = './regala_private_key_new.json'
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path

publisher = pubsub_v1.PublisherClient()
topic_path = 'projects/lateral-medium-329915/topics/regala'

data = 'Test Message'
data = data.encode('utf-8')
attributes = {
    'user_id' : '777',
    'user_name' : 'Taemin',
    'time' : '30'
}

future = publisher.publish(topic_path, data, **attributes)
print('published message id {}'.format(future.result()))