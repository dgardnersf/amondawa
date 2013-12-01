from boto import dynamodb2

def connect(region):
  return dynamodb2.connect_to_region(region)

