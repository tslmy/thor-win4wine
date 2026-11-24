/* Refresh only Explorer folder non-client frames after theme metrics change. */
#define _WIN32_WINNT 0x0a00
#include <windows.h>
#include <stdio.h>
#include <wchar.h>

static BOOL CALLBACK refresh(HWND window, LPARAM unused)
{
    WCHAR kind[64];
    RECT outer, client;
    (void)unused;
    if (!IsWindowVisible(window) || !GetClassNameW(window, kind, 64)) return TRUE;
    if (wcscmp(kind, L"CabinetWClass") && wcscmp(kind, L"ExploreWClass")) return TRUE;
    printf("Explorer window %p DPI=%u\n", (void *)window, GetDpiForWindow(window));
    SetWindowPos(window, NULL, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED);
    RedrawWindow(window, NULL, NULL, RDW_INVALIDATE | RDW_FRAME | RDW_ALLCHILDREN | RDW_UPDATENOW);
    GetWindowRect(window, &outer);
    GetClientRect(window, &client);
    printf("Outer=%ldx%ld client=%ldx%ld\n", outer.right-outer.left, outer.bottom-outer.top, client.right, client.bottom);
    return TRUE;
}

int main(void)
{
    NONCLIENTMETRICSW metrics = {0};
    LOGFONTW icon;
    DWORD_PTR ignored;
    SetProcessDPIAware();
    metrics.cbSize = sizeof(metrics);
    if (SystemParametersInfoW(SPI_GETNONCLIENTMETRICS, sizeof(metrics), &metrics, 0))
        SystemParametersInfoW(SPI_SETNONCLIENTMETRICS, sizeof(metrics), &metrics, SPIF_UPDATEINIFILE | SPIF_SENDCHANGE);
    if (SystemParametersInfoW(SPI_GETICONTITLELOGFONT, sizeof(icon), &icon, 0))
        SystemParametersInfoW(SPI_SETICONTITLELOGFONT, sizeof(icon), &icon, SPIF_UPDATEINIFILE | SPIF_SENDCHANGE);
    SendMessageTimeoutW(HWND_BROADCAST, WM_SETTINGCHANGE, SPI_SETNONCLIENTMETRICS,
                        (LPARAM)L"WindowMetrics", SMTO_ABORTIFHUNG, 2000, &ignored);
    SendMessageTimeoutW(HWND_BROADCAST, WM_THEMECHANGED, 0, 0, SMTO_ABORTIFHUNG, 2000, &ignored);
    EnumWindows(refresh, 0);
    return 0;
}
