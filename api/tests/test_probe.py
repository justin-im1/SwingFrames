from __future__ import annotations

from app.media.probe import parse_probe, rotation_from_probe


def test_measured_fps_from_packets_not_container_rate() -> None:
    data = {
        "streams": [
            {
                "width": 640,
                "height": 480,
                "duration": "2.0",
                "nb_read_packets": "48",
                "r_frame_rate": "60/1",
                "avg_frame_rate": "30/1",
                "codec_name": "h264",
            }
        ],
        "format": {"duration": "2.0"},
    }
    probed = parse_probe(data)
    assert probed.packet_count == 48
    assert probed.fps == 24.0
    assert probed.width == 640


def test_rotation_from_side_data() -> None:
    data = {
        "streams": [
            {
                "width": 1920,
                "height": 1080,
                "side_data_list": [{"rotation": -90}],
            }
        ]
    }
    assert rotation_from_probe(data) == -90


def test_no_rotation() -> None:
    data = {"streams": [{"width": 640, "height": 480, "side_data_list": []}]}
    assert rotation_from_probe(data) is None
