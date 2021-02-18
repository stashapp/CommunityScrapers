#!/usr/bin/env python
# coding: utf-8

"""
A .torrent file parser for both Python 2 and 3

Usage:

    data = parse_torrent_file(filename)

    # or

    with open(filename, 'rb') as f: # the binary mode 'b' is necessary
        data = TorrentFileParser(f).parse()

    # then you can edit the data

    data['announce-list'].append(['http://127.0.0.1:8080'])

    # and create a new torrent file from data

    create_torrent_file('new.torrent', data)

    # or

    with open('new.torrent', 'wb') as f:
        f.write(TorrentFileCreator(data).encode())

    # or you don't deal with file, just object in memory

    data = decode(b'i12345e') # data = 12345
    content = encode(data) # content = b'i12345e'

"""

from __future__ import print_function, unicode_literals

import argparse
import binascii
import collections
import io
import json
import sys
import warnings

try:
    FileNotFoundError
except NameError:
    # Python 2 do not have FileNotFoundError, use IOError instead
    # noinspection PyShadowingBuiltins
    FileNotFoundError = IOError

try:
    # noinspection PyPackageRequirements
    from chardet import detect as _detect
except ImportError:
    def _detect(_):
        warnings.warn("No chardet module installed, encoding will be utf-8")
        return {'encoding': 'utf-8', 'confidence': 1}

try:
    # noinspection PyUnresolvedReferences
    # For Python 2
    str_type = unicode
except NameError:
    # For Python 3
    str_type = str

__all__ = [
    'InvalidTorrentDataException',
    'BEncoder',
    'BDecoder',
    'encode',
    'decode',
    'TorrentFileParser',
    'create_torrent_file',
    'parse_torrent_file',
]

__version__ = '0.3.0'


def detect(content):
    return _detect(content)['encoding']


class InvalidTorrentDataException(Exception):
    def __init__(self, pos, msg=None):
        msg = msg or "Invalid torrent format when read at pos {pos}"
        msg = msg.format(pos=pos)
        super(InvalidTorrentDataException, self).__init__(msg)


class __EndCls(object):
    pass


_END = __EndCls()


def _check_hash_field_params(name, value):
    return isinstance(name, str_type) \
           and isinstance(value, tuple) and len(value) == 2 \
           and isinstance(value[0], int) and isinstance(value[1], bool)


