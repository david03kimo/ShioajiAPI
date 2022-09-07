from shioaji.backend.http import HttpApi as _http


def get_backends():
    apis = {
        'http': _http,
    }
    return apis
