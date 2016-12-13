# -*- coding:utf-8 -*-
import base64
import re
import os

from googleapiclient import discovery
from googleapiclient import errors
from oauth2client.client import GoogleCredentials

DISCOVERY_URL = 'https://{api}.googleapis.com/$discovery/rest?version={apiVersion}'

FILE_PATH = '/'.join([os.path.dirname(os.path.abspath(__file__)), 'barcode_images'])


class VisionApi:
    """Construct and use the Google Vision API service."""

    def __init__(self, image_input_directory=FILE_PATH):
        # TODO: Jenkins 잡 만들 때 환경 변수 셋팅 잊지말자.
        # TODO: e.g. export GOOGLE_APPLICATION_CREDENTIALS=/Users/Nate/work/billi/store/barcode-ocr-2f567a109442.json
        self.credentials = GoogleCredentials.get_application_default()
        self.service = discovery.build(
            'vision', 'v1', credentials=self.credentials,
            discoveryServiceUrl=DISCOVERY_URL)
        self.image_input_directory = image_input_directory

    def detect_text(self, input_filenames, num_retries=3, max_results=6):
        """Uses the Vision API to detect text in the given file.
        """
        images = {}
        for filename in input_filenames:
            with open(filename, 'rb') as image_file:
                images[filename] = image_file.read()

        batch_request = []
        for filename in images:
            batch_request.append({
                'image': {
                    'content': base64.b64encode(
                            images[filename]).decode('UTF-8')
                },
                'features': [{
                    'type': 'TEXT_DETECTION',
                    'maxResults': max_results,
                }]
            })
        request = self.service.images().annotate(
            body={'requests': batch_request})

        try:
            responses = request.execute(num_retries=num_retries)
            if 'responses' not in responses:
                return {}
            text_response = {}
            for filename, response in zip(images, responses['responses']):
                if 'error' in response:
                    print("API Error for %s: %s" % (
                            filename,
                            response['error']['message']
                            if 'message' in response['error']
                            else ''))
                    continue
                if 'textAnnotations' in response:
                    text_response[filename] = response['textAnnotations']
                else:
                    text_response[filename] = []
            return text_response
        except errors.HttpError as e:
            print("Http Error")
            print(e)
            print("If admission error occurred, please reduce image counts")
            # print("Http Error for %s: %s" % (filename, e))
        except KeyError as e2:
            print("Key error: %s" % e2)

    def detect_text_from_directory(self, num_retries=3, max_results=6):
        input_filenames = self.load_image_names_from_directory()
        return self.detect_text(input_filenames, num_retries, max_results)

    def load_image_names_from_directory(self):
        filenames = ['/'.join([FILE_PATH, filename]) for filename in os.listdir(self.image_input_directory) if filename.endswith('jpg') or
                     filename.endswith('png')]

        return filenames


class VisionAPIHelper:

    PIN_TYPE_TO_REGEX = {
        'numeric': '[0-9]',
        'alphanumeric': '[0-9a-ZA-Z]'
    }

    PIN_NOT_FOUND = 'ERROR_PIN_NOT_FOUND'
    PRETTY_PRINT_FAILED = 'PRETTY_PRINT_FAILED'

    def __init__(self, pin_length=10, pin_type='numeric'):
        self.pin_length = pin_length
        self.pin_type = self.PIN_TYPE_TO_REGEX[pin_type]

    def pretty_print(self, bounding_poly):
        # Prints the entire blob of text found within the photo
        if len(bounding_poly.keys()) != 1:
            return self.PRETTY_PRINT_FAILED
        key = bounding_poly.keys()[0]
        return bounding_poly[key][0]['description']

    def find_pin_number(self, detect_res):
        pin_re_pattern = ''.join(['^', self.pin_type, '{', str(self.pin_length), '}', '$'])
        for bounding_poly in detect_res:
            # Iterate over the entire set of bounding polygons
            # Do just basic regex pattern matching.
            # TODO: handle edge cases and improve accuracy. for example, OCR recognizes the barcode pin number over
            # TODO: two separate lines.
            description_cleaned = bounding_poly['description'].replace('.', '').replace(' ', '')

            if re.match(pin_re_pattern, description_cleaned):
                return description_cleaned

        # look for a pattern that instead "contains" it.
        pin_looser_re_pattern = ''.join(['.*[^0-9]', self.pin_type, '{', str(self.pin_length), '}', '[^0-9].*'])
        for bounding_poly in detect_res:
            description_cleaned = bounding_poly['description'].replace('.', '').replace(' ', '')

            if re.match(pin_looser_re_pattern, description_cleaned):

                substring = re.search(pin_re_pattern[1:-1], description_cleaned)
                if substring:
                    return substring.group(0)

        return self.PIN_NOT_FOUND