class TorrentFileParser(object):

    TYPE_LIST = 'list'
    TYPE_DICT = 'dict'
    TYPE_INT = 'int'
    TYPE_STRING = 'string'
    TYPE_END = 'end'

    LIST_INDICATOR = b'l'
    DICT_INDICATOR = b'd'
    INT_INDICATOR = b'i'
    END_INDICATOR = b'e'
    STRING_INDICATOR = b''
    STRING_DELIMITER = b':'

    HASH_FIELD_PARAMS = {
        # field length need_list
        'pieces': (20, True),
        'ed2k': (16, False),
        'filehash': (20, False),
    }

    TYPES = [
        (TYPE_LIST, LIST_INDICATOR),
        (TYPE_DICT, DICT_INDICATOR),
        (TYPE_INT, INT_INDICATOR),
        (TYPE_END, END_INDICATOR),
        (TYPE_STRING, STRING_INDICATOR),
    ]

    def __init__(
            self, fp, use_ordered_dict=False, encoding='utf-8', errors='strict',
            hash_fields=None, hash_raw=False,
    ):
        """
        :param fp: a **binary** file-like object to parse,
          which means need 'b' mode when use built-in open function
        :param bool use_ordered_dict: Use collections.OrderedDict as dict
          container default False, which mean use built-in dict
        :param str encoding: file content encoding, default utf-8, use 'auto'
          to enable charset auto detection (need 'chardet' package installed)
        :param str errors: how to deal with encoding error when try to parse
          string from content with ``encoding``
        :param Dict[str, Tuple[int, bool]] hash_fields: extra fields should
          be treated as hash value. dict key is the field name, value is a
          two-element tuple of (hash_block_length, as_a_list).
          See :any:`hash_field` for detail
        """
        if getattr(fp, 'read', ) is None \
                or getattr(fp, 'seek') is None:
            raise ValueError('Parameter fp needs a file like object')

        self._pos = 0
        self._encoding = encoding
        self._content = fp
        self._use_ordered_dict = use_ordered_dict
        self._error_handler = errors
        self._hash_fields = dict(TorrentFileParser.HASH_FIELD_PARAMS)
        if hash_fields is not None:
            for k, v in hash_fields.items():
                if _check_hash_field_params(k, v):
                    self._hash_fields[k] = v
                else:
                    raise ValueError(
                        "Invalid hash field parameter, it should be type of "
                        "Dict[str, Tuple[int, bool]]"
                    )
        self._hash_raw = bool(hash_raw)

    def hash_field(self, name, block_length=20, need_list=False):
        """
        Let field with the `name` to be treated as hash value, don't decode it
        as a string.

        :param str name: field name
        :param int block_length: hash block length for split
        :param bool need_list:  if True, when the field only has one block(
          or even empty) its parse result will be a one-element list(
          or empty list); If False, will be a string in 0 or 1 block condition
        :return: return self, so you can chained call
        """
        v = (block_length, need_list)
        if _check_hash_field_params(name, v):
            self._hash_fields[name] = v
        else:
            raise ValueError("Invalid hash field parameter")
        return self

    def parse(self):
        """
        :rtype: dict|list|int|str|bytes
        :raise: :any:`InvalidTorrentDataException` when parse failed or error
          happened when decode string using specified encoding
        """
        self._restart()
        data = self._next_element()

        try:
            c = self._read_byte(1, True)
            raise InvalidTorrentDataException(
                0, 'Expect EOF, but get [{}] at pos {}'.format(c, self._pos)
            )
        except EOFError:  # expect EOF
            pass

        return data

    def _read_byte(self, count=1, raise_eof=False):
        assert count >= 0
        gotten = self._content.read(count)
        if count != 0 and len(gotten) == 0:
            if raise_eof:
                raise EOFError()
            raise InvalidTorrentDataException(
                self._pos,
                'Unexpected EOF when reading torrent file'
            )
        self._pos += count
        return gotten

    def _seek_back(self, count):
        self._content.seek(-count, 1)
        self._pos = self._pos - count

    def _restart(self):
        self._content.seek(0, 0)
        self._pos = 0

    def _dict_items_generator(self):
        while True:
            k = self._next_element()
            if k is _END:
                return
            if not isinstance(k, str_type):
                raise InvalidTorrentDataException(
                    self._pos, "Type of dict key can't be " + type(k).__name__
                )
            if k in self._hash_fields:
                v = self._next_hash(*self._hash_fields[k])
            else:
                v = self._next_element(k)
            if k == 'encoding':
                self._encoding = v
            yield k, v

    def _next_dict(self):
        data = collections.OrderedDict() if self._use_ordered_dict else dict()
        for key, element in self._dict_items_generator():
            data[key] = element
        return data

    def _list_items_generator(self):
        while True:
            element = self._next_element()
            if element is _END:
                return
            yield element

    def _next_list(self):
        return [element for element in self._list_items_generator()]

    def _next_int(self, end=END_INDICATOR):
        value = 0
        char = self._read_byte(1)
        neg = False
        while char != end:
            if not neg and char == b'-':
                neg = True
            elif not b'0' <= char <= b'9':
                raise InvalidTorrentDataException(self._pos - 1)
            else:
                value = value * 10 + int(char) - int(b'0')
            char = self._read_byte(1)
        return -value if neg else value

    def _next_string(self, need_decode=True, field=None):
        length = self._next_int(self.STRING_DELIMITER)
        raw = self._read_byte(length)
        if need_decode:
            encoding = self._encoding
            if encoding == 'auto':
                self.encoding = encoding = detect(raw)
            try:
                string = raw.decode(encoding, self._error_handler)
            except UnicodeDecodeError as e:
                msg = [
                    "Fail to decode string at pos {pos} using encoding ",
                    e.encoding
                ]
                if field:
                    msg.extend([
                        ' when parser field "', field, '"'
                        ', maybe it is an hash field. ',
                        'You can use self.hash_field("', field, '") ',
                        'to let it be treated as hash value, ',
                        'so this error may disappear'
                    ])
                raise InvalidTorrentDataException(
                    self._pos - length + e.start,
                    ''.join(msg)
                )
            return string
        return raw

    def _next_hash(self, p_len, need_list):
        raw = self._next_string(need_decode=False)
        if len(raw) % p_len != 0:
            raise InvalidTorrentDataException(
                self._pos - len(raw), "Hash bit length not match at pos {pos}"
            )
        if self._hash_raw:
            return raw
        res = [
            binascii.hexlify(chunk).decode('ascii')
            for chunk in (raw[x:x+p_len] for x in range(0, len(raw), p_len))
        ]
        if len(res) == 0 and not need_list:
            return ''
        if len(res) == 1 and not need_list:
            return res[0]
        return res

    @staticmethod
    def _next_end():
        return _END

    def _next_type(self):
        for (element_type, indicator) in self.TYPES:
            indicator_length = len(indicator)
            char = self._read_byte(indicator_length)
            if indicator == char:
                return element_type
            self._seek_back(indicator_length)
        raise InvalidTorrentDataException(self._pos)

    def _type_to_func(self, t):
        return getattr(self, '_next_' + t)

    def _next_element(self, field=None):
        element_type = self._next_type()
        if element_type is TorrentFileParser.TYPE_STRING and field is not None:
            element = self._type_to_func(element_type)(field=field)
        else:
            element = self._type_to_func(element_type)()
        return element


