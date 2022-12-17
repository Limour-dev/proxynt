import asyncio
import json
import logging
import os.path

import sys
from optparse import OptionParser

import tornado.ioloop
import tornado.web

from common.logger_factory import LoggerFactory
from constant.system_constant import SystemConstant
from context.context_utils import ContextUtils
from entity.server_config_entity import ServerConfigEntity
from server.admin_http_handler import AdminHtmlHandler, AdminHttpApiHandler
from server.heart_beat_task import HeartBeatTask
from server.websocket_handler import MyWebSocketaHandler

DEFAULT_CONFIG = './config_s.json'
DEFAULT_LOGGER_LEVEL = logging.INFO
DEFAULT_WEBSOCKET_PATH = '/ws'

name_to_level = {
    'debug': logging.DEBUG,
    'info': logging.INFO,
    'warn': logging.WARN,
    'error': logging.ERROR
}


def load_config() -> ServerConfigEntity:
    parser = OptionParser(usage="usage: %prog -c config_s.json ")
    parser.add_option("-c", "--config",
                      type='str',
                      dest='config',
                      default=DEFAULT_CONFIG,
                      help="config json file"
                      )
    parser.add_option("-l", "--level",
                      type='str',
                      dest='log_level',
                      default='info',
                      help="log level: debug, info, warn , error"
                      )
    (options, args) = parser.parse_args()
    config_path = options.config
    log_level = options.log_level
    if log_level not in name_to_level:
        print('invalid log level.')
        sys.exit()
    ContextUtils.set_log_level(name_to_level[log_level])
    print(f'use config path : {config_path}')
    config_path = config_path or DEFAULT_CONFIG
    with open(config_path, 'r') as rf:
        content_str = rf.read()
    ContextUtils.set_config_file_path(os.path.abspath(config_path))
    content_json: ServerConfigEntity = json.loads(content_str)
    password = content_json.get('password', '')
    port = content_json.get('port', )
    path = content_json.get('path', DEFAULT_WEBSOCKET_PATH)
    if not path.startswith('/'):
        print('path should startswith "/" ')
        sys.exit()
    if not port:
        raise Exception('server port is required')
    ContextUtils.set_password(password)
    ContextUtils.set_websocket_path(path)
    ContextUtils.set_port(int(port))
    ContextUtils.set_log_file(content_json.get('log_file'))
    return content_json


if __name__ == "__main__":
    server_config = load_config()
    ContextUtils.set_client_name_to_config_in_server(server_config.get('client_config') or {})
    websocket_path = ContextUtils.get_websocket_path()
    admin_html_path = websocket_path + ('' if websocket_path.endswith('/') else '/') + SystemConstant.ADMIN_PATH  # 管理网页路径
    admin_api_path = websocket_path + ('' if websocket_path.endswith('/') else '/') + SystemConstant.ADMIN_PATH + '/api'  # 管理api路径
    status_url_path = websocket_path + ('' if websocket_path.endswith('/') else '/') + SystemConstant.ADMIN_PATH + '/static'  # static
    static_path = os.path.join(os.path.dirname(__file__), 'server', 'template')
    template_path = os.path.join(os.path.dirname(__file__), 'server', 'template')
    app = tornado.web.Application([
        (websocket_path, MyWebSocketaHandler),
        (admin_html_path, AdminHtmlHandler),
        (admin_api_path, AdminHttpApiHandler),
    ], static_path=static_path, static_url_prefix=status_url_path, template_path=template_path, debug=False)
    app.listen(ContextUtils.get_port(), chunk_size=65536 * 2)
    LoggerFactory.get_logger().info(f'start server at port {ContextUtils.get_port()}, websocket_path: {websocket_path}, admin_path: {admin_html_path}')
    heart_beat_task = HeartBeatTask(asyncio.get_event_loop())
    tornado.ioloop.PeriodicCallback(heart_beat_task.run, SystemConstant.HEART_BEAT_INTERVAL * 1000).start()
    tornado.ioloop.IOLoop.current().start()
