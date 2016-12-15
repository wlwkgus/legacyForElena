from lib import VisionApi, VisionAPIHelper


if __name__ == '__main__':
    api_client = VisionApi()
    barcode_finder = VisionAPIHelper()
    print('input image files are: ')
    print(api_client.load_image_names_from_directory())
    api_response = api_client.detect_text_from_directory()
    f = open('result.csv', 'w')
    # print api_response
    for filename, blob in api_response.iteritems():
        barcode = barcode_finder.find_pin_number(blob)
        if barcode != 'ERROR_PIN_NOT_FOUND':
            print("{0} : {1}".format(filename, barcode))
            f.write('{0}\n'.format(barcode))
        else:
            print("error")
    f.close()
    # TODO : https://developers.google.com/identity/protocols/application-default-credentials
    # TODO : Check URL above, and export env var.
    # TODO : export GOOGLE_APPLICATION_CREDENTIALS= ~/elenakey.json
