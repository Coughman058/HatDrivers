# -*- coding: utf-8 -*-
"""
Created on Wed Jun 24 18:12:24 2020

@author: Hatlab_3
"""
import ctypes
import types
import logging
import types
import logging
import numpy as np
import time
from qcodes import (Instrument, VisaInstrument,
                    ManualParameter, MultiParameter,
                    validators as vals)

sn = ctypes.c_char_p(b'10000E9D') # Signal core 1
debug = True

class SignalCore_sc5511a(Instrument):
    
    def __init__(self, name, dll = None, serial_number=sn):
        # logging.info(__name__ + ' : Initializing instrument SignalCore generator')
        super().__init__(name)
        
        # I tried to open the dll file in the create_instruments file to shre the same dll
        # file, but that did not seem to fix the problem
        if dll is not None:
            self._dll = dll
        else:
            self._dll = ctypes.CDLL('DLL//sc5511a.dll')  #Original Line to access dll file          
        if debug:
            print(self._dll)
        self._handle = self._dll.sc5511a_open_device(ctypes.c_char_p(serial_number))
        self._serial_number = ctypes.c_char_p(serial_number)
        self._rf_params = Device_rf_params_t(0,0,0,0,0,0,0,0,0)        
        self._status = Operate_status_t(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0)
        self._open = False
        self._temperature = Device_temperature_t(0)        
        
        self._pll_status = Pll_status_t()
        self._list_mode = List_mode_t()
        self._device_status = Device_status_t(self._list_mode, self._status, self._pll_status)
        if debug:
            print(serial_number, self._handle)
        self._dll.sc5511a_close_device(self._handle)  
        
        self.add_parameter('output_status', 
                           get_cmd = self.do_get_output_status,
                           set_cmd = self.do_set_output_status, 
                           vals = vals.Ints(0,1),
                           get_parser = int
                           )
        self.add_parameter('frequency',
                           get_cmd = self.do_get_frequency,
                           set_cmd = self.do_set_frequency,
                           vals = vals.Numbers(100e6, 20e9),
                           unit = 'Hz'
                           )
        self.add_parameter('reference_source', 
                           get_cmd = self.do_get_reference_source, 
                           set_cmd = self.do_set_reference_source, 
                           vals = vals.Ints(0,1), 
                           get_parser = int
                           )
        self.add_parameter('alc_auto', 
                           get_cmd = self.do_get_alc_auto, 
                           set_cmd = self.do_set_alc_auto, 
                           vals = vals.Ints(0,1), 
                           get_parser = int
                           )
        self.add_parameter('power',
                           get_cmd = self.do_get_power, 
                           set_cmd = self.do_set_power, 
                           vals = vals.Numbers(-30,20),
                           unit = ' dBm')
        
        self.add_parameter('device_temp', 
                           get_parser = float, 
                           get_cmd = self.do_get_device_temp, 
                           unit = 'C')
    		
        
        if self._device_status.operate_status_t.ext_ref_lock_enable == 0:
            self.do_set_reference_source(1)
    
        self.get_all()
        
    def set_open(self, open):
            if open and not self._open:
                self._handle = self._dll.sc5511a_open_device(self._serial_number)
                self._open = True
            if not open and self._open:
                self._dll.sc5511a_close_device(self._handle)
                self._open = False
            return 1
                      
    def do_set_output_status(self, enable):
        """
        Turns the output of RF1 on or off.
            Input: 
                enable (int) = OFF = 0 ; ON = 1
        """
        logging.info(__name__ + ' : Setting output to %s' % enable)
        c_enable = ctypes.c_ubyte(enable)
        self._handle = self._dll.sc5511a_open_device(self._serial_number)
        completed = self._dll.sc5511a_set_output(self._handle, c_enable)
        self._dll.sc5511a_close_device(self._handle)
        return completed
    
    def do_get_output_status(self):
        '''
        Reads the output status of RF1
            Output:
                status (int) : OFF = 0 ; ON = 1
        '''
        logging.info(__name__ + ' : Getting output')
        self._handle = self._dll.sc5511a_open_device(self._serial_number)
        self._dll.sc5511a_get_device_status(self._handle, ctypes.byref(self._device_status))
        status = self._device_status.operate_status_t.rf1_out_enable
        self._dll.sc5511a_close_device(self._handle)
        return status
                    
    def do_set_frequency(self, frequency):
        """
        Sets RF1 frequency. Valid between 100MHz and 20GHz
            Args:
                frequency (int) = frequency in Hz
        """
        c_freq = ctypes.c_ulonglong(frequency)
        logging.info(__name__ + ' : Setting frequency to %s' % frequency)
        close = False
        if not self._open:
            self._handle = self._dll.sc5511a_open_device(self._serial_number)
            close = True
        if_set = self._dll.sc5511a_set_freq(self._handle, c_freq)
        if close:
            self._dll.sc5511a_close_device(self._handle)
        return if_set
        
    def do_get_frequency(self):
        logging.info(__name__ + ' : Getting frequency')
        self._handle = self._dll.sc5511a_open_device(self._serial_number)
        self._dll.sc5511a_get_rf_parameters(self._handle, ctypes.byref(self._rf_params))
        frequency = self._rf_params.rf1_freq
        self._dll.sc5511a_close_device(self._handle)
        return frequency
    
    def do_set_reference_source(self, lock_to_external):
        logging.info(__name__ + ' : Setting reference source to %s' % lock_to_external)
        high = ctypes.c_ubyte(0)
        lock = ctypes.c_ubyte(lock_to_external)
        self._handle = self._dll.sc5511a_open_device(self._serial_number)
        source = self._dll.sc5511a_set_clock_reference(self._handle, high, lock)
        self._dll.sc5511a_close_device(self._handle)
        return source
    
    def do_get_reference_source(self):
        logging.info(__name__ + ' : Getting reference source')
        self._handle = self._dll.sc5511a_open_device(self._serial_number)
        enabled =  self._device_status.operate_status_t.ext_ref_lock_enable
        self._dll.sc5511a_close_device(self._handle)
        return enabled
        
    def do_set_alc_auto(self, enable):
        logging.info(__name__ + ' : Settingalc auto to %s' % enable)
        if enable == 1:
            enable = 0
        elif enable == 0:
            enable = 1
        c_enable = ctypes.c_ubyte(enable)
        self._handle = self._dll.sc5511a_open_device(self._serial_number)
        completed =  self._dll.sc5511a_set_auto_level_disable(self._handle, c_enable)
        self._dll.sc5511a_close_device(self._handle)
        return completed
        
    def do_get_alc_auto(self):
        logging.info(__name__ + ' : Getting alc auto status')
        self._handle = self._dll.sc5511a_open_device(self._serial_number)
        self._dll.sc5511a_get_device_status(self._handle, ctypes.byref(self._device_status))
        enabled =  self._device_status.operate_status_t.auto_pwr_disable
        self._dll.sc5511a_close_device(self._handle)
        if enabled == 1:
            enabled = 0
        elif enabled == 0:
            enabled = 1
        return enabled
    
    def close(self):
        self.set_open(0)
    
    def do_set_power(self, power):
        logging.info(__name__ + ' : Setting power to %s' % power)
        c_power = ctypes.c_float(power)
        close = False
        if not self._open:
            self._handle = self._dll.sc5511a_open_device(self._serial_number)
            close = True
        completed = self._dll.sc5511a_set_level(self._handle, c_power)
        if close:
            self._dll.sc5511a_close_device(self._handle)
        return completed
    
    def do_get_power(self):
        logging.info(__name__ + ' : Getting Power')
        self._handle = self._dll.sc5511a_open_device(self._serial_number)
        self._dll.sc5511a_get_rf_parameters(self._handle, ctypes.byref(self._rf_params))
        rf_level = self._rf_params.rf_level
        self._dll.sc5511a_close_device(self._handle)
        return rf_level
        
    def do_get_device_temp(self):
        logging.info(__name__ + " : Getting device temperature")
        self._handle = self._dll.sc5511a_open_device(self._serial_number)        
        self._dll.sc5511a_get_temperature(self._handle, ctypes.byref(self._temperature))
        device_temp = self._temperature.device_temp
        self._dll.sc5511a_close_device(self._handle)
        return device_temp

    
    def get_all(self):
        self.output_status()
        self.frequency()
        self.reference_source()
        self.alc_auto()
        self.power()
