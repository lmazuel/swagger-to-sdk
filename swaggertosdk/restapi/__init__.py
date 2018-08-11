from logging import Filter
import uuid

from flask import Flask
from flask_request_id import RequestID
from gevent.pywsgi import WSGIHandler
from jsonrpc.backend.flask import api
from werkzeug.contrib.fixers import ProxyFix

from ..SwaggerToSdkMain import generate_sdk
from ..SwaggerToSdkCore import CONFIG_FILE, DEFAULT_COMMIT_MESSAGE

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app)
RequestID(app)
app.add_url_rule('/', 'api', api.as_view(), methods=['POST'])

@api.dispatcher.add_method
def ping(*args, **kwargs):
    return "Pong!"

@api.dispatcher.add_method
def generate_project(*args, **kwargs):
    # Get required parameter
    rest_api_id = kwargs['rest_api_id']
    sdk_id = kwargs['sdk_id']
    project = kwargs['project']

    generate_sdk(
        os.environ['GH_TOKEN'],
        CONFIG_FILE,
        project,
        rest_api_id,
        sdk_id,
        None, # No PR repo id
        DEFAULT_COMMIT_MESSAGE,
        'master',
        None # Destination branch
    )

@app.route('/healthz', methods=['GET'])
def healthz():
    return "Pong!"

class RealRequestFilter(Filter): # pylint: disable=too-few-public-methods
    def filter(self, record):
        return "GET /healthz" not in record.msg

class ProxyAwareHandler(WSGIHandler):
    def get_environ(self):
        if self.headers.get("x-request-id") is None:
            self.headers["X-Request-ID"] = str(uuid.uuid4())

        # Fix up client_address from headers
        forward = self.headers.get("x-forwarded-for")
        if forward is not None:
            if "," in forward:
                forward = forward.split(',')[-1].strip()
            if ":" in forward:
                addr, port = forward.split(':')
                self.client_address = (addr, port)
            else:
                self.client_address = (forward, "")

        env = super().get_environ()

        # Fix up wsgi.url_scheme from headers
        scheme = self.headers.getheader("x-forwarded-proto")
        if scheme is not None:
            env['wsgi.url_scheme'] = scheme

        return env

    def format_request(self):
        msg = super().format_request()
        request_id = self.headers.get("x-request-id")
        if request_id is not None:
            msg = request_id + ":" + msg
        return msg

from .github import *
from .travis import *
