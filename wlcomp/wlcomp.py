#!/usr/bin/python3

from bitstring import Bits, BitArray
from cffi import FFI

ffi = FFI()

ffi.cdef('''
struct LDevice;

struct LDevice* CreateLDevice(unsigned int Slot, unsigned int* err);
void ReleaseLDevice(struct LDevice* hIfc);

unsigned int PlataTest(struct LDevice* hIfc);

unsigned int OpenLDevice(struct LDevice* hIfc);
unsigned int CloseLDevice(struct LDevice* hIfc);

unsigned int InitStartLDevice(struct LDevice* hIfc);
unsigned int StartLDevice(struct LDevice* hIfc);
unsigned int StopLDevice(struct LDevice* hIfc);

unsigned int LoadBios(struct LDevice* hIfc, char *FileName);

typedef struct
{
   unsigned int s_Type;
   unsigned int FIFO;
   unsigned int IrqStep;
   unsigned int Pages;

   double dRate;
   unsigned int Rate;
   unsigned int NCh;
   unsigned int Chn[128];
   unsigned int Data[128];
   unsigned int Mode;
} WASYNC_PAR;

unsigned int IoAsync(struct LDevice* hIfc, WASYNC_PAR* sp);

typedef struct
{
   unsigned int Base;
   unsigned int BaseL;
   unsigned int Base1;
   unsigned int BaseL1;
   unsigned int Mem;
   unsigned int MemL;
   unsigned int Mem1;
   unsigned int MemL1;
   unsigned int Irq;
   unsigned int BoardType;
   unsigned int DSPType;
   unsigned int Dma;
   unsigned int DmaDac;
   unsigned int DTA_REG;
   unsigned int IDMA_REG;
   unsigned int CMD_REG;
   unsigned int IRQ_RST;
   unsigned int DTA_ARRAY;
   unsigned int RDY_REG;
   unsigned int CFG_REG;
} SLOT_PAR;

unsigned int GetSlotParam(struct LDevice* hIfc, SLOT_PAR* slPar);
unsigned int EnableCorrection(struct LDevice* hIfc, unsigned short Enabled);
''')

_dll = ffi.dlopen("libwlcomp.so")

#Коды ошибок
L_SUCCESS = 0
L_NOTSUPPORTED = 1
L_ERROR = 2
L_ERROR_NOBOARD = 3
L_ERROR_INUSE = 4

#Константы типа операции для IoAsync
L_ASYNC_ADC_CFG = 3
L_ASYNC_TTL_CFG = 4
L_ASYNC_DAC_CFG = 5

L_ASYNC_ADC_INP = 6
L_ASYNC_TTL_INP = 7

L_ASYNC_TTL_OUT = 8
L_ASYNC_DAC_OUT = 9


class LDeviceError(Exception):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return "LDeviceError: " + self.msg


class LDevice:
    #Обертка над C API
    def __init__(self, slot):
        err = ffi.new("unsigned int*")
        device = _dll.CreateLDevice(0, err)
        err = err[0]

        if err != L_SUCCESS:
            if err == 1:
                raise LDeviceError("CreateLDevice return L_NOTSUPPORTED")
            elif err == 2:
                raise LDeviceError("CreateLDevice return L_ERROR")
            elif err == 3:
                raise LDeviceError("CreateLDevice return L_ERROR_NOBOARD")
            elif err == 4:
                raise LDeviceError("CreateLDevice return L_ERROR_INUSE")
            else:
                raise AssertionError("Unknown error number {}".format(err))

        if _dll.OpenLDevice(device) == L_ERROR:
            _dll.ReleaseLDevice(device)
            raise LDeviceError("OpenLDevice error")

        self._impl = device

    def close(self):
        try:
            if _dll.CloseLDevice(self._impl) == L_ERROR:
                raise LDeviceError("CloseLDevice error")
        finally:
            _dll.ReleaseLDevice(self._impl)

    def plata_test(self):
        return _dll.PlataTest(self._impl) == L_SUCCESS

    def init_start(self):
        if _dll.InitStartLDevice(self._impl) == L_ERROR:
            raise LDeviceError("InitStartLDevice error")

    def start(self):
        if _dll.StartLDevice(self._impl) == L_ERROR:
            raise LDeviceError("StartLDevice error")

    def stop(self):
        if _dll.StopLDevice(self._impl) == L_ERROR:
            raise LDeviceError("StopLDevice error")

    def load_bios(self, filename):
        assert type(filename) == str
        filename = filename.encode("ascii")
        if _dll.LoadBios(self._impl, filename) == L_ERROR:
            raise LDeviceError("LoadBios error")

    def create_WASYNC_PAR(self):
        return ffi.new("WASYNC_PAR*")

    def io_async(self, WASYNC_PAR):
        if _dll.IoAsync(self._impl, WASYNC_PAR) == L_ERROR:
            raise LDeviceError("IoAsync error")

    def get_slot_param(self):
        sp = ffi.new("SLOT_PAR*")
        if _dll.GetSlotParam(self._impl, sp) == L_ERROR:
            raise LDeviceError("GetSlotParam error")
        return sp

    def enable_correction(self, val):
        assert type(val) == bool
        if _dll.EnableCorrection(self._impl, int(val)) == L_ERROR:
            raise LDeviceError("EnableCorrection error")

    #Пользовательские функции
    def ttl_write(self, bits):
        assert type(bits) in (Bits, BitArray)
        assert len(bits) == 16
        sp = self.create_WASYNC_PAR()
        sp.s_Type = L_ASYNC_TTL_OUT
        sp.Data[0] = bits.uint
        self.io_async(sp)

    def ttl_read(self):
        sp = self.create_WASYNC_PAR()
        sp.s_Type = L_ASYNC_TTL_INP
        self.io_async(sp)
        return Bits(uint=sp.Data[0], length=16)

    def adc_get(self, num):
        assert (num >= 0) and (num < 16)
        sp = self.create_WASYNC_PAR()
        sp.s_Type = L_ASYNC_ADC_INP
        sp.Chn[0] = num
        self.io_async(sp)

        value = Bits(uint=sp.Data[0], length=16)
        return value.int


def main():
    device = LDevice(0)

    try:
        print("PlataTest", device.plata_test())

        sp = device.get_slot_param()

        print("Base    ", sp.Base)
        print("BaseL   ", sp.BaseL)
        print("Mem     ", sp.Mem)
        print("MemL    ", sp.MemL)
        print("Type    ", sp.BoardType)
        print("DSPType ", sp.DSPType)
        print("Irq     ", sp.Irq)

        print(device.ttl_read().bin)
        print(device.ttl_read()[4])

        ttl = BitArray(uint=0, length=16)
        ttl[5] = 1
        device.ttl_write(ttl)

        device.enable_correction(True)
        print(device.adc_get(4))
    finally:
        device.close()

if __name__ == "__main__":
    main()
