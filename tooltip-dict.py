import time
import ctypes
from ctypes import wintypes, c_void_p,c_wchar_p,c_int
import struct
import threading
import mouse, keyboard
from bs4 import BeautifulSoup
import urllib.request
import win32clipboard
from win32 import win32gui
import wmi
import win32process
import psutil

#############################################################################################################################
# Based on G33kDude's System wide tooltips using python 3 (https://gist.github.com/G33kDude/6dab4ee16713802b2770ccf4e9f033d4)
# And Erriez's win32clipboard_example.py (https://gist.github.com/Erriez/8d0f9d0855708da7fd85c45e6e9a62f6)
#############################################################################################################################

c=wmi.WMI()

# Append the apps you want to use
app_list=["SumatraPDF.exe".lower()]

def get_app_exe(hwnd):
    """Get applicatin filename given hwnd."""
    pid= win32process.GetWindowThreadProcessId(hwnd)
    return psutil.Process(pid[-1]).name().lower()


# --- Windows API Setup ---

# User32\SendMessage
SendMessage = ctypes.windll.user32.SendMessageW
SendMessage.restype = wintypes.LPARAM # LRESULT
SendMessage.argtypes = (
    wintypes.HWND,   # hWnd
    wintypes.UINT,   # Msg
    wintypes.WPARAM, # wParam
    wintypes.LPARAM, # lParam
)

# User32\PostMessage
PostMessage = ctypes.windll.user32.PostMessageW
PostMessage.restype = SendMessage.restype

# User32\CreateWindowEx
CreateWindowEx = ctypes.windll.user32.CreateWindowExW
CreateWindowEx.restype = wintypes.HWND
CreateWindowEx.argtypes = (
    wintypes.DWORD,     # dwExStyle
    wintypes.LPWSTR,    # lpClassName
    wintypes.LPWSTR,    # lpWindowName
    wintypes.DWORD,     # dwStyle
    wintypes.INT,       # X
    wintypes.INT,       # Y
    wintypes.INT,       # nWidth
    wintypes.INT,       # nHeight
    wintypes.HWND,      # hWndParent
    wintypes.HWND,      # hMenu
    wintypes.HINSTANCE, # hInstance
    wintypes.LPVOID,    # lpParam
)

# User32\GetMessage
GetMessage = ctypes.windll.user32.GetMessageW
GetMessage.restype = wintypes.BOOL
GetMessage.argtypes = (
    wintypes.LPMSG, # lpMsg
    wintypes.HWND,  # hWnd
    wintypes.UINT,  # wMsgFilterMin
    wintypes.UINT,  # wMsgFilterMax
)

# User32\TranslateMessage
TranslateMessage = ctypes.windll.user32.TranslateMessage
TranslateMessage.restype = wintypes.BOOL
TranslateMessage.argtypes = (wintypes.LPMSG,)

# User32\DispatchMessage
DispatchMessage = ctypes.windll.user32.DispatchMessageW
DispatchMessage.restype = wintypes.LPARAM # LRESULT

# Constants
TOOLTIPS_CLASSW = "tooltips_class32"
TTF_TRACK = 0x20
WM_USER = 0x400
TTM_ADDTOOLW = WM_USER + 50
TTM_TRACKACTIVATE = WM_USER + 17
TTM_TRACKPOSITION = WM_USER + 18
TTS_NOPREFIX = 0x2
TTS_ALWAYSTIP = 0x1
WS_EX_TOPMOST = 0x8


# --- Class Definitions ---

class ToolTip():
    class TOOLINFOW(ctypes.Structure):
        _fields_ = [
            ("cbSize",     wintypes.UINT),
            ("uFlags",     wintypes.UINT),
            ("hwnd",       wintypes.HWND),
            ("uId",        wintypes.LPVOID),
            ("rect",       wintypes.RECT),
            ("hinst",      wintypes.HINSTANCE),
            ("lpszText",   wintypes.LPWSTR),
            ("lParam",     wintypes.LPARAM),
            ("lpReserved", wintypes.LPVOID),
        ]

    def __init__(self, text, x=0, y=0):
        # Save configuration data
        self.text = text
        self.x, self.y = x, y

        # Start the creation thread
        self.evt_created = threading.Event()
        threading.Thread(target=self.create, daemon=True).start()

        # Wait for the tooltip to be created
        self.evt_created.wait()

    def create(self):
        # Create a window to house the tooltip
        self.hwnd = CreateWindowEx(
            WS_EX_TOPMOST,   # DWORD     dwExStyle
            TOOLTIPS_CLASSW, # LPCWSTR   lpClassName
            None,            # LPCWSTR   lpWindowName
            TTS_NOPREFIX |
            TTS_ALWAYSTIP,   # DWORD     dwStyle
            0,               # int       X
            0,               # int       Y
            0,               # int       nWidth
            0,               # int       nHeight
            None,            # HWND      hWndParent
            None,            # HWND      hMenu
            None,            # HINSTANCE hInstance
            None,            # LPVOID    lpParam
        )

        # Create the tooltip information
        ti = self.TOOLINFOW(ctypes.sizeof(self.TOOLINFOW))
        ti.uFlags = TTF_TRACK
        ti.lpszText = self.text

        # Configure the window with the tooltip data
        SendMessage(self.hwnd, TTM_ADDTOOLW, 0, ctypes.addressof(ti))
        self.update_pos(self.x, self.y, True)
        SendMessage(self.hwnd, TTM_TRACKACTIVATE, 1, ctypes.addressof(ti))

        # Raise the tooltip created event
        self.evt_created.set()

        # Process messages for that window
        x = wintypes.MSG()
        while True:
            bRet = GetMessage(ctypes.byref(x), self.hwnd, 0, 0)
            if bRet in (0, -1): break
            TranslateMessage(ctypes.byref(x))
            DispatchMessage(ctypes.byref(x))

    def destroy(self):
        PostMessage(self.hwnd, 0x10, 0, 0)

    def update_pos(self, x, y, wait=False):
        self.x, self.y = x, y
        long_words = struct.unpack('L', struct.pack('hh', x, y))[0]
        Message = SendMessage if wait else PostMessage
        Message(self.hwnd, TTM_TRACKPOSITION, 0, long_words)


