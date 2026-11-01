"""Drag and drop of image files onto one widget of the Settings window (the background drop zone).

Tk has no built-in support for files dropped from Explorer, so on Windows this hooks the standard
WM_DROPFILES message with ctypes (no extra package). Everywhere else it does nothing. The part
that decides which dropped files are images (``split_images``) is plain Python and is tested.
"""

import os
import sys

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}


def split_images(paths):
    """(images, rejected): the dropped files PhraseLock can use as a background, and the others."""
    images, rejected = [], []
    for path in paths:
        ok = not os.path.isdir(path) and os.path.splitext(str(path))[1].lower() in IMAGE_EXT
        (images if ok else rejected).append(path)
    return images, rejected


# ---------------------------------------------------------------------------
# Windows hook
# ---------------------------------------------------------------------------

def _safe_call(callback, paths):
    try:
        callback(paths)
    except Exception:
        import traceback
        _log("Handling dropped files failed:\n" + traceback.format_exc())


_hooks = {}          # hwnd -> original window procedure
_handlers = {}       # hwnd -> (widget, callback)
_keep = {}           # keeps the ctypes callback alive for the life of the process


def _log(text):
    try:
        from config import log
        log(text)
    except Exception:
        pass


def enable_widget(widget, callback):
    """Accept dropped files on this one widget only. callback(list_of_paths) is called in the Tk
    thread. Returns True when the hook is in place (False off Windows or when it cannot be done)."""
    if sys.platform != "win32":
        return False
    try:
        import ctypes
        from ctypes import wintypes

        user32, shell32 = ctypes.windll.user32, ctypes.windll.shell32
        WM_DROPFILES, WM_COPYGLOBALDATA, MSGFLT_ALLOW, GWL_WNDPROC = 0x233, 0x49, 1, -4
        wndproc_t = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, wintypes.HWND, wintypes.UINT, wintypes.WPARAM,
                                       wintypes.LPARAM)
        set_long = getattr(user32, "SetWindowLongPtrW", None) or user32.SetWindowLongW
        set_long.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
        set_long.restype = ctypes.c_void_p
        user32.CallWindowProcW.argtypes = [ctypes.c_void_p, wintypes.HWND, wintypes.UINT, wintypes.WPARAM,
                                           wintypes.LPARAM]
        user32.CallWindowProcW.restype = ctypes.c_ssize_t
        shell32.DragQueryFileW.argtypes = [ctypes.c_void_p, wintypes.UINT, wintypes.LPWSTR, wintypes.UINT]
        shell32.DragQueryFileW.restype = wintypes.UINT
        shell32.DragFinish.argtypes = [ctypes.c_void_p]

        def read_paths(hdrop):
            count = shell32.DragQueryFileW(hdrop, 0xFFFFFFFF, None, 0)
            paths = []
            for i in range(count):
                length = shell32.DragQueryFileW(hdrop, i, None, 0)
                buffer = ctypes.create_unicode_buffer(length + 1)
                shell32.DragQueryFileW(hdrop, i, buffer, length + 1)
                paths.append(buffer.value)
            shell32.DragFinish(hdrop)
            return paths

        def proc(hwnd, msg, wparam, lparam):
            if msg == WM_DROPFILES:
                try:
                    paths = read_paths(wparam)
                    target_widget, target_callback = _handlers[hwnd]
                    target_widget.after(0, lambda: _safe_call(target_callback, paths))
                except Exception:
                    import traceback
                    _log("Drop failed:\n" + traceback.format_exc())
                return 0
            if msg == 0x82:      # WM_NCDESTROY: the window is going away, forget it (handles get reused)
                old = _hooks.pop(hwnd, None)
                _handlers.pop(hwnd, None)
            else:
                old = _hooks.get(hwnd)
            return user32.CallWindowProcW(old, hwnd, msg, wparam, lparam)

        new_proc = _keep.get("proc")
        if new_proc is None:
            _keep["proc"] = new_proc = wndproc_t(proc)
        widget.update_idletasks()
        hwnd = widget.winfo_id()
        _handlers[hwnd] = (widget, callback)
        if hwnd in _hooks:
            return True
        user32.ChangeWindowMessageFilterEx(hwnd, WM_DROPFILES, MSGFLT_ALLOW, None)
        user32.ChangeWindowMessageFilterEx(hwnd, WM_COPYGLOBALDATA, MSGFLT_ALLOW, None)
        shell32.DragAcceptFiles(hwnd, True)
        old = set_long(hwnd, GWL_WNDPROC, ctypes.cast(new_proc, ctypes.c_void_p))
        if old:
            _hooks[hwnd] = old
            return True
        return False
    except Exception:
        import traceback
        _log("Drag and drop could not be enabled:\n" + traceback.format_exc())
        return False
