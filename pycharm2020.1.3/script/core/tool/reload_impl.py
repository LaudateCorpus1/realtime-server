# -*- coding: utf-8 -*-
import sys
import inspect
from importlib import reload

from core.mobilelog.LogManager import LogManager

MODULE_RELOAD_BLACKLIST = ["os", "sys"]
ATTR_RELOAD_BLACKLIST = ['__module__', '_reload_all', '__dict__', '__weakref__', '__doc__', ]
_IGNORE_ATTRS = []


def is_in_module_blacklist(mod_name):
    blacklist = MODULE_RELOAD_BLACKLIST
    return mod_name in blacklist


def is_in_attr_blacklist(attr_name):
    blacklist = ATTR_RELOAD_BLACKLIST
    return attr_name in blacklist


def is_data_provider(mod_name):
    module_names = mod_name.split(".")
    if module_names[0] == "data":
        return True
    elif module_names[0] == "common" and len(module_names) > 1 and module_names[1] == "cdata":
        return True
    else:
        return False


def update_module(mod_name, old_content, new):
    new_content = new.__dict__
    ok = True
    for attr_name, attr_new_info in new_content.items():
        if is_in_attr_blacklist(attr_name):
            continue
        attr_old_info = old_content.get(attr_name, None)

        if attr_old_info is None:
            setattr(new, attr_name, attr_new_info)
        else:
            if inspect.isclass(attr_new_info):
                ok = update_class(attr_old_info, attr_new_info, None)
                setattr(new, attr_name, attr_old_info)
            elif inspect.isfunction(attr_new_info):
                ok = update_func(attr_old_info, attr_new_info)
                setattr(new, attr_name, attr_old_info)
            elif is_data_provider(mod_name) and attr_name == "Data":
                ok = update_attr(attr_old_info, attr_new_info)
                setattr(new, attr_name, attr_old_info)
            else:
                setattr(new, attr_name, attr_new_info)

        if not ok:
            return False

    # if not getattr(new, '_reload_all', False):
    #     new.__dict__.update(old_content)
    return True


def update_class(old_class, new_class, reload_all):
    for name, attr in tuple(old_class.__dict__.items()):  # delete function
        if name in new_class.__dict__:
            continue

        if not inspect.isfunction(attr):
            continue

        type.__delattr__(old_class, name)

    ok = True
    for name, attr in new_class.__dict__.items():
        if name not in old_class.__dict__:  # new attribute
            setattr(old_class, name, attr)
            continue

        old_attr = old_class.__dict__[name]
        new_attr = attr
        if inspect.isfunction(old_attr) and inspect.isfunction(new_attr):
            if not update_func(old_attr, new_attr):
                setattr(old_class, name, new_attr)
        elif isinstance(new_attr, staticmethod) or isinstance(new_attr, classmethod):
            if not update_func(old_attr.__func__, new_attr.__func__):
                old_attr.__func__ = new_attr.__func__
                ok = False
        elif reload_all and name not in _IGNORE_ATTRS:
            setattr(old_class, name, attr)

        if not ok:
            return False

    return True


def update_func(old_fun, new_fun, update_cell_depth=2):
    old_cell_num = 0
    if old_fun.__closure__:
        # old_cell_num = len(old_fun.func_closure)
        old_cell_num = len(old_fun.__closure__)
    new_cell_num = 0
    if new_fun.__closure__:
        new_cell_num = len(new_fun.__closure__)

    if old_cell_num != new_cell_num:
        return False

    setattr(old_fun, '__code__', new_fun.__code__)
    setattr(old_fun, '__defaults__', new_fun.__defaults__)
    setattr(old_fun, '__doc__', new_fun.__doc__)
    setattr(old_fun, '__dict__', new_fun.__dict__)

    if not (update_cell_depth and old_cell_num):
        return True

    for index, cell in enumerate(old_fun.__closure__):
        ok = True
        if inspect.isfunction(cell.cell_contents):
            ok = update_func(cell.cell_contents, new_fun.__closure__[index].cell_contents, update_cell_depth - 1)

        if not ok:
            return False

    return True


def update_attr(old_attr, new_attr):
    if type(old_attr) == list and type(new_attr) == list:
        old_attr.clear()
        for elem in new_attr:
            old_attr.append(elem)
        return True
    elif type(old_attr) == dict and type(new_attr) == dict:
        old_attr.clear()
        for k, v in new_attr.items():
            old_attr[k] = v
        return True
    elif type(old_attr) == set and type(new_attr) == dict:
        old_attr.clear()
        for elem in new_attr:
            old_attr.add(elem)
        return True
    else:
        return False


def reload_module(mod_name):
    # 模块是否已加载
    old_mod_info = sys.modules.get(mod_name, None)
    if old_mod_info is None:
        return False

    # 是否是制定无需热更模块
    if is_in_module_blacklist(mod_name):
        return False

    old_mod_content = dict(old_mod_info.__dict__)

    # 更新模块
    new_mod_info = reload(old_mod_info)

    LogManager.get_logger().info("reload module %s" % mod_name)
    return update_module(mod_name, old_mod_content, new_mod_info)


ALLOWED_PREFIX = ["ui.", "common.", "entities.", "helper.", "client", "game_world.", "visual_"]


def _iter_all_reloadable_mods():
    for mod_name, mod in sys.modules.items():
        if any((mod_name.startswith(x) for x in ALLOWED_PREFIX)) and mod:
            yield mod_name


def reload_by_prefix(prefix):
    for mod_name in _iter_all_reloadable_mods():
        if mod_name.startswith(prefix):
            if not reload_module(mod_name):
                print('ERROR: reload %s failed' % mod_name)
    return True


def reload_common():
    for mod_name in _iter_all_reloadable_mods():
        reload_module(mod_name)
