import unittest

from zelotes_mouse.protocol import (
    OP_LIGHT,
    ProtocolError,
    checksum,
    encode_dpi_stage,
    feature,
    init_link,
    light_block,
    select_profile,
    set_polling,
    settings_packets,
    split_block,
    upload_header,
)


class ProtocolTest(unittest.TestCase):
    def test_checksum_matches_windows_formula(self) -> None:
        head = bytes([0x01, 0x88, 0, 0, 0, 0, 0])
        total = -1
        for byte in reversed(head):
            total -= byte
        self.assertEqual(checksum(head), total & 0xFF)
        self.assertEqual(checksum(head), 0x76)

    def test_checksum_wraps_past_255(self) -> None:
        head = bytes([0xFF] * 7)
        self.assertEqual(checksum(head), (0xFF - (sum(head) & 0xFF)) & 0xFF)

    def test_feature_sum_is_0xff(self) -> None:
        packet = init_link()
        self.assertEqual(packet, bytes([0x01, 0x88, 0, 0, 0, 0, 0, 0x76]))
        self.assertEqual(sum(packet) & 0xFF, 0xFF)

    def test_settings_sequence(self) -> None:
        packets = settings_packets(0, 1000)
        self.assertEqual([item[0] for item in packets], [0x01, 0x02, 0x03])
        self.assertEqual(packets[1][1], 1)
        self.assertEqual(packets[2][1:3], bytes([0x01, 0x01]))

    def test_profile_and_polling(self) -> None:
        self.assertEqual(select_profile(0)[0:2], bytes([0x02, 0x01]))
        self.assertEqual(set_polling(1, 1000)[0:3], bytes([0x03, 0x02, 0x01]))
        self.assertEqual(sum(set_polling(0, 125)) & 0xFF, 0xFF)

    def test_upload_header_and_split(self) -> None:
        header = upload_header(0x0D, 0)
        self.assertEqual(header[0:3], bytes([0x0D, 0x01, 0x80]))
        self.assertEqual(sum(header) & 0xFF, 0xFF)
        first, second = split_block(bytes([0xAB]) + bytes(127))
        self.assertEqual(len(first), 64)
        self.assertEqual(len(second), 64)
        self.assertEqual(first[0], 0xAB)

    def test_dpi_stage_matches_monitor_table(self) -> None:
        self.assertEqual(encode_dpi_stage(15), 0x22)
        self.assertEqual(encode_dpi_stage(25), 0x39)
        self.assertEqual(encode_dpi_stage(40), 0x5C)
        self.assertEqual(encode_dpi_stage(70), 0xD0)
        self.assertEqual(encode_dpi_stage(100), 0xF3)
        self.assertEqual(encode_dpi_stage(1), 4)

    def test_light_block_follows_monitor_layout(self) -> None:
        block = light_block("padrao", 1, 10, 10, (255, 0, 16), (15, 25, 40, 70, 100))
        self.assertEqual(len(block), 128)
        self.assertEqual(block[0:2], b"\xff\xff")
        self.assertEqual(block[0x40], 0x0F)
        self.assertEqual(block[0x47:0x4C], bytes([1, 1, 3, 100, 100]))
        self.assertEqual(block[0x54:0x59], bytes([0x22, 0x39, 0x5C, 0xD0, 0xF3]))
        self.assertEqual(block[0x5C:0x61], block[0x54:0x59])
        self.assertEqual(block[0x64], 0x1F)
        self.assertEqual(block[0x68:0x6B], bytes([255, 0, 16]))
        self.assertEqual(block[0x7D:0x80], bytes([255, 0, 16]))
        header = upload_header(OP_LIGHT, 0)
        self.assertEqual(header[0:3], bytes([0x0C, 0x01, 0x80]))
        flowing = light_block("fluxo", 2, 1, 0, (0, 0, 0), (15, 25, 40, 70, 100))
        self.assertEqual(flowing[0x47:0x4A], bytes([6, 0x5F, 10]))

    def test_rejects_bad_profile(self) -> None:
        with self.assertRaises(ProtocolError):
            feature(1, 2, 3, 4, 5, 6, 7, 8)
        with self.assertRaises(ProtocolError):
            select_profile(8)
        with self.assertRaises(ProtocolError):
            set_polling(0, 2000)


if __name__ == "__main__":
    unittest.main()
