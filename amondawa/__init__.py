from boto import dynamodb2
from os import environ

def connect(region):
  return dynamodb2.connect_to_region(region, aws_access_key_id=environ['AWS_ACCESS_KEY_ID'],
      aws_secret_access_key=environ['AWS_SECRET_KEY'])
