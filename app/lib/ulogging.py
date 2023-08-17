# ulogging.py
# Forked from https://github.com/pfalcon/pycopy-lib/blob/master/ulogging/metadata.txt
#
# Copyright (c) 2014-2021 Paul Sokolovsky
# Copyright (c) 2014-2020 pycopy-lib contributors
# Released under the MIT License (MIT) - see LICENSE file


import sys

CRITICAL = 50
ERROR = 40
WARNING = 30
INFO = 20
DEBUG = 10
NOTSET = 0

S_EMERG = const(0)
S_ALERT = const(1)
S_CRIT = const(2)
S_ERR = const(3)
S_WARN = const(4)
S_NOTICE = const(5)
S_INFO = const(6)
S_DEBUG = const(7)

F_USER = const(1)

_level_dict = {
    CRITICAL: "CRIT",
    ERROR: "ERROR",
    WARNING: "WARN",
    INFO: "INFO",
    DEBUG: "DEBUG",
}

_syslog_mapping = {
    CRITICAL: S_CRIT,
    ERROR: S_ERR,
    WARNING: S_WARN,
    INFO: S_INFO,
    DEBUG: S_DEBUG
}

_stream = sys.stderr


def _send_to_syslog(level, msg, facility=F_USER):
    if _socket is None:
        return

    data = "<%d>projector_cabinet: %s" % (_syslog_mapping.get(level) + (facility << 3), msg)

    try:
        _socket.send(data.encode())
    except Exception as e:
        error(f"Error while sending logs to syslog: {e}")


class Logger:
    level = NOTSET

    def __init__(self, name):
        self.name = name

    def _level_str(self, level):
        l = _level_dict.get(level)
        if l is not None:
            return l
        return "LVL%s" % level

    def setLevel(self, level):
        self.level = level

    def isEnabledFor(self, level):
        return level >= (self.level or _level)

    def log(self, level, msg, *args):
        if args:
            msg = msg % args

        if _syslog_send_all:
            _send_to_syslog(level, msg)

        if level >= (self.level or _level):
            not _syslog_send_all and _send_to_syslog(level, msg)
            if self.name is None:
                _stream.write("[%s]" % (self._level_str(level)))
            else:
                _stream.write("[%s][%s]" % (self._level_str(level), self.name))
            print(msg, file=_stream)

    def debug(self, msg, *args):
        self.log(DEBUG, msg, *args)

    def info(self, msg, *args):
        self.log(INFO, msg, *args)

    def warning(self, msg, *args):
        self.log(WARNING, msg, *args)

    def error(self, msg, *args):
        self.log(ERROR, msg, *args)

    def critical(self, msg, *args):
        self.log(CRITICAL, msg, *args)

    def exc(self, e, msg, *args):
        self.log(ERROR, msg, *args)
        sys.print_exception(e, _stream)

    def exception(self, msg, *args):
        self.exc(sys.exc_info()[1], msg, *args)


_level = INFO
_loggers = {}
_socket = None
_syslog_send_all = True


def getLogger(name):
    if name in _loggers:
        return _loggers[name]
    l = Logger(name)
    _loggers[name] = l
    return l


def info(msg, *args):
    getLogger(None).info(msg, *args)


def debug(msg, *args):
    getLogger(None).debug(msg, *args)


def error(msg, *args):
    getLogger(None).error(msg, *args)


def basicConfig(level=INFO, filename=None, stream=None, format=None, syslog=None, syslog_send_all=True):
    """
    Syslog option takes tuple: (IP, port)
    If specified than syslog formatted messages are sent there over UDP

    syslog_send_all defines if all logs no matter level should be sent to syslog. Default True
    """
    global _level, _stream, _socket, _syslog_send_all
    _level = level
    if stream:
        _stream = stream
    if filename is not None:
        print("logging.basicConfig: filename arg is not supported")
    if format is not None:
        print("logging.basicConfig: format arg is not supported")
    if syslog is not None:
        import socket
        print("ulogging remote syslog sending enabled")
        _addr = socket.getaddrinfo(syslog[0], syslog[1])[0][-1]
        _socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        _socket.connect(_addr)
        _syslog_send_all = syslog_send_all
