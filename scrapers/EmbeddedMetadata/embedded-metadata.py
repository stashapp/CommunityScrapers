from datetime import datetime
import hashlib
import json
import os
import sys

from py_common import graphql, log
from py_common.deps import ensure_requirements
from py_common.util import dig, scraper_args

# try importing config
try:
    import config
except:
    config = object()

skip_ensure_requirements = config.skip_ensure_requirements if hasattr(config, 'skip_ensure_requirements') else False

if not skip_ensure_requirements:
	ensure_requirements("pyexiv2", "pyexiftool")

try:
    import pyexiv2
# might fail due to old GLIBC, fall back to exiftool
except:
	try:
		import exiftool
	except:
		log.error("You need to install the pyexiv2 or exiftool module.")
		log.error("If you have pip (normally installed with python), run this command in a terminal (cmd): pip install pyexiv2 exiftool")
		sys.exit()

details_date_fields = config.details_date_fields if hasattr(config, 'details_date_fields') else False
details_title_fields = config.details_title_fields if hasattr(config, 'details_title_fields') else False
details_author_fields = config.details_author_fields if hasattr(config, 'details_author_fields') else False
details_camera_infos = config.details_camera_infos if hasattr(config, 'details_camera_infos') else False

details_upprocessed_fields = config.details_upprocessed_fields if hasattr(config, 'details_upprocessed_fields') else False
details_upprocessed_fields_ignored = config.details_upprocessed_fields_ignored if hasattr(config, 'details_upprocessed_fields_ignored') else []
details_upprocessed_fields_unignored = config.details_upprocessed_fields_unignored if hasattr(config, 'details_upprocessed_fields_unignored') else []

details_ignored_labels = {
	'ExifTag', 'Orientation', 'PhotometricInterpretation', 'ResolutionUnit', 'Contrast', 'CustomRendered', 'DigitalZoomRatio', 'ExposureBiasValue', 'ExposureMode', 'ExposureProgram', 'ExposureTime', 'ExposureCompensation', 
	'ColorSpace', 'ComponentsConfiguration', 'CompressedBitsPerPixel', 'ExifVersion', 'FlashpixVersion', 'YCbCrPositioning', 'JPEGInterchangeFormat', 'JPEGInterchangeFormatLength', 'BaselineExposureOffset',
	'FNumber', 'FileSource', 'Flash', 'FocalLength', 'FocalLengthIn35mmFilm', 'GainControl', 'ISOSpeedRatings', 'LightSource', 'MaxApertureValue', 'MeteringMode', 'Saturation', 'SceneCaptureType', 'SensingMethod', 'BaselineExposure',
	'Sharpness', 'WhiteBalance', 'ShutterSpeedValue', 'ApertureValue', 'FocalLength', 'FocalLengthIn35mmFilm', 'FocalLengthIn35mmFormat', 'ExposureTime', 'ExposureProgram', 'ExposureBiasValue', 'MaxApertureValue', 'ShutterSpeedValue', 
	'ExposureIndex', 'FocalPlaneResolutionUnit', 'FocalPlaneXResolution', 'FocalPlaneYResolution',
	'PixelXDimension', 'PixelYDimension', 'XResolution', 'YResolution', 'ExifImageWidth', 'ExifImageHeight', 'ImageHeight', 'ImageWidth', 'RelatedImageHeight', 'RelatedImageWidth',
	'RecordVersion', 'CharacterSet', 'SceneType', 'BrightnessValue', 'ISO', 'Compression', 'ModifyDate'
	'FlashCompensation', 'LensID', 'InteropIndex', 'InteropVersion', 'ThumbnailImage', 'ThumbnailLength', 'ThumbnailOffset', 'OffsetSchema', 'Padding', 'OtherImageLength', 'OtherImageStart',
	'GPSVersionID', 'XMPToolkit'
}
details_ignored_labels.update(details_upprocessed_fields_ignored)
details_ignored_labels.difference_update(details_upprocessed_fields_unignored)


