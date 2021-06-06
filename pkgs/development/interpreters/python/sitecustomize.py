"""
This is a Nix-specific module for discovering modules built with Nix.

The module recursively adds paths that are on `NIX_PYTHONPATH` to `sys.path`. In
order to process possible `.pth` files `site.addsitedir` is used.

The paths listed in `PYTHONPATH` are added to `sys.path` afterwards, but they
will be added before the entries we add here and thus take precedence.

Note the `NIX_PYTHONPATH` environment variable is unset in order to prevent leakage.

Similarly, this module listens to the environment variable `NIX_PYTHONEXECUTABLE`
and sets `sys.executable` to its value.
"""
import site
import sys
import os
import functools
import threading

paths = os.environ.pop('NIX_PYTHONPATH', None)
if paths:
    functools.reduce(lambda k, p: site.addsitedir(p, k), paths.split(':'), site._init_pathinfo())

# Check whether we are in a venv or virtualenv.
# For Python 3 we check whether our `base_prefix` is different from our current `prefix`.
# For Python 2 we check whether the non-standard `real_prefix` is set.
# https://stackoverflow.com/questions/1871549/determine-if-python-is-running-inside-virtualenv
in_venv = (sys.version_info.major == 3 and sys.prefix != sys.base_prefix) or (sys.version_info.major == 2 and hasattr(sys, "real_prefix"))

if not in_venv:
    executable = os.environ.pop('NIX_PYTHONEXECUTABLE', None)
    prefix = os.environ.pop('NIX_PYTHONPREFIX', None)

    if 'PYTHONEXECUTABLE' not in os.environ and executable is not None:
        sys.executable = executable
    if prefix is not None:
        # Sysconfig does not like it when sys.prefix is set to None
        sys.prefix = sys.exec_prefix = prefix
        site.PREFIXES.insert(0, prefix)


# ----------------------------------------------------------

import _warnings
import importlib.machinery
import os
import sys
import inspect
import traceback
from importlib import _bootstrap, import_module
from importlib._bootstrap import _ModuleLockManager, _find_and_load_unlocked, _lock_unlock_module, _find_spec_legacy, \
    _ImportLockContext
from os.path import dirname

from importlib._bootstrap_external import _NamespacePath, _path_join, _path_isdir, _path_isfile, _make_relax_case, \
    _path_stat

_relax_case = _make_relax_case()


def _find_spec(name, path, target=None):
    """Find a module's spec."""
    meta_path = sys.meta_path
    if meta_path is None:
        # PyImport_Cleanup() is running or has been called.
        raise ImportError("sys.meta_path is None, Python is likely "
                          "shutting down")

    if not meta_path:
        _warnings.warn('sys.meta_path is empty', ImportWarning)

    # We check sys.modules here for the reload case.  While a passed-in
    # target will usually indicate a reload there is no guarantee, whereas
    # sys.modules provides one.
    is_reload = name in sys.modules
    for finder in meta_path:
        with _ImportLockContext():
            try:
                find_spec = finder.find_spec
            except AttributeError:
                spec = _find_spec_legacy(finder, name, path)
                if spec is None:
                    continue
            else:
                spec = find_spec(name, path, target)
        if spec is not None:
            # The parent import may have already imported this module.
            if not is_reload and name in sys.modules:
                module = sys.modules[name]
                try:
                    __spec__ = module.__spec__
                except AttributeError:
                    # We use the found spec since that is the one that
                    # we would have used if the parent module hadn't
                    # beaten us to the punch.
                    return spec
                else:
                    if __spec__ is None:
                        return spec
                    else:
                        return __spec__
            else:
                return spec
    else:
        return None


def _find_and_load_unlocked(name, import_):
    path = None
    parent = name.rpartition('.')[0]
    if parent:
        # if '#' in name:
        #     parent = name.split('#')[0] + '#' + parent
        parent_base_name = parent.rpartition('#')[-1]
        if parent not in sys.modules:
            _bootstrap._call_with_frames_removed(import_, parent_base_name)
            # _find_and_load(parent.rpartition('#')[-1], import_)
        if parent not in sys.modules \
                and parent_base_name in sys.modules:
            parent = parent_base_name
        # Crazy side-effects!
        if name in sys.modules:
            return sys.modules[name]
        parent_module = sys.modules[parent]
        try:
            path = parent_module.__path__
        except AttributeError:
            msg = (_bootstrap._ERR_MSG + '; {!r} is not a package').format(name, parent)
            raise ModuleNotFoundError(msg, name=name) from None
    if name == 'attr':
        x=1
    spec = _bootstrap._find_spec(name, path)
    if spec is None:
        raise ModuleNotFoundError(_bootstrap._ERR_MSG.format(name.rpartition('#')[-1]), name=name)
    else:
        module = _bootstrap._load_unlocked(spec)
    if parent:
        # Set the module as an attribute on its parent.
        parent_module = sys.modules[parent]
        setattr(parent_module, name.rpartition('.')[2], module)
    return module


