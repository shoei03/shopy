import json

import pytest

from shopy.utils.json import read_json


def test_read_json_reads_valid_json(tmp_path):
    # Arrange
    data = {"foo": "bar", "num": 123}
    json_file = tmp_path / "test.json"
    json_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    # Act
    result = read_json(json_file)

    # Assert
    assert result == data


def test_read_json_raises_file_not_found(tmp_path):
    non_existent_file = tmp_path / "no_such_file.json"
    with pytest.raises(FileNotFoundError):
        read_json(non_existent_file)


def test_read_json_raises_json_decode_error(tmp_path):
    invalid_json_file = tmp_path / "invalid.json"
    invalid_json_file.write_text("{invalid json:}", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        read_json(invalid_json_file)
