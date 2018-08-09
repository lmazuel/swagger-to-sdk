from gevent import monkey
monkey.patch_all()

import sys
from swaggertosdk.SwaggerToSdkMain import main
main(sys.argv)
