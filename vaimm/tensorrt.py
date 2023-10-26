from dataclasses import dataclass
import ctypes
import platform

GPU_TRT_MAP = {
    'RTX20': 705,
    'RTX30': 806,
    'RTX40': 809,
}
OS_TRT_MAP = {
    'Windows': 8500,
    'Linux': 8517,
}


@dataclass
class TRT:
    os_family: int
    gpu_family: int


def find_tensorrt_engine(card_family) -> TRT:
    card_family = GPU_TRT_MAP.get(card_family)
    if not card_family:
        return
    platform_code = OS_TRT_MAP.get(platform.system())
    if not platform_code:
        return
    return TRT(platform_code, card_family)


def find_graphics_card_family() -> str:
    card = find_graphics_card()
    if 'RTX 20' in card:
        return 'RTX20'
    if 'RTX 30' in card:
        return 'RTX30'
    if 'RTX 40' in card:
        return 'RTX40'
    return ''


def find_graphics_card() -> str:
    # only works on windows, on other platforms users have to specify TRT details themselves
    if not platform.system() == 'Windows':
        return ''

    D3D_SDK_VERSION = 32
    D3DADAPTER_DEFAULT = 0
    HRESULT = ctypes.c_long

    # https://learn.microsoft.com/en-us/windows/win32/api/guiddef/ns-guiddef-guid
    class GUID(ctypes.Structure):
        _fields_ = [
            ('Data1', ctypes.c_ulong),
            ('Data2', ctypes.c_ushort),
            ('Data3', ctypes.c_ushort),
            ('Data4', ctypes.c_ubyte * 8)
        ]

    # https://learn.microsoft.com/en-us/windows/win32/direct3d9/d3dadapter-identifier9
    class D3DADAPTER_IDENTIFIER9(ctypes.Structure):
        _fields_ = [
            ('Driver', ctypes.c_char * 512),
            ('Description', ctypes.c_char * 512),
            ('DeviceName', ctypes.c_char * 32),
            ('DriverVersion', ctypes.c_longlong),  # LARGE_INTEGER
            ('VendorId', ctypes.c_uint),
            ('DeviceId', ctypes.c_uint),
            ('SubSysId', ctypes.c_uint),
            ('Revision', ctypes.c_uint),
            ('DeviceIdentifier', GUID),
            ('WHQLLevel', ctypes.c_uint),
        ]

    d3d9 = ctypes.windll.d3d9

    # need a COM object so we can fake "this" in the win API
    # https://learn.microsoft.com/en-us/windows/win32/api/d3d9/nf-d3d9-direct3dcreate9
    Direct3DCreate9 = d3d9.Direct3DCreate9
    Direct3DCreate9.argtypes = [ctypes.c_uint]
    Direct3DCreate9.restype = ctypes.c_void_p
    d3d9_obj = Direct3DCreate9(D3D_SDK_VERSION)

    # GetAdapterIdentifier function prototype
    # https://learn.microsoft.com/en-us/windows/win32/api/d3d9/nf-d3d9-idirect3d9-getadapteridentifier
    GetAdapterIdentifierProto = ctypes.CFUNCTYPE(
        HRESULT,                                # return type
        ctypes.c_void_p,                        # this
        ctypes.c_uint,                          # adapter
        ctypes.c_uint,                          # flags
        ctypes.POINTER(D3DADAPTER_IDENTIFIER9)  # pIdentifier
    )

    # derive vtable from the COM object
    vtable_ptr = ctypes.c_void_p.from_address(d3d9_obj).value
    vtable_offset = 5  # for GetAdapterIdentifier
    func_ptr = ctypes.c_void_p.from_address(vtable_ptr + vtable_offset * ctypes.sizeof(ctypes.c_void_p)).value
    GetAdapterIdentifier = GetAdapterIdentifierProto(func_ptr)

    identifier = D3DADAPTER_IDENTIFIER9()

    # finally, get the gpu info
    result = GetAdapterIdentifier(d3d9_obj, D3DADAPTER_DEFAULT, 0, ctypes.byref(identifier))

    if result:
        print('WARNING: Failed to automatically find graphics card type (GetAdapterIdentifier HRESULT: '
              f'{result}), you will have to specify which card you use manually if you are going to download'
              'TensorRT models.')
        return ''
    return identifier.Description.decode('utf-8')