class BEncoder(object):

    TYPES = {
        (dict,): TorrentFileParser.TYPE_DICT,
        (list,): TorrentFileParser.TYPE_LIST,
        (int,): TorrentFileParser.TYPE_INT,
        (str_type, bytes): TorrentFileParser.TYPE_STRING,
    }

    def __init__(self, data, encoding='utf-8', hash_fields=None):
        """
        :param dict|list|int|str data: data will be encoded
        :param str encoding: string field output encoding
        :param List[str] hash_fields: see
          :any:`TorrentFileParser.__init__`
        """
        self._data = data
        self._encoding = encoding
        self._hash_fields = list(TorrentFileParser.HASH_FIELD_PARAMS.keys())
        if hash_fields is not None:
            self._hash_fields.extend(str_type(hash_fields))

    def hash_field(self, name):
        """
        see :any:`TorrentFileParser.hash_field`

        :param str name:
        :return: return self, so you can chained call
        """
        return self._hash_fields.append(str_type(name))

    def encode(self):
        """
        Encode to bytes

        :rtype: bytes
        """
        return b''.join(self._output_element(self._data))

    def encode_to_filelike(self):
        """
        Encode to a file-like(BytesIO) object

        :rtype: BytesIO
        """
        return io.BytesIO(self.encode())

    def _output_string(self, data):
        if isinstance(data, str_type):
            data = data.encode(self._encoding)
        yield str(len(data)).encode('ascii')
        yield TorrentFileParser.STRING_DELIMITER
        yield data

    @staticmethod
    def _output_int(data):
        yield TorrentFileParser.INT_INDICATOR
        yield str(data).encode('ascii')
        yield TorrentFileParser.END_INDICATOR

    def _output_decode_hash(self, data):
        if isinstance(data, str_type):
            data = [data]
        result = []
        for hash_line in data:
            if not isinstance(hash_line, str_type):
                raise InvalidTorrentDataException(
                    None,
                    "Hash must be " + str_type.__name__ + " not " +
                    type(hash_line).__name__,
                )
            if len(hash_line) % 2 != 0:
                raise InvalidTorrentDataException(
                    None,
                    "Hash(" + hash_line + ") length(" + str(len(hash_line)) +
                    ") is a not even number",
                )
            try:
                raw = binascii.unhexlify(hash_line)
            except binascii.Error as e:
                raise InvalidTorrentDataException(
                    None, str(e),
                )
            result.append(raw)
        for x in self._output_string(b''.join(result)):
            yield x

    def _output_dict(self, data):
        yield TorrentFileParser.DICT_INDICATOR
        for k, v in data.items():
            if not isinstance(k, str_type):
                raise InvalidTorrentDataException(
                    None, "Dict key must be " + str_type.__name__,
                )
            for x in self._output_element(k):
                yield x
            if k in self._hash_fields:
                for x in self._output_decode_hash(v):
                    yield x
            else:
                for x in self._output_element(v):
                    yield x
        yield TorrentFileParser.END_INDICATOR

    def _output_list(self, data):
        yield TorrentFileParser.LIST_INDICATOR
        for v in data:
            for x in self._output_element(v):
                yield x
        yield TorrentFileParser.END_INDICATOR

    def _type_to_func(self, t):
        return getattr(self, '_output_' + t)

    def _output_element(self, data):
        for types, t in self.TYPES.items():
            if isinstance(data, types):
                # noinspection PyCallingNonCallable
                return self._type_to_func(t)(data)
        raise InvalidTorrentDataException(
            None,
            "Invalid type for torrent file: " + type(data).__name__,
        )


