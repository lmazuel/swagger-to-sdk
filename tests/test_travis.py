import traceback
from subprocess import CalledProcessError

import pytest

from swaggertosdk.restapi.travis import (ChecksCommentableObject,
                                         exception_to_output)


def test_checks_commentable_object():
    obj = ChecksCommentableObject()

    obj.create_comment("comment a")
    with pytest.raises(ValueError):
        val = obj.getvalue()

    obj.create_comment("title a\ncomment a")
    val = obj.getvalue()
    assert val["title"] == "title a"
    assert val["summary"] == "comment a"

    obj.create_comment("### title a\ncomment a")
    val = obj.getvalue()
    assert val["title"] == "title a"
    assert val["summary"] == "comment a"

    obj.create_comment("### title b\ncomment b")
    val = obj.getvalue()
    assert val["title"] == "title b"
    assert val["summary"] == "comment b"

    obj.create_comment("### title b \n comment b ")
    val = obj.getvalue()
    assert val["title"] == "title b"
    assert val["summary"] == "comment b"

def test_exception_to_output():
    try:
        raise AttributeError("Message 123")
    except Exception as ex: # pylint: disable=broad-except
        result = exception_to_output(ex, traceback.format_exc())

    assert result["title"] == "Failed with AttributeError"

    assert "AttributeError was encountered" in result["summary"]
    assert "Message 123" in result["summary"]

    assert "Traceback" in result["text"]
    assert "test_travis.py" in result["text"]
    assert "AttributeError" in result["text"]
    assert "Message 123" in result["text"]

def test_exception_to_output_calledprocesserror():
    try:
        raise CalledProcessError(3, "foobarcmd", "Message 123")
    except Exception as ex: # pylint: disable=broad-except
        result = exception_to_output(ex, traceback.format_exc())

    assert result["title"] == "Failed with CalledProcessError"

    assert "CalledProcessError was encountered" in result["summary"]
    assert "Message 123" not in result["summary"]

    assert "Traceback" not in result["text"]
    assert "test_travis.py" not in result["text"]
    assert "CalledProcessError" not in result["text"]

    assert "foobarcmd" in result["text"]
    assert "code 3" in result["text"]
    assert "Message 123" in result["text"]
