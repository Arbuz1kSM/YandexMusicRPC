#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <wchar.h>
#include <stdio.h>

int WINAPI wWinMain(HINSTANCE instance, HINSTANCE previous, PWSTR arguments, int show) {
    (void)instance; (void)previous; (void)show;
    wchar_t root[32768], python[32768], command[32768];
    DWORD length = GetModuleFileNameW(NULL, root, 32768);
    if (!length || length >= 32768) return 1;
    wchar_t *slash = wcsrchr(root, L'\\');
    if (!slash) return 1;
    *slash = L'\0';
    int a = _snwprintf(python, 32768, L"%ls\\runtime\\pythonw.exe", root);
    int b = _snwprintf(command, 32768,
        L"\"%ls\" \"%ls\\app\\embedded_main.py\" %ls", python, root, arguments);
    if (a < 0 || a >= 32768 || b < 0 || b >= 32768) return 1;
    STARTUPINFOW startup = {0};
    PROCESS_INFORMATION process = {0};
    startup.cb = sizeof(startup);
    if (!CreateProcessW(python, command, NULL, NULL, FALSE, 0, NULL, root, &startup, &process)) {
        wchar_t message[256];
        _snwprintf(message, 256, L"Unable to start Yandex Music RPC (Windows error %lu).\nPlease reinstall the application.", GetLastError());
        MessageBoxW(NULL, message, L"Yandex Music RPC", MB_OK | MB_ICONERROR);
        return 1;
    }
    CloseHandle(process.hThread);
    CloseHandle(process.hProcess);
    return 0;
}
