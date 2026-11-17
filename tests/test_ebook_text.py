import struct
import unittest

from core.workers.conversion.ebook_text import _read_mobi


class EbookTextTests(unittest.TestCase):
    def test_uncompressed_mobi_text_is_decoded(self):
        text = b"<p>Hello MOBI</p>"
        header = struct.pack(">HHIHHH", 1, 0, len(text), 1, 4096, 0) + b"\0\0"
        first = 78 + 16
        pdb = bytearray(first)
        struct.pack_into(">H", pdb, 76, 2)
        struct.pack_into(">I", pdb, 78, first)
        struct.pack_into(">I", pdb, 86, first + len(header))
        self.assertEqual(_read_mobi(bytes(pdb) + header + text, lambda value: value), text.decode())

    def test_encrypted_mobi_is_rejected(self):
        header = struct.pack(">HHIHHH", 1, 0, 1, 1, 4096, 1) + b"\0\0"
        first = 78 + 16
        pdb = bytearray(first)
        struct.pack_into(">H", pdb, 76, 2)
        struct.pack_into(">I", pdb, 78, first)
        struct.pack_into(">I", pdb, 86, first + len(header))
        with self.assertRaises(ValueError):
            _read_mobi(bytes(pdb) + header + b"x", lambda value: value)