def get_clipboard():
    clipboard_dict = {}

    # Open clipboard
    win32clipboard.OpenClipboard()

    # Create list clipboard formats
    cf = [win32clipboard.EnumClipboardFormats(0)]
    while cf[-1]:
        cf.append(win32clipboard.EnumClipboardFormats(cf[-1]))
    cf.pop()

    # Get clipboard format name and data
    for format_id in cf:
        try:
            format_name = win32clipboard.GetClipboardFormatName(format_id)
        except:
            format_name = ""
        try:
            format_data = win32clipboard.GetClipboardData(format_id)
        except:
            format_data = None

        clipboard_dict[format_id] = {'name': format_name, 'data': format_data}

    # Close clipboard
    win32clipboard.CloseClipboard()

    return clipboard_dict

def set_clipboard(clipboard_dict):
    # Open and empty clipboard
    win32clipboard.OpenClipboard()
    win32clipboard.EmptyClipboard()

    # Set clipboard data per clipboard format
    for format_id in clipboard_dict:
        try:
            format_data = clipboard_dict.get(format_id).get('data')
            if format_data:
                win32clipboard.SetClipboardData(format_id, format_data)
        except:
            print('Error writing format ID {}'.format(format_id))

    # Close clipboard
    win32clipboard.CloseClipboard()


_GetWindowText = ctypes.WinDLL('user32').GetWindowTextW
_GetWindowText.argtypes = [c_void_p,c_wchar_p,c_int]
_GetWindowText.restype = c_int

def GetWindowText(h):
    b = ctypes.create_unicode_buffer(255)
    _GetWindowText(h,b,255)
    return b.value

# --- Entry Point ---

def make_tooltip():
    try:
        GetCursorPos = ctypes.windll.user32.GetCursorPos
        GetCursorPos.restype = wintypes.BOOL
        GetCursorPos.argtypes = (wintypes.LPPOINT,)

        point=win32gui.GetCursorPos()
        # I know GetCursorPos is duplicated, but I am not good at dealing with ctypes, so I had to use it twice in different ways to use win32gui module also.
        # If you have better solution, pelase make a Pull Request!
        hwnd=win32gui.WindowFromPoint(point)
        window_text=win32gui.GetWindowText(hwnd)
        while(window_text == ""):
            hwnd=win32gui.GetParent(hwnd)     
            window_text=win32gui.GetWindowText(hwnd)
        if window_text=="Chrome Legacy Window":
            hwnd=win32gui.GetParent(hwnd)     
            window_text=win32gui.GetWindowText(hwnd)
        app_name=get_app_exe(hwnd)
        print(window_text)
        if (not app_name in app_list):
            return
        tmp_clipboard_dict=get_clipboard()
        time.sleep(0.2)
        keyboard.press_and_release("ctrl+c")
        time.sleep(0.4)
        win32clipboard.OpenClipboard()
        word=win32clipboard.GetClipboardData()
        win32clipboard.CloseClipboard()
        set_clipboard(tmp_clipboard_dict)
        
        # You have to create your own code to get the search result of the word you want
        # Below is an example.
        url = "https://www.some_dict.com/search?q=" + word
        html = urllib.request.urlopen(url)
        soup=BeautifulSoup(html,"html.parser")
        ul=soup.find("ul",class_="list_search")
        result=""
        li_list=ul.find_all("li")
        for li in li_list:
            result=result+li.get_text()+" "

        # Create a tooltip
        tt = ToolTip(result)

        # Make tooltip follow cursor
        pt = wintypes.POINT()
        for i in range(30):
            GetCursorPos(ctypes.byref(pt))
            tt.update_pos(pt.x + 8, pt.y + 16)
            time.sleep(0.05)

        # Destroy the tooltip
        tt.destroy()
    except:
        pass

def main():
    mouse.on_double_click(make_tooltip)

    keyboard.wait()


if __name__ == '__main__':
    main()