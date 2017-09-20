import urllib
import urlparse
import fileinput
import logging
import boto3
import botocore
import rfc3986
import os

class TableContent(object):
    
    def __init__(self, header = None, body = None):
        self._header = header
        self._body = body

    def set_header(self, header):
        self._header = header + "\n"

    def get_header(self):
        return self._header

    def set_body(self, body):
        self._body = body + "\n"

    def get_body(self):
        return self._body

    def get_content(self):
        return self._header + self._body



def read_file(file_url):
    logging.debug("Reading file from URL: %s", file_url)
    file_uri = get_file_uri(file_url)

    if file_uri.scheme == "s3":
        return read_file_s3(file_uri)
    elif (file_uri.scheme == "http") or (file_uri.scheme == "https"):
        return read_file_http(file_url)
    elif (file_uri.scheme == "file") or (file_uri.scheme is None):
        return read_file_local(file_url)
    else:
        raise ValueError(
            "File location '{0}' not supported".format(file_uri.scheme)
        )


def save_file(body, filepath):
    
    if not body:
        raise IOError("File body cannot be empty")
    if not filepath:
        raise IOError("File path cannot be empty")
        
    
    file_uri = get_file_uri(filepath)

    if file_uri.scheme == "s3":
        return save_file_to_s3(body, file_uri)
    elif (file_uri.scheme == "file") or (file_uri.scheme is None):
        return save_file_local(body, filepath)
    else:
        raise ValueError("File location '{0}' not supported".format(file_uri.scheme))



##### 'Private' methods

## Read

def read_file_s3(s3_uri):
    logging.debug("Reading file from AWS S3...")

    bucket = s3_uri.host
    key = s3_uri.path[1:]  # uri.path includes a leading "/"

    boto3_session = boto3.Session()
    s3_client = boto3_session.client("s3")

    # uri.path includes a leading "/"
    try:
        response = s3_client.get_object(Bucket=bucket, Key=key)
    except botocore.exceptions.ClientError, e:
        if e.response['Error']['Code'] == "404":
            logging.error("Requested file '%s' in bucket '%s' does not exist", key, bucket)
        else:
            logging.error("There was a problem downloading requested file '%s' in bucket '%s'", key, bucket)
        raise

    content = response["Body"].read()
    return content.splitlines()

def read_file_http(url):
    logging.debug("Reading file from http/https...")
    response = urllib.urlopen(url)
    if response.code == 200:
        return response.read()
    elif response.code == 404:
        raise IOError("Requested file '{0}' does not exist".format(url))
    else:
        raise IOError("There was a problem downloading requested file '{0}'".format(url))
    

def read_file_local(url):
    logging.debug("Reading local file...")
    try:
        input_file = fileinput.input(url)
    except IOError, e:
        logging.error("Failed to load file: %s", url)
        raise e
    return input_file


## Write 

def save_file_to_s3(body, s3_uri):
    logging.debug("Saving file to AWS S3...")

    bucket = s3_uri.host
    key = s3_uri.path[1:]  # uri.path includes a leading "/"
    
    boto3_session = boto3.Session()
    s3_client = boto3_session.client("s3")

    try:
        response = s3_client.put_object(Body=body, Bucket=bucket, Key=key)
        logging.info("Done saving to AWS S3. Response:")
        logging.info(response)
    except botocore.exceptions.ClientError, e:
        if e.response['Error']['Code'] == "404":
            logging.error("Requested file '%s' in bucket '%s' does not exist", key, bucket)
        else:
            logging.error("There was a problem downloading requested file '%s' in bucket '%s'", key, bucket)
        raise

def save_file_local(body, filepath):
    logging.debug("Saving file locally...")
    init_local_directory(filepath)
    write_local_file(body, filepath)

def init_local_directory(filepath):
    dirname = os.path.dirname(filepath)
    if not os.path.exists(dirname):
        os.makedirs(dirname)

def write_local_file(body, filepath):
    with open(filepath, "w") as text_file:
        text_file.write(body)


## Misc

def get_file_uri(url):
    return rfc3986.urlparse(url)