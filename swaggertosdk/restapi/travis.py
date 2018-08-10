import logging
import os
import traceback
from io import StringIO
from subprocess import CalledProcessError

from flask import jsonify, request
from github import Github

from . import app
from .github_handler import rest_pr_management

_LOGGER = logging.getLogger("swaggertosdk.restapi.travis")

class ChecksCommentableObject:
    def __init__(self):
        self._text = ""

    def create_comment(self, text):
        self._text = text

    def getvalue(self):
        sep = self._text.index("\n")
        title = self._text[:sep].lstrip("#").strip()
        summary = self._text[sep+1:].strip()

        return {
            "title": title,
            "summary": summary
        }

class RequestFilter(logging.Filter): # pylint: disable=too-few-public-methods
    def __init__(self, request_id): # pylint: disable=super-init-not-called
        self._request_id = request_id

    def filter(self, record):
        return 'requestid' in record.__dict__ and record.requestid == self._request_id

def exception_to_output(err, trace):
    error_type = type(err).__name__
    if isinstance(err, CalledProcessError):
        content = "Command: {}\n".format(err.cmd)
        content += "Finished with return code {}\n".format(err.returncode)
        if err.output:
            content += "and output:\n```shell\n{}\n```".format(err.output)
        else:
            content += "and no output"
    else:
        content = "```python\n{}\n```".format(trace)

    response = {
        "title": "Failed with {}".format(error_type),
        "summary": "{} was encountered while attempting to generate this SDK: {}".format(error_type, str(err)),
        "text": content
    }
    return response

@app.route('/travis', methods=['POST'])
def travis_notify():
    """Travis main endpoint."""
    log = StringIO()
    root_logger = logging.getLogger()
    handler = logging.StreamHandler(log)
    handler.setFormatter(logging.Formatter("%(levelname)s:%(name)s:%(message)s"))
    handler.addFilter(RequestFilter(request.environ.get("FLASK_REQUEST_ID")))
    root_logger.addHandler(handler)

    try:
        body = request.get_json()
        try:
            target_slug = body["target_slug"]
            target_base = body["target_base"] if "target_base" in body else "master"
            pr_num = body["pull_request_num"]
            repo_slug = body["repo_slug"]
        except Exception: # pylint: disable=broad-except
            return {'message': 'Malformed body'}

        _LOGGER.info("Received build notification for https://github.com/%s/pull/%s", repo_slug, pr_num)

        sdk_tag = target_slug.split("/")[-1].lower()
        commentable = ChecksCommentableObject()
        gh_token = os.environ["GH_TOKEN"]
        github_con = Github(gh_token)
        sdk_pr_target_repo = github_con.get_repo(target_slug)
        restapi_repo = github_con.get_repo(repo_slug)
        rest_pr = restapi_repo.get_pull(pr_num)
        rest_pr_management(commentable, rest_pr, sdk_pr_target_repo, sdk_tag, target_base)

        return jsonify({
            "success": True,
            "text": log.getvalue(),
            "output": commentable.getvalue()
        })
    except Exception as ex:  # pylint: disable=broad-except
        return jsonify({
            "success": False,
            "text": log.getvalue(),
            "output": exception_to_output(ex, traceback.format_exc())
        })
    finally:
        root_logger.removeHandler(handler)
        log.close()