def process_image(image_path: str):
	data: dict[str, str] = {}
	
	try:
		with pyexiv2.Image(image_path) as img:
			data.update(img.read_exif())
			data.update(img.read_iptc())
			data.update(img.read_xmp())
	except:
		with exiftool.ExifToolHelper() as et:
			metadata = et.get_metadata(image_path)
			log.debug(f"exiftool metadata {metadata}")
			data.update(metadata[0])

	ret = {}

	details = ''

	log.debug(f"image {image_path} data: {data}")

	fields_processed = set()

	#
	# description, comment to details
	#
	for field in ['Exif.Image.ImageDescription', 'EXIF:ImageDescription', 'Exif.Image.XPComment', 'EXIF:XPComment', 'Exif.Photo.UserComment', 'EXIF:UserComment', 'Iptc.Application2.Caption', 'Xmp.dc.description', 'XMP:Description']:
		if field not in data:
			continue
		value = data[field]
		if not value:
			continue

		fields_processed.add(field)

		if value:
			if isinstance(value, list):
				for list_value in value:
					details += str(list_value) + "\n"
			elif isinstance(value, dict):
				for list_value in value.values():
					details += str(list_value) + "\n"
			else:
				details += str(value) + "\n"
	if len(details) > 0:
		details += '\n'

	#
	# date fields
	#
	date_details = ''
	for field in ['EXIF:CreateDate', 'Iptc.Application2.DateCreated', 'IPTC:DateCreated', 'Exif.Image.DateTime', 'Exif.Photo.DateTime',  'EXIF:DateTime', 
			'Iptc.Application2.DigitizationDate', 'IPTC:DigitizationDate', 'Exif.Photo.DateTimeDigitized', 'EXIF:DateTimeDigitized', 
			'Exif.Image.DateTimeOriginal', 'Exif.Photo.DateTimeOriginal', 'EXIF:DateTimeOriginal']:
		if field not in data:
			continue
		value = data[field]
		if not value:
			continue
		
		date_value = None
		try:
			if field.startswith('Exif.') or field.startswith('EXIF:'):
				date_value = datetime.strptime(value, '%Y:%m:%d %H:%M:%S')
			elif field.startswith('Iptc.'):
				date_value = datetime.strptime(value, '%Y-%m-%d')
			elif field.startswith('IPTC:'):
				date_value = datetime.strptime(value, '%Y:%m:%d')
		except:
			continue
		
		fields_processed.add(field)
		label = _field_name_to_details_label(field)
		date_details += label + ': ' + date_value.isoformat() + "\n"
		
		if date_value.day == 1 and date_value.month == 1 and date_value.year == 2000:
			continue

		ret['Date'] = date_value.date().isoformat()
	if details_date_fields and len(date_details) > 0:
		details += 'Dates:\n' + date_details + '\n'

	#
	# title
	#
	title_details = ''
	for field in ['Exif.Image.DocumentName', 'EXIF:DocumentName', 'Exif.Image.XPTitle', 'EXIF:XPTitle', 'Exif.Photo.ImageTitle', 'EXIF:ImageTitle', 'Iptc.Application2.Headline', 'IPTC:Headline','Xmp.dc.title', 'XMP:Title', 'Xmp.dc.headline', 'XMP:Headline']:
		if field not in data:
			continue
		value = data[field]
		if not value:
			continue

		fields_processed.add(field)
		label = _field_name_to_details_label(field)
		title_details += label + ': ' + str(value) + "\n"

		if value:
			ret['Title'] = value
	if details_title_fields and len(title_details) > 0:
		details += 'Titles:\n' + title_details + '\n'
	
	#
	# studio / photographer
	#
	author_details = ''
	for field in ['Exif.Image.XPAuthor', 'EXIF:XPAuthor', 'Exif.Photo.Photographer', 'EXIF:Photographer', 'Iptc.Application2.Byline', 'IPTC:By-line','Xmp.dc.creator', 'XMP:Creator', 'Exif.Image.Artist', 'EXIF:Artist']:
		if field not in data:
			continue
		value = data[field]
		if not value:
			continue

		fields_processed.add(field)
		label = _field_name_to_details_label(field)

		if value:
			if isinstance(value, list):
				for list_value in value:
					ret['Studio'] = {'Name': list_value}
					ret['Photographer'] = list_value
					author_details += label + ': ' + str(list_value) + "\n"
			else:
				ret['Studio'] = {'Name': value}
				ret['Photographer'] = value
				author_details += label + ': ' + str(value) + "\n"
	if details_author_fields and len(author_details) > 0:
		details += 'Authors:\n' + author_details + '\n'
	
	#
	# tags
	#
	for field in ['Exif.Image.XPKeywords', 'EXIF:XPKeywords', 'Iptc.Application2.Keywords', 'IPTC:Keywords']:
		if field not in data:
			continue
		value = data[field]
		if not value:
			continue

		fields_processed.add(field)
		
		if 'Tags' not in ret:
			ret['Tags'] = []
		for value_part in value.split(','):
			if not value_part:
				continue
			ret['Tags'].append({
				'Name': value_part.strip()
			})
	
	#
	# camera details
	#

	make = None
	for field in ['Exif.Image.Make', 'EXIF:Make']:
		if field not in data:
			continue
		value = data[field]
		if not value:
			continue

		fields_processed.add(field)
	
		make = str(value)
	
	model = None
	for field in ['Exif.Image.Model', 'EXIF:Model']:
		if field not in data:
			continue
		value = data[field]
		if not value:
			continue

		fields_processed.add(field)
	
		model = str(value)
	
	lens_make = None
	for field in ['Exif.Photo.LensMake', 'EXIF:LensMake']:
		if field not in data:
			continue
		value = data[field]
		if not value:
			continue

		fields_processed.add(field)
	
		lens_make = str(value)
	
	lens_model = None
	for field in ['Exif.Image.LensInfo', 'EXIF:LensInfo','Exif.Photo.LensModel', 'EXIF:LensModel', 'Xmp.aux.Lens', 'XMP:Lens']:
		if field not in data:
			continue
		value = data[field]
		if not value:
			continue

		fields_processed.add(field)
	
		lens_model = str(value)

	if details_camera_infos and make and model:
		details += make + ' ' + model
		if lens_make:
			details += ' ' + lens_make
		if lens_model:
			details += ' ' + lens_model
		details += "\n"
	
	#if 'Details' not in ret:
	#		ret['Details'] = ''
	#ret['Details'] += str(data) + "\n"

	#
	# fill details with unprocessed fields except ignored
	#
	if details_upprocessed_fields:
		details_headlines_added = {}
		for field in sorted(list(data.keys())):
			# skip unkown fields
			if field.startswith('Exif.Image.0x'):
				continue
			# already handled elsewhere
			elif field in fields_processed:
				continue
			label = _field_name_to_details_label(field)
			if label is None:
				continue
			
			for section_headline in ["EXIF", "IPTC", 'XMP']:
				if field.upper().startswith(section_headline) and section_headline not in details_headlines_added:
					details+= "\n" + section_headline + ' metadata:' + "\n"
					details_headlines_added[section_headline] = True
			
			details += label + ':'
			
			value = data[field]
			if isinstance(value, list):
				for list_value in value:
					details += ' ' + str(list_value)
			elif isinstance(value, dict):
				for list_value in value.values():
					details += ' ' + str(list_value)
			else:
				details += ' ' + str(value)
			details += "\n"

	if len(details) > 0:
		ret['Details'] = details

	return ret

