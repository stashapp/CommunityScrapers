import os
import sys
import unittest

# add scraper directory to loadable module path
sys.path.insert(0, os.path.join(os.path.dirname(__file__),'..','..','scrapers', 'GalleryDLInfo'))  #
import gallerydl_info


class GalleryDLInfoTestCase(unittest.TestCase):
    def test_gallery_a_directory(self):
        result = gallerydl_info.process_gallery_path(os.path.join(os.path.dirname(__file__), 'test-data', 'a'))

        self.assertSetEqual({'Code', 'Date', 'Performers', 'Photographer', 'Studio', 'Title', 'Tags'}, set(result.keys()),
                            'present fields should match expected')
        self.assertEqual('title (en)', result['Title'], 'title should match expected')
        self.assertEqual('12345', result['Code'], 'code should match expected')
        self.assertEqual('2016-01-23', result['Date'], 'date should match expected')
        self.assertEqual('group 1', result['Photographer'], 'photographer should match expected')
        self.assertEqual({'Name': 'artist 1'}, result['Studio'], 'studio should match expected')
        self.assertListEqual([{'Name': 'character 1'}, {'Name': 'character 2'}], result['Performers'],
                             'performers should match expected')
        self.assertListEqual(
        [
                {'Name': 'language:english'}, {'Name': 'language:translated'}, {'Name': 'parody 1'}, {'Name': 'parody 2'},
                {'Name': 'tag 1'}, {'Name': 'tag 2'}, {'Name': 'tag 3'}, {'Name': 'male:tag 4'}, {'Name': 'tag 5'},
                {'Name': 'multi-work series'}
            ],
            result['Tags'],
            'tags should match expected')

    def test_gallery_a_zip(self):
        result = gallerydl_info.process_gallery_path(os.path.join(os.path.dirname(__file__), 'test-data', 'a.zip'))

        self.assertSetEqual({'Code', 'Date', 'Performers', 'Photographer', 'Studio', 'Title', 'Tags'}, set(result.keys()),
                            'present fields should match expected')
        self.assertEqual('title (en)', result['Title'], 'title should match expected')
        self.assertEqual('12345', result['Code'], 'code should match expected')
        self.assertEqual('2016-01-23', result['Date'], 'date should match expected')
        self.assertEqual('group 1', result['Photographer'], 'photographer should match expected')
        self.assertEqual({'Name': 'artist 1'}, result['Studio'], 'studio should match expected')
        self.assertListEqual([{'Name': 'character 1'}, {'Name': 'character 2'}], result['Performers'],
                             'performers should match expected')
        self.assertListEqual(
            [
                {'Name': 'language:english'}, {'Name': 'language:translated'}, {'Name': 'parody 1'},
                {'Name': 'parody 2'},
                {'Name': 'tag 1'}, {'Name': 'tag 2'}, {'Name': 'tag 3'}, {'Name': 'male:tag 4'}, {'Name': 'tag 5'},
                {'Name': 'multi-work series'}
            ],
            result['Tags'],
            'tags should match expected')

    def test_image_a_directory_exact_match(self):
        result = gallerydl_info.process_image_path(os.path.join(os.path.dirname(__file__), 'test-data', 'a', 'gallery', '12345_0003_987654321_02.webp'))

        self.assertSetEqual({'Date', 'Performers', 'Photographer', 'Studio', 'Title', 'Tags'}, set(result.keys()),
                            'present fields should match expected')
        self.assertEqual('title (en)', result['Title'], 'title should match expected')
        self.assertEqual('2016-01-23', result['Date'], 'date should match expected')
        self.assertEqual('group 1', result['Photographer'], 'photographer should match expected')
        self.assertEqual({'Name': 'artist 1'}, result['Studio'], 'studio should match expected')
        self.assertListEqual([{'Name': 'character 1'}, {'Name': 'character 2'}], result['Performers'],
                             'performers should match expected')
        self.assertListEqual(
            [
                {'Name': 'language:english'}, {'Name': 'language:translated'}, {'Name': 'parody 1'},
                {'Name': 'parody 2'},
                {'Name': 'tag 1'}, {'Name': 'tag 2'}, {'Name': 'tag 3'}, {'Name': 'male:tag 4'}, {'Name': 'tag 5'},
                {'Name': 'multi-work series'}
            ],
            result['Tags'],
            'tags should match expected')

    def test_image_a_directory_different_extension(self):
        result = gallerydl_info.process_image_path(
            os.path.join(os.path.dirname(__file__), 'test-data', 'a', 'gallery', '12345_0003_987654321_02.jpg'))

        self.assertSetEqual({'Date',  'Performers', 'Photographer', 'Studio', 'Title', 'Tags'}, set(result.keys()),
                            'present fields should match expected')
        self.assertEqual('title (en)', result['Title'], 'title should match expected')
        self.assertEqual('2016-01-23', result['Date'], 'date should match expected')
        self.assertEqual('group 1', result['Photographer'], 'photographer should match expected')
        self.assertEqual({'Name': 'artist 1'}, result['Studio'], 'studio should match expected')
        self.assertListEqual([{'Name': 'character 1'}, {'Name': 'character 2'}], result['Performers'],
                             'performers should match expected')
        self.assertListEqual(
            [
                {'Name': 'language:english'}, {'Name': 'language:translated'}, {'Name': 'parody 1'},
                {'Name': 'parody 2'},
                {'Name': 'tag 1'}, {'Name': 'tag 2'}, {'Name': 'tag 3'}, {'Name': 'male:tag 4'}, {'Name': 'tag 5'},
                {'Name': 'multi-work series'}
            ],
            result['Tags'],
            'tags should match expected')

    def test_image_a_zip_exact_match(self):
        result = gallerydl_info.process_image_path(os.path.join(os.path.dirname(__file__), 'test-data', 'a.zip', 'a', 'gallery', '12345_0003_987654321_02.webp'))

        self.assertSetEqual({'Date', 'Performers', 'Photographer', 'Studio', 'Title', 'Tags'}, set(result.keys()),
                            'present fields should match expected')
        self.assertEqual('title (en)', result['Title'], 'title should match expected')
        self.assertEqual('2016-01-23', result['Date'], 'date should match expected')
        self.assertEqual('group 1', result['Photographer'], 'photographer should match expected')
        self.assertEqual({'Name': 'artist 1'}, result['Studio'], 'studio should match expected')
        self.assertListEqual([{'Name': 'character 1'}, {'Name': 'character 2'}], result['Performers'],
                             'performers should match expected')
        self.assertListEqual(
            [
                {'Name': 'language:english'}, {'Name': 'language:translated'}, {'Name': 'parody 1'},
                {'Name': 'parody 2'},
                {'Name': 'tag 1'}, {'Name': 'tag 2'}, {'Name': 'tag 3'}, {'Name': 'male:tag 4'}, {'Name': 'tag 5'},
                {'Name': 'multi-work series'}
            ],
            result['Tags'],
            'tags should match expected')

    def test_image_a_zip_different_extension(self):
        result = gallerydl_info.process_image_path(
            os.path.join(os.path.dirname(__file__), 'test-data', 'a.zip', 'a', 'gallery', '12345_0003_987654321_02.jpg'))

        self.assertSetEqual({'Date', 'Performers', 'Photographer', 'Studio', 'Title', 'Tags'}, set(result.keys()),
                            'present fields should match expected')
        self.assertEqual('title (en)', result['Title'], 'title should match expected')
        self.assertEqual('2016-01-23', result['Date'], 'date should match expected')
        self.assertEqual('group 1', result['Photographer'], 'photographer should match expected')
        self.assertEqual({'Name': 'artist 1'}, result['Studio'], 'studio should match expected')
        self.assertListEqual([{'Name': 'character 1'}, {'Name': 'character 2'}], result['Performers'],
                             'performers should match expected')
        self.assertListEqual(
            [
                {'Name': 'language:english'}, {'Name': 'language:translated'}, {'Name': 'parody 1'},
                {'Name': 'parody 2'},
                {'Name': 'tag 1'}, {'Name': 'tag 2'}, {'Name': 'tag 3'}, {'Name': 'male:tag 4'}, {'Name': 'tag 5'},
                {'Name': 'multi-work series'}
            ],
            result['Tags'],
            'tags should match expected')

    def test_gallery_b_directory(self):
        result = gallerydl_info.process_gallery_path(os.path.join(os.path.dirname(__file__), 'test-data', 'b'))

        self.assertSetEqual(
            {'Code', 'Date', 'Performers', 'Photographer', 'Studio', 'Title', 'Tags'}, set(result.keys()),
            'present fields should match expected')
        self.assertEqual('title', result['Title'], 'title should match expected')
        self.assertEqual('12345', result['Code'], 'code should match expected')
        self.assertEqual('2021-02-03', result['Date'], 'date should match expected')
        self.assertEqual('group 1', result['Photographer'], 'photographer should match expected')
        self.assertEqual({'Name': 'artist 1'}, result['Studio'], 'studio should match expected')
        self.assertListEqual([{'Name': 'character 1'}, {'Name': 'character 2'}], result['Performers'],
                             'performers should match expected')
        self.assertListEqual(
            [{'Name': 'parody 1'}, {'Name': 'parody 2'}, {'Name': 'tag 1'}, {'Name': 'tag 2'}, {'Name': 'tag 3'}],
            result['Tags'],
            'tags should match expected')

    def test_image_c_exact_match(self):
        result = gallerydl_info.process_image_path(os.path.join(os.path.dirname(__file__), 'test-data', 'c', 'c_12345678_abcdefghijklmno.jpg'))

        self.assertSetEqual({'Date', 'Tags'}, set(result.keys()), 'present fields should match expected')
        self.assertEqual('2012-09-12', result['Date'], 'date should match expected')
        self.assertListEqual(
            [{'Name': 'artist 1'}, {'Name': 'artist 2'}, {'Name': 'parody 1'}, {'Name': 'parody 2'},
             {'Name': 'character 1'}, {'Name': 'character 2'},
             {'Name': 'tag 1'}, {'Name': 'tag 2'}, {'Name': 'tag 3'}],
            result['Tags'],
            'tags should match expected')

    def test_image_c_different_extension(self):
        result = gallerydl_info.process_image_path(os.path.join(os.path.dirname(__file__), 'test-data', 'c', 'c_12345678_abcdefghijklmno.png'))

        self.assertSetEqual({'Date', 'Tags'}, set(result.keys()), 'present fields should match expected')
        self.assertEqual('2012-09-12', result['Date'], 'date should match expected')
        self.assertListEqual(
            [{'Name': 'artist 1'}, {'Name': 'artist 2'}, {'Name': 'parody 1'}, {'Name': 'parody 2'},
             {'Name': 'character 1'}, {'Name': 'character 2'},
             {'Name': 'tag 1'}, {'Name': 'tag 2'}, {'Name': 'tag 3'}],
            result['Tags'],
            'tags should match expected')

if __name__ == '__main__':
    unittest.main()