def _find_and_load_original(name, import_):
    """Find and load the module."""
    with _ModuleLockManager(name):
        module = sys.modules.get(name, 1)
        if module == 1:
            return _find_and_load_unlocked(name, import_)

    if module is None:
        message = ('import of {} halted; '
                   'None in sys.modules'.format(name))
        raise ModuleNotFoundError(message, name=name)

    _lock_unlock_module(name)
    return module


import atexit
# monkey patch _bootstrap._find_and_load
def _find_and_load(name, import_):
    """Find and load the module."""
    # name_lookup = name
    # print(f"_find_and_load: {name}")
    if name == "attr.exceptions":
        x=1
    if "atexit" in name:
        x=1
    if name.endswith("attr.converters"):
        x=1
    if '#' not in name:
        local_dir = find_local_dir()
        if local_dir:
            name_local = make_local_module_name(name, local_dir)
            try:
                return _find_and_load_original(name_local, import_)
            except ModuleNotFoundError:
                pass
    return _find_and_load_original(name, import_)


def is_module_dir(dir):
    return os.path.isfile(dir + "/__init__.py")


def contains_local_site_dir(dir):
    return os.path.isdir(dir + '/_site_local')


def contains_module(dir, module_name):
    return \
        os.path.isdir(dir + '/' + module_name + '/__init__.py') \
        or os.path.isfile(dir + '/' + module_name + '.py')


def find_local_dir():
    """
    This tries to find a local/private site packages directory for the module issuing the current import.
    A fallback is made to the local site packages of parent modules only if those resist within the same package.
    :return directory or None if no local site dir could be found
    """
    stack = list(reversed(traceback.extract_stack()))
    # stack = inspect.stack()
    importing_module_dir = None
    for idx, e in enumerate(stack):
        if e.name == "_find_and_load":
            try:
                importing_module = stack[idx + 1]
                importing_module_dir = dirname(importing_module.filename)
                if importing_module_dir != '':
                    break
            except IndexError:
                return None
    else:
        if importing_module_dir is None:
            raise Exception("Cannot find module requesting import")


    if '/_site_local' in importing_module_dir:
        return importing_module_dir.rpartition('/_site_local')[0] + '/_site_local'

    # search for '_site_local' directory
    # start from directory of importing module and continue with parents
    # stop if the current directory is not a python module
    search_dir = importing_module_dir
    while True:
        local_site_dir = search_dir + '/' + "_site_local"
        if os.path.isdir(local_site_dir):
                # and contains_module(local_site_dir, module_to_import):
            # return the real path to prevent redundant imports
            # of module referenced via symlink from different locations
            # print(f"found local site dir: {local_site_dir}")
            return os.path.realpath(local_site_dir)
        # switch to parent module
        search_dir += "/.."
        if not os.path.isdir(search_dir):
            break
        if not is_module_dir(search_dir) \
                and not contains_local_site_dir(search_dir):
            break
        # print(f"Next search dir: {search_dir}")
    return None


def make_local_module_name(base_name, local_dir):
    # return base_name + f"{local_dir.replace('.', ':').replace('/', '_').replace('-', '_')}"
    return f"{local_dir.replace('.', ',')}#{base_name}"


