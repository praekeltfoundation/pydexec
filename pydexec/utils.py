def arg_from_env(command, env_key, default=None, required=False, remove=True):
    """
    Convert the environment variable ``env_key`` to a program argument, if
    it is set. Note that this will remove ``env_key`` from the command's
    environment by default.

    :param command: the Command object to use
    :param env_key: environment variable name to use
    :param default: default value if the environment variable is not set
    :param required: raise an error if the environment variable is not set
    :param remove: remove the variable from the command's environment

    :returns: the Command object
    """
    env_val = _arg_from_env(
        command, env_key, remove, default, required, 'an argument')
    return command.args(env_val) if env_val is not None else command


def opt_from_env(command, opt_key, env_key, default=None, required=False,
                 remove=True):
    """
    Convert the environment variable ``env_key`` to the program option
    ``opt_key``, if the variable is set. Note that this will remove
    ``env_key`` from the command's environment by default.

    :param command: the Command object to use
    :param opt_key: the option to set (e.g. ``--volume``)
    :param env_key: environment variable name to use
    :param default: default value if the environment variable is not set
    :param required: raise an error if the environment variable is not set
    :param remove: remove the variable from the command's environment

    :returns: the Command object
    """
    env_val = _arg_from_env(
        command, env_key, remove, default, required,
        'option "{}"'.format(opt_key))
    return command.args(opt_key, env_val) if env_val is not None else command


def _arg_from_env(command, env_key, remove, default, required, missing_str):
    """ Shared logic to fetch a program argument from the environment. """
    env_op = command._env.pop if remove else command._env.get
    env_val = env_op(env_key, default)

    if required and env_val is None:
        raise RuntimeError(
            'Environment variable "{}" is required to determine {} for '
            'program "{}"'.format(env_key, missing_str, command._program))

    return env_val