def _field_name_to_details_label(field: str) -> str:
	if '.' in field and (field.startswith("Exif.") or field.startswith("Iptc") or field.startswith("Xmp")):
		label = field[field.rindex('.')+1:]
	elif ':' in field and (field.startswith("EXIF") or field.startswith("IPTC") or field.startswith("XMP")):
		label = field[field.rindex(':')+1:]
	else:
		return None
	
	if label in details_ignored_labels:
		return None
	
	return label

def get_imape_paths(image_id):
	query = """
	query FindImage($id: ID!) {
	  findImage(id: $id) {
	    id
	    visual_files {
	    	__typename
	    	... on BaseFile {
	      	path
	    	}
	  	}
	  }
	}
	"""
	result = graphql.callGraphQL(query, {"id": image_id})
	data = dig(result, "findImage")
	
	log.trace(f"image paths data: {data}")
	
	return [f["path"] for f in data['visual_files']]

#
# Start processing
#

if __name__ == "__main__":
	op, args = scraper_args()
	result = None
	match op, args:
		case "image-by-fragment", {"id": image_id} if image_id:
			files = get_imape_paths(image_id)
			ret = {}
	
			for file in files:
				data = process_image(file)
				ret.update(data)
			
			print(json.dumps(ret))
			sys.exit(0)
		case _:
			log.error(f"Not Implemented: Operation: {op}, arguments: {json.dumps(args)}")
			sys.exit(1)
	
print(json.dumps({}))
sys.exit(1)