# Structures to communicate with device----------------------------------------
class Device_rf_params_t(ctypes.Structure):
	_fields_ = [("rf1_freq", ctypes.c_ulonglong),
				("start_freq", ctypes.c_ulonglong),
				("stop_freq", ctypes.c_ulonglong),
				("step_freq", ctypes.c_ulonglong),
				("sweep_dwell_time", ctypes.c_uint),
				("sweep_cycles", ctypes.c_uint),
				("buffer_time", ctypes.c_uint),
				("rf_level", ctypes.c_float),
				("rf2_freq", ctypes.c_short)
				]

class Device_temperature_t(ctypes.Structure):
    _fields_ = [("device_temp", ctypes.c_float)]

				
class Operate_status_t(ctypes.Structure):
	_fields_ = [("rf1_lock_mode", ctypes.c_ubyte),
				("rf1_loop_gain", ctypes.c_ubyte),
				("device_access", ctypes.c_ubyte),
				("rf2_standby", ctypes.c_ubyte),
				("rf1_standby", ctypes.c_ubyte),
				("auto_pwr_disable", ctypes.c_ubyte),
				("alc_mode", ctypes.c_ubyte),
				("rf1_out_enable", ctypes.c_ubyte),
				("ext_ref_lock_enable", ctypes.c_ubyte),
				("ext_ref_detect", ctypes.c_ubyte),
				("ref_out_select", ctypes.c_ubyte),
				("list_mode_running", ctypes.c_ubyte),
				("rf1_mode", ctypes.c_ubyte),
				("harmonic_ss", ctypes.c_ubyte),
				("over_temp", ctypes.c_ubyte)
				]

class Pll_status_t(ctypes.Structure):
    _fields_ = [("sum_pll_ld",ctypes.c_ubyte),
                ("crs_pll_ld",ctypes.c_ubyte),
                ("fine_pll_ld",ctypes.c_ubyte),
                ("crs_ref_pll_ld",ctypes.c_ubyte),
                ("crs_aux_pll_ld",ctypes.c_ubyte),
                ("ref_100_pll_ld",ctypes.c_ubyte),
                ("ref_10_pll_ld",ctypes.c_ubyte),
                ("rf2_pll_ld",ctypes.c_ubyte)]
                
class List_mode_t(ctypes.Structure):
    _fields_ = [("sss_mode",ctypes.c_ubyte),
                ("sweep_dir",ctypes.c_ubyte),
                ("tri_waveform",ctypes.c_ubyte),
                ("hw_trigger",ctypes.c_ubyte),
                ("step_on_hw_trig",ctypes.c_ubyte),
                ("return_to_start",ctypes.c_ubyte),
                ("trig_out_enable",ctypes.c_ubyte),
                ("trig_out_on_cycle",ctypes.c_ubyte)]
                
class Device_status_t(ctypes.Structure):
    _fields_ = [("list_mode", List_mode_t),
                ("operate_status_t", Operate_status_t),
                ("pll_status_t", Pll_status_t)]