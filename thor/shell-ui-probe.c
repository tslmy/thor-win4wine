/* Public API diagnostics; theme assets are not embedded or redistributed. */
#define _WIN32_WINNT 0x0601
#include <windows.h>
#include <uxtheme.h>
#include <dwmapi.h>
#include <stdio.h>
#include <stdlib.h>

int main(int argc, char **argv)
{
    HDC dc;
    WCHAR file[MAX_PATH] = {0}, color[64] = {0}, size[64] = {0};
    BOOL composition = FALSE;
    HWND window;
    DWM_BLURBEHIND blur = {0};
    HTHUMBNAIL thumbnail = NULL;
    int dpi;
    if (argc != 2) return 2;
    SetProcessDPIAware();
    dc = GetDC(NULL);
    dpi = GetDeviceCaps(dc, LOGPIXELSX);
    ReleaseDC(NULL, dc);
    printf("system-dpi=%d theme-active=%d\n", dpi, IsThemeActive());
    if (FAILED(GetCurrentThemeName(file, MAX_PATH, color, 64, size, 64))) return 3;
    wprintf(L"theme=%ls color=%ls size=%ls\n", file, color, size);
    DwmIsCompositionEnabled(&composition);
    printf("dwm-composition=%d (generic probe only; not proof of Aero glass)\n", composition);
    window = CreateWindowExW(0, L"STATIC", L"DWM API probe", WS_OVERLAPPEDWINDOW,
                            0, 0, 100, 100, NULL, NULL, GetModuleHandleW(NULL), NULL);
    if (!window) return 5;
    blur.dwFlags = DWM_BB_ENABLE;
    blur.fEnable = TRUE;
    printf("dwm-blur-hresult=0x%08lx\n", (unsigned long)DwmEnableBlurBehindWindow(window, &blur));
    printf("dwm-thumbnail-hresult=0x%08lx\n", (unsigned long)DwmRegisterThumbnail(window, GetDesktopWindow(), &thumbnail));
    if (thumbnail) DwmUnregisterThumbnail(thumbnail);
    DestroyWindow(window);
    if (dpi != atoi(argv[1]) || !IsThemeActive()) return 4;
    return 0;
}
