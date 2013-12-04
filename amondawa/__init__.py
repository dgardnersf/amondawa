from boto import dynamodb2
from os import environ

def connect(region):
  return dynamodb2.connect_to_region(region)
