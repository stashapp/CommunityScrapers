import os
import sys
import unittest

import embedded_metadata

import test_config


class TestEmbeddedMetadataExiftool(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        test_config.FORCE_METHOD = "exiftool"

    def test_EXIF_IPTC_XMP_keywords_title(self):
        data = embedded_metadata.process_image(os.path.join(os.path.dirname(__file__), 'test-data/EXIF_IPTC_XMP_keywords_title.jpg'))

        self.assertSetEqual({'Title', 'Date', 'Tags', 'Details'}, set(data.keys()))
        self.assertEqual("Blue Square Test File - .jpg", data['Title'])
        self.assertEqual("2005-09-07", data['Date'])
        self.assertListEqual(
           [{"Name": "XMP"}, {"Name": "Blue Square"}, {"Name": "test file"}, {"Name": "Photoshop"}, {"Name": ".jpg"}],
            data['Tags']
        )
        self.assertEqual(('XMPFiles BlueSquare test file, created in Photoshop CS2, saved as .psd, '
 '.jpg, and .tif.\n'
 'XMPFiles BlueSquare test file, created in Photoshop CS2, saved as .psd, '
 '.jpg, and .tif.\n'
 '\n'), data['Details'])

    def test_EXIF_camera(self):
        data = embedded_metadata.process_image(os.path.join(os.path.dirname(__file__), 'test-data/EXIF_camera.jpg'))

        self.assertSetEqual(set(data.keys()), {'Date'})
        self.assertEqual("2008-11-01", data['Date']) # not the same as pyexiv2, exiftool does not return exif.DateTime


class TestEmbeddedMetadataPyexiv2tool(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        test_config.FORCE_METHOD = "pyexiv2"

    def test_EXIF_IPTC_XMP_keywords_title(self):
        data = embedded_metadata.process_image(os.path.join(os.path.dirname(__file__), 'test-data/EXIF_IPTC_XMP_keywords_title.jpg'))

        self.assertSetEqual({'Title', 'Date', 'Tags', 'Details'}, set(data.keys()))
        self.assertEqual("Blue Square Test File - .jpg", data['Title'])
        self.assertEqual("2005-09-07", data['Date'])
        self.assertListEqual(
            [{"Name": "XMP"}, {"Name": "Blue Square"}, {"Name": "test file"}, {"Name": "Photoshop"}, {"Name": ".jpg"}],
            data['Tags']
        )
        self.assertEqual(('XMPFiles BlueSquare test file, created in Photoshop CS2, saved as .psd, '
 '.jpg, and .tif.\n'
 'XMPFiles BlueSquare test file, created in Photoshop CS2, saved as .psd, '
 '.jpg, and .tif.\n'
 'XMPFiles BlueSquare test file, created in Photoshop CS2, saved as .psd, '
 '.jpg, and .tif.\n'
 '\n'), data['Details'])

    def test_EXIF_camera(self):
        data = embedded_metadata.process_image(os.path.join(os.path.dirname(__file__), 'test-data/EXIF_camera.jpg'))

        self.assertSetEqual(set(data.keys()), {'Date'})
        self.assertEqual("2008-10-22", data['Date'])
