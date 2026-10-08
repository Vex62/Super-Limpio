/*
 * Super Limpio - lanzador nativo (SuperLimpio.exe)
 *
 * Hace una sola cosa: cargar el intérprete oficial de Python que hay en
 * runtime\python (python3xx.dll, firmado por la Python Software Foundation)
 * y pedirle que ejecute app\main.py. Es lo mismo que hace pythonw.exe, pero
 * sabiendo dónde está la aplicación, para que baste con un doble clic.
 *
 * Lo que NO hace, a propósito (es lo que dispara los antivirus):
 *   - no lleva nada empaquetado ni comprimido dentro, ni extrae archivos
 *   - no escribe en disco, ni en el registro, ni usa la red
 *   - no lanza otros procesos ni toca la memoria de ninguno
 *   - no usa empaquetadores (UPX, etc.) ni ofuscación
 *
 * Solo usa 13 funciones de Windows (kernel32, user32 y shell32), declaradas
 * aquí abajo. No depende del SDK de Windows ni de la biblioteca de C: se
 * compila con tools\crear_exe.py.
 */

typedef unsigned short WCHAR;
typedef unsigned long DWORD;
typedef unsigned long long SIZE_T;
typedef void *HANDLE;

#define IMPORT __declspec(dllimport)
#define INVALID_HANDLE ((HANDLE)(long long)-1)
#define INVALID_ATTRIBUTES ((DWORD)-1)
#define LOAD_WITH_ALTERED_SEARCH_PATH 0x00000008
#define MB_ICONERROR 0x00000010
#define MAX_LONG_PATH 32768

typedef struct {
    DWORD dwFileAttributes;
    DWORD ftCreationTime[2];
    DWORD ftLastAccessTime[2];
    DWORD ftLastWriteTime[2];
    DWORD nFileSizeHigh;
    DWORD nFileSizeLow;
    DWORD dwReserved0;
    DWORD dwReserved1;
    WCHAR cFileName[260];
    WCHAR cAlternateFileName[14];
} FIND_DATA;

IMPORT DWORD GetModuleFileNameW(HANDLE module, WCHAR *buffer, DWORD size);
IMPORT DWORD GetFileAttributesW(const WCHAR *path);
IMPORT HANDLE FindFirstFileW(const WCHAR *pattern, FIND_DATA *data);
IMPORT int FindNextFileW(HANDLE find, FIND_DATA *data);
IMPORT int FindClose(HANDLE find);
IMPORT HANDLE LoadLibraryExW(const WCHAR *path, HANDLE file, DWORD flags);
IMPORT void *GetProcAddress(HANDLE module, const char *name);
IMPORT WCHAR *GetCommandLineW(void);
IMPORT HANDLE GetProcessHeap(void);
IMPORT void *HeapAlloc(HANDLE heap, DWORD flags, SIZE_T bytes);
IMPORT void ExitProcess(unsigned int code);
IMPORT int MessageBoxW(HANDLE owner, const WCHAR *text, const WCHAR *caption, unsigned int type);
IMPORT WCHAR **CommandLineToArgvW(const WCHAR *command_line, int *argc);

typedef int (*PY_MAIN)(int argc, WCHAR **argv);

static WCHAR g_root[MAX_LONG_PATH];    /* carpeta del .exe, acabada en \ */
static WCHAR g_dll[MAX_LONG_PATH];     /* runtime\python\python3xx.dll   */
static WCHAR g_script[MAX_LONG_PATH];  /* app\main.py                    */

static void fail(const WCHAR *text)
{
    MessageBoxW(0, text, L"Super Limpio", MB_ICONERROR);
    ExitProcess(1);
}

/* Copia src en dst sin pasarse de end; devuelve dónde quedó el terminador. */
static WCHAR *append(WCHAR *dst, const WCHAR *end, const WCHAR *src)
{
    while (*src) {
        if (dst + 1 >= end)
            fail(L"La ruta de la aplicación es demasiado larga.");
        *dst++ = *src++;
    }
    *dst = 0;
    return dst;
}

/* Busca python3xx.dll (no python3.dll) para no atarse a una versión concreta. */
static int find_python_dll(void)
{
    const WCHAR *end = g_dll + MAX_LONG_PATH;
    WCHAR *name = append(append(g_dll, end, g_root), end, L"runtime\\python\\");
    FIND_DATA data;
    HANDLE find;
    int found = 0;

    append(name, end, L"python3*.dll");
    find = FindFirstFileW(g_dll, &data);
    if (find == INVALID_HANDLE)
        return 0;
    do {
        if (data.cFileName[7] != L'.') {
            append(name, end, data.cFileName);
            found = 1;
            break;
        }
    } while (FindNextFileW(find, &data));
    FindClose(find);
    return found;
}

void entry(void)
{
    DWORD len = GetModuleFileNameW(0, g_root, MAX_LONG_PATH);
    WCHAR *cut = g_root + len;
    HANDLE python;
    PY_MAIN py_main;
    WCHAR **args, **argv;
    int argc = 0, i;

    if (len == 0 || len >= MAX_LONG_PATH)
        fail(L"No se pudo averiguar la carpeta de la aplicación.");
    while (cut > g_root && cut[-1] != L'\\')
        cut--;
    *cut = 0;

    append(append(g_script, g_script + MAX_LONG_PATH, g_root), g_script + MAX_LONG_PATH, L"app\\main.py");
    if (GetFileAttributesW(g_script) == INVALID_ATTRIBUTES)
        fail(L"Falta la carpeta «app».\n\n"
             L"SuperLimpio.exe tiene que estar junto a las carpetas «app» y «runtime»: "
             L"descomprime el zip entero y no muevas el .exe fuera de su carpeta.");
    if (!find_python_dll())
        fail(L"Falta el Python portable en «runtime\\python».\n\n"
             L"SuperLimpio.exe tiene que estar junto a las carpetas «app» y «runtime»: "
             L"descomprime el zip entero y no muevas el .exe fuera de su carpeta.");

    /* Ruta completa + ALTERED_SEARCH_PATH: sus dependencias (vcruntime140.dll)
       se buscan junto a la propia DLL y no en la carpeta actual ni en el PATH. */
    python = LoadLibraryExW(g_dll, 0, LOAD_WITH_ALTERED_SEARCH_PATH);
    py_main = python ? (PY_MAIN)GetProcAddress(python, "Py_Main") : 0;
    if (!py_main)
        fail(L"No se pudo cargar el Python portable de «runtime\\python».\n\n"
             L"Vuelve a descomprimir el zip, o ejecuta preparar_entorno.bat.");

    args = CommandLineToArgvW(GetCommandLineW(), &argc);
    argv = args ? (WCHAR **)HeapAlloc(GetProcessHeap(), 0, sizeof(WCHAR *) * ((SIZE_T)argc + 3)) : 0;
    if (!argv || argc < 1)
        fail(L"No hay memoria suficiente para abrir la aplicación.");

    /* SuperLimpio.exe -I app\main.py [argumentos del usuario]
       -I = modo aislado: ignora PYTHONPATH/PYTHONHOME y los paquetes del usuario,
       así la app se comporta igual en cualquier equipo. */
    argv[0] = args[0];
    argv[1] = L"-I";
    argv[2] = g_script;
    for (i = 1; i < argc; i++)
        argv[i + 2] = args[i];
    argv[argc + 2] = 0;

    ExitProcess((unsigned int)py_main(argc + 2, argv));
}
