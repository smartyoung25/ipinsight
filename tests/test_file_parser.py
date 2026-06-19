"""file_parser 파싱 + 품질 검사 테스트"""
import sys
import io
import zipfile
import pytest

sys.path.insert(0, "C:/IPinsight")
from api.services.file_parser import parse_file, quality_check, SUPPORTED_EXTENSIONS


def test_txt_utf8():
    content = b"claim 1. A data processing device comprising: a processor; a memory;"
    text = parse_file("patent.txt", content)
    assert "claim" in text.lower()


def test_txt_cp949():
    content = "청구항 1. 데이터 처리 장치.".encode("cp949")
    text = parse_file("patent.txt", content)
    assert "청구항" in text


def test_unsupported_extension():
    with pytest.raises(ValueError, match="지원하지 않는"):
        parse_file("doc.xyz", b"data")


def test_quality_good():
    text = "claim 1. " + "A " * 100
    q = quality_check(text)
    assert q["quality"] == "good"
    assert q["has_claims"] is True


def test_quality_poor_short():
    q = quality_check("짧음")
    assert q["quality"] == "poor"
    assert any("길이" in w for w in q["warnings"])


def test_quality_no_claims():
    text = "This is a long text without any claim or patent terminology. " * 5
    q = quality_check(text)
    assert any("청구항" in w for w in q["warnings"])


def test_hwpx_parse():
    """HWPX (ZIP+XML) 최소 구조 파싱 테스트"""
    ns = "http://www.hancom.co.kr/hwpml/2012/paragraph"
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<root xmlns:hp="{ns}">
  <hp:t>청구항 1. 테스트 장치.</hp:t>
</root>""".encode("utf-8")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("Contents/section0.xml", xml)
    content = buf.getvalue()

    text = parse_file("patent.hwpx", content)
    assert "청구항" in text


def test_supported_extensions():
    assert ".pdf" in SUPPORTED_EXTENSIONS
    assert ".hwp" in SUPPORTED_EXTENSIONS
    assert ".hwpx" in SUPPORTED_EXTENSIONS
    assert ".docx" in SUPPORTED_EXTENSIONS
    assert ".txt" in SUPPORTED_EXTENSIONS
