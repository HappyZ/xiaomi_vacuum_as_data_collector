import os


def get_env_var(name):
    return os.environ[name] if name in os.environ else None


def set_env_var(name, value):
    os.environ[name] = value


def clear_env_var(name):
    del os.environ[name]