class BDecoder(object):
    def __init__(
        self, data, use_ordered_dict=False, encoding='utf-8', errors='strict',
        hash_fields=None, hash_raw=False,
    ):
        """
        See :any:`TorrentFileParser.__init__` for parameter description.

        :param bytes data: raw data to be decoded
        :param bool use_ordered_dict:
        :param str encoding:
        :param str errors:
        :param Dict[str, Tuple[int, bool]] hash_fields:
        :param bool hash_raw:
        """
        self._parser = TorrentFileParser(
            io.BytesIO(bytes(data)),
            use_ordered_dict,
            encoding,
            errors,
            hash_fields,
            hash_raw,
        )

    def hash_field(self, name, block_length=20, need_dict=False):
        """
        See :any:`TorrentFileParser.hash_field` for parameter description

        :param name:
        :param block_length:
        :param need_dict:
        :return: return self, so you can chained call
        """
        self._parser.hash_field(name, block_length, need_dict)
        return self

    def decode(self):
        return self._parser.parse()


def encode(data, encoding='utf-8', hash_fields=None):
    """
    Shortcut function for encode python object to torrent file format(bencode)

    See :any:`BEncoder.__init__` for parameter description

    :param dict|list|int|str|bytes data: data to be encoded
    :param str encoding:
    :param List[str] hash_fields:
    :rtype: bytes
    """
    return BEncoder(data, encoding, hash_fields).encode()


def decode(
        data, use_ordered_dict=False, encoding='utf-8', errors='strict',
        hash_fields=None, hash_raw=False,
):
    """
    Shortcut function for decode bytes as torrent file format(bencode) to python
    object

    See :any:`BDecoder.__init__` for parameter description

    :param bytes data: raw data to be decoded
    :param bool use_ordered_dict:
    :param str encoding:
    :param str errors:
    :param Dict[str, Tuple[int, bool]] hash_fields:
    :param bool hash_raw:
    :rtype: dict|list|int|str|bytes|bytes
    """
    return BDecoder(
        data, use_ordered_dict, encoding, errors, hash_fields, hash_raw,
    ).decode()


def parse_torrent_file(
        filename, use_ordered_dict=False, encoding='utf-8', errors='strict',
        hash_fields=None, hash_raw=False,
):
    """
    Shortcut function for parse torrent object using TorrentFileParser

    See :any:`TorrentFileParser.__init__` for parameter description

    :param str filename: torrent filename
    :param bool use_ordered_dict:
    :param str encoding:
    :param str errors:
    :param Dict[str, Tuple[int, bool]] hash_fields:
    :param bool hash_raw:
    :rtype: dict|list|int|str|bytes
    """
    with open(filename, 'rb') as f:
        return TorrentFileParser(
            f, use_ordered_dict, encoding, errors, hash_fields, hash_raw,
        ).parse()


def create_torrent_file(filename, data, encoding='utf-8', hash_fields=None):
    """
    Shortcut function for create a torrent file using BEncoder

    see :any:`BDecoder.__init__` for parameter description

    :param str filename: output torrent filename
    :param dict|list|int|str|bytes data:
    :param str encoding:
    :param List[str] hash_fields:
    """
    with open(filename, 'wb') as f:
        f.write(BEncoder(data, encoding, hash_fields).encode())


def __main():
    parser = argparse.ArgumentParser()
    parser.add_argument('file', nargs='?', default='',
                        help='input file, will read form stdin if empty')
    parser.add_argument('--dict', '-d', action='store_true', default=False,
                        help='use built-in dict, default will be OrderedDict')
    parser.add_argument('--sort', '-s', action='store_true', default=False,
                        help='sort output json item by key')
    parser.add_argument('--indent', '-i', type=int, default=None,
                        help='json output indent for every inner level')
    parser.add_argument('--ascii', '-a', action='store_true', default=False,
                        help='ensure output json use ascii char, '
                             'escape other char use \\u')
    parser.add_argument('--coding', '-c', default='utf-8',
                        help='string encoding, default "utf-8"')
    parser.add_argument('--errors', '-e', default='strict',
                        help='decoding error handler, default "strict", you can'
                             ' use "ignore" or "replace" to avoid exception')
    parser.add_argument('--version', '-v', action='store_true', default=False,
                        help='print version and exit')
    args = parser.parse_args()

    if args.version:
        print(__version__)
        exit(0)

    try:
        if args.file == '':
            target_file = io.BytesIO(
                getattr(sys.stdin, 'buffer', sys.stdin).read()
            )
        else:
            target_file = open(args.file, 'rb')
    except FileNotFoundError:
        sys.stderr.write('File "{}" not exist\n'.format(args.file))
        exit(1)

    # noinspection PyUnboundLocalVariable
    data = TorrentFileParser(
        target_file, not args.dict, args.coding, args.errors
    ).parse()

    data = json.dumps(
        data, ensure_ascii=args.ascii,
        sort_keys=args.sort, indent=args.indent
    )

    print(data)


if __name__ == '__main__':
    __main()