# custom finder to prefer modules from local site dir
class PathFinder(importlib.machinery.PathFinder):
    # pass
    # @classmethod
    # def _path_hooks(cls, path):
    #     """Search sys.path_hooks for a finder for 'path'."""
    #     if sys.path_hooks is not None and not sys.path_hooks:
    #         _warnings.warn('sys.path_hooks is empty', ImportWarning)
    #     for hook in sys.path_hooks:
    #         try:
    #             return hook(path)
    #         except ImportError:
    #             continue
    #     else:
    #         return None
    #
    @classmethod
    def _path_importer_cache(cls, path):
        """Get the finder for the path entry from sys.path_importer_cache.

        If the path entry is not in the cache, find the appropriate finder
        and cache it. If no finder is available, store None.

        """
        if path == '':
            try:
                path = os.getcwd()
            except FileNotFoundError:
                # Don't cache the failure as the cwd can easily change to
                # a valid directory later on.
                return None
        try:
            finder = sys.path_importer_cache[path]
        except KeyError:
            finder = cls._path_hooks(path)
            sys.path_importer_cache[path] = finder
        return finder

    @classmethod
    def _get_spec(cls, fullname, path, target=None):
        """Find the loader or namespace_path for this module/package name."""

        local_dir = None
        base_name = fullname
        if '#' in fullname:
            local_dir, base_name = fullname.replace(',', '.').split('#')

        if local_dir:
            if len(path) == 1 and '_site_local' in path[0]:
                subdir = path[0].rpartition('/_site_local')[-1]
            else:
                subdir = ''
            finder = cls._path_importer_cache(local_dir + subdir)
            if finder is not None:
                if hasattr(finder, 'find_spec'):
                    spec = finder.find_spec(base_name, target)
                else:
                    spec = cls._legacy_get_spec(base_name, finder)
                if spec:
                    spec.name = fullname
                    spec.loader.name = fullname
                    return spec

        return super()._get_spec(base_name, path, target=target)

    @classmethod
    def find_spec(cls, fullname, path=None, target=None):
        """Try to find a spec for 'fullname' on sys.path or 'path'.

        The search is based on sys.path_hooks and sys.path_importer_cache.
        """
        if path is None:
            path = sys.path
        spec = cls._get_spec(fullname, path, target)
        if spec is None:
            return None
        elif spec.loader is None:
            namespace_path = spec.submodule_search_locations
            if namespace_path:
                # We found at least one namespace path.  Return a spec which
                # can create the namespace package.
                spec.origin = None
                spec.submodule_search_locations = _NamespacePath(fullname, namespace_path, cls._get_spec)
                return spec
            else:
                return None
        else:
            return spec


class FileFinder(importlib.machinery.FileFinder):
    pass
    def find_spec(self, fullname, target=None):
        """Try to find a spec for the specified module.

        Returns the matching spec, or None if not found.
        """
        is_namespace = False
        tail_module = fullname.rpartition('.')[2]
        try:
            mtime = _path_stat(self.path or os.getcwd()).st_mtime
        except OSError:
            mtime = -1
        if mtime != self._path_mtime:
            self._fill_cache()
            self._path_mtime = mtime
        # tail_module keeps the original casing, for __file__ and friends
        if _relax_case():
            cache = self._relaxed_path_cache
            cache_module = tail_module.lower()
        else:
            cache = self._path_cache
            cache_module = tail_module
        # Check if the module is the name of a directory (and thus a package).
        if cache_module in cache:
            base_path = _path_join(self.path, tail_module)
            for suffix, loader_class in self._loaders:
                init_filename = '__init__' + suffix
                full_path = _path_join(base_path, init_filename)
                if _path_isfile(full_path):
                    return self._get_spec(loader_class, fullname, full_path, [base_path], target)
            else:
                # If a namespace package, return the path if we don't
                #  find a module in the next section.
                is_namespace = _path_isdir(base_path)
        # Check for a file w/ a proper suffix exists.
        for suffix, loader_class in self._loaders:
            full_path = _path_join(self.path, tail_module + suffix)
            _bootstrap._verbose_message('trying {}', full_path, verbosity=2)
            if cache_module + suffix in cache:
                if _path_isfile(full_path):
                    return self._get_spec(loader_class, fullname, full_path,
                                          None, target)
        if is_namespace:
            _bootstrap._verbose_message('possible namespace for {}', base_path)
            spec = _bootstrap.ModuleSpec(fullname, None)
            spec.submodule_search_locations = [base_path]
            return spec
        return None


# PathEntryFinder = importlib.machinery.FileFinder
# loader_details = (importlib.machinery.SourceFileLoader,
#                   importlib.machinery.SOURCE_SUFFIXES)
# sys.path_hooks = [FileFinder.path_hook(loader_details)]
#
# insert custom PathFinder with higher priority than the existing one
for idx, p in enumerate(sys.meta_path):
    if p.__name__ == "PathFinder":
        sys.meta_path.insert(idx, PathFinder)
        break
else:
    sys.meta_path.append(PathFinder)

if not hasattr(_bootstrap, "_find_and_load_original"):
    # print("monkey patching _find_and_load")
    _bootstrap._find_and_load_original = _bootstrap._find_and_load
    _bootstrap._find_and_load = _find_and_load
    _bootstrap._find_spec = _find_spec

PathFinder.invalidate_caches()

# import module_a
# import module_b

# del sys.modules['atexit']
# import pytest
