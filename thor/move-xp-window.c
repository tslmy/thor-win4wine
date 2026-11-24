/* Diagnostic: move only an Explorer folder window, using public Win32 APIs. */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <wchar.h>

int main(int argc, char **argv)
{
    HWND window;
    WCHAR kind[64];
    RECT rect;
    if (argc != 6) return 2;
    SetProcessDPIAware();
    window = (HWND)(UINT_PTR)strtoul(argv[1], NULL, 16);
    if (!IsWindow(window) || !GetClassNameW(window, kind, 64)) return 3;
    if (wcscmp(kind, L"CabinetWClass") && wcscmp(kind, L"ExploreWClass")) return 4;
    ShowWindow(window, SW_RESTORE);
    if (!SetWindowPos(window, HWND_TOP, atoi(argv[2]), atoi(argv[3]), atoi(argv[4]), atoi(argv[5]),
                      SWP_SHOWWINDOW)) return 5;
    SetForegroundWindow(window);
    GetWindowRect(window, &rect);
    printf("Folder window: %ld,%ld..%ld,%ld\n", rect.left, rect.top, rect.right, rect.bottom);
    return 0;
}
