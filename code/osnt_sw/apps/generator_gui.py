import os
from generator import *
import wx
import  wx.lib.scrolledpanel as scrolled
from axi import *

class MainWindow(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self, None, wx.ID_ANY, "OSNT Generator", size=(-1,-1))
        self.gui_init()

    def gui_init(self):

        self.SetMinSize(wx.Size(900,-1))

        # Pcap engine panel
        pcap_title = wx.StaticText(self, label="PCAP ENGINE", style=wx.ALIGN_CENTER)
        pcap_title.SetFont(wx.Font(15, wx.DECORATIVE, wx.NORMAL, wx.BOLD))
        pcap_title.SetBackgroundColour('GRAY')
        pcap_panel = wx.Panel(self)
        pcap_panel.SetBackgroundColour('WHEAT')
        pcap_sizer = wx.GridSizer(5, 5, 10, 10)
        pcap_panel.SetSizer(pcap_sizer)
        self.pcap_file_btn = [None]*4
        self.replay_cnt_input = [None]*4
        self.mem_addr_low_txt = [None]*4
        self.mem_addr_high_txt = [None]*4
        pcap_sizer.AddMany([(wx.StaticText(pcap_panel, label="Interface", style=wx.ALIGN_CENTER), 0, wx.EXPAND),
            (wx.StaticText(pcap_panel, label="Pcap File", style=wx.ALIGN_CENTER), 0, wx.EXPAND),
            (wx.StaticText(pcap_panel, label="Replay Cnt", style=wx.ALIGN_CENTER), 0, wx.EXPAND),
            (wx.StaticText(pcap_panel, label="Mem_addr_low", style=wx.ALIGN_CENTER), 0, wx.EXPAND),
            (wx.StaticText(pcap_panel, label="Mem_addr_high", style=wx.ALIGN_CENTER), 0, wx.EXPAND)])
        for i in range(4):
            self.pcap_file_btn[i] = wx.Button(pcap_panel, wx.ID_ANY, "Select Pcap File", style=wx.ALIGN_CENTER)
            self.replay_cnt_input[i] = wx.SpinCtrl(pcap_panel, value='0', min=0, style=wx.ALIGN_CENTER)
            self.mem_addr_low_txt[i] = wx.StaticText(pcap_panel, wx.ID_ANY, label='0', style=wx.ALIGN_CENTER)
            self.mem_addr_high_txt[i] = wx.StaticText(pcap_panel, wx.ID_ANY, label='0', style=wx.ALIGN_CENTER)
            pcap_sizer.AddMany([(wx.StaticText(pcap_panel, label=str(i), style=wx.ALIGN_CENTER), 0, wx.EXPAND),
                (self.pcap_file_btn[i], 0, wx.EXPAND),
                (self.replay_cnt_input[i], 0, wx.EXPAND),
                (self.mem_addr_low_txt[i], 0, wx.EXPAND),
                (self.mem_addr_high_txt[i], 0, wx.EXPAND)])

        # Rate Limiter panel
        rate_limiter_title = wx.StaticText(self, label="RATE LIMITER", style=wx.ALIGN_CENTER)
        rate_limiter_title.SetFont(wx.Font(15, wx.DECORATIVE, wx.NORMAL, wx.BOLD))
        rate_limiter_title.SetBackgroundColour('GRAY')
        rate_limiter_panel = wx.Panel(self)
        rate_limiter_panel.SetBackgroundColour('WHEAT')
        rate_limiter_sizer = wx.GridSizer(5, 5, 10, 10)
        rate_limiter_panel.SetSizer(rate_limiter_sizer)
        self.rate_input = [None]*4
        self.rate_txt = [None]*4
        self.rate_limiter_enable_toggle = [None]*4
        self.rate_limiter_reset_toggle = [None]*4
        rate_limiter_sizer.AddMany([(wx.StaticText(rate_limiter_panel, label="Interface", style=wx.ALIGN_CENTER), 0, wx.EXPAND),
            (wx.StaticText(rate_limiter_panel, label="Rate Input", style=wx.ALIGN_CENTER), 0, wx.EXPAND),
            (wx.StaticText(rate_limiter_panel, label="Rate Display", style=wx.ALIGN_CENTER), 0, wx.EXPAND),
            (wx.StaticText(rate_limiter_panel, label="Enable", style=wx.ALIGN_CENTER), 0, wx.EXPAND),
            (wx.StaticText(rate_limiter_panel, label="Reset", style=wx.ALIGN_CENTER), 0, wx.EXPAND)])
        for i in range(4):
            self.rate_input[i] = wx.SpinCtrl(rate_limiter_panel, value='0', min=0, style=wx.ALIGN_CENTER)
            self.rate_txt[i] = wx.StaticText(rate_limiter_panel, wx.ID_ANY, label='0', style=wx.ALIGN_CENTER)
            self.rate_limiter_enable_toggle[i] = wx.ToggleButton(rate_limiter_panel, wx.ID_ANY, label="Enable", style=wx.ALIGN_CENTER)
            self.rate_limiter_reset_toggle[i] = wx.ToggleButton(rate_limiter_panel, wx.ID_ANY, label="Reset", style=wx.ALIGN_CENTER)
            rate_limiter_sizer.AddMany([(wx.StaticText(rate_limiter_panel, label=str(i), style=wx.ALIGN_CENTER), 0, wx.EXPAND),
                (self.rate_input[i], 0, wx.EXPAND),
                (self.rate_txt[i], 0, wx.EXPAND),
                (self.rate_limiter_enable_toggle[i], 0, wx.EXPAND),
                (self.rate_limiter_reset_toggle[i], 0, wx.EXPAND)])

        # Delay panel
        delay_title = wx.StaticText(self, label="INTER PACKET DELAY", style=wx.ALIGN_CENTER)
        delay_title.SetFont(wx.Font(15, wx.DECORATIVE, wx.NORMAL, wx.BOLD))
        delay_title.SetBackgroundColour('GRAY')
        delay_panel = wx.Panel(self)
        delay_panel.SetBackgroundColour('WHEAT')
        delay_sizer = wx.GridSizer(5, 6, 10, 10)
        delay_panel.SetSizer(delay_sizer)
        self.use_reg_toggle = [None]*4
        self.delay_input = [None]*4
        self.delay_txt = [None]*4
        self.delay_enable_toggle = [None]*4
        self.delay_reset_toggle = [None]*4
        delay_sizer.AddMany([(wx.StaticText(delay_panel, label="Interface", style=wx.ALIGN_CENTER), 0, wx.EXPAND),
            (wx.StaticText(delay_panel, label="Use Reg Value", style=wx.ALIGN_CENTER), 0, wx.EXPAND),
            (wx.StaticText(delay_panel, label="Delay Input", style=wx.ALIGN_CENTER), 0, wx.EXPAND),
            (wx.StaticText(delay_panel, label="Delay Display", style=wx.ALIGN_CENTER), 0, wx.EXPAND),
            (wx.StaticText(delay_panel, label="Enable", style=wx.ALIGN_CENTER), 0, wx.EXPAND),
            (wx.StaticText(delay_panel, label="Reset", style=wx.ALIGN_CENTER), 0, wx.EXPAND)])
        for i in range(4):
            self.use_reg_toggle[i] = wx.ToggleButton(delay_panel, wx.ID_ANY, label="Use Reg", style=wx.ALIGN_CENTER)
            self.delay_input[i] = wx.SpinCtrl(delay_panel, value='0', min=0, style=wx.ALIGN_CENTER)
            self.delay_txt[i] = wx.StaticText(delay_panel, wx.ID_ANY, label='0', style=wx.ALIGN_CENTER)
            self.delay_enable_toggle[i] = wx.ToggleButton(delay_panel, wx.ID_ANY, label="Enable", style=wx.ALIGN_CENTER)
            self.delay_reset_toggle[i] = wx.ToggleButton(delay_panel, wx.ID_ANY, label="Reset", style=wx.ALIGN_CENTER)
            delay_sizer.AddMany([(wx.StaticText(delay_panel, label=str(i), style=wx.ALIGN_CENTER), 0, wx.EXPAND),
                (self.use_reg_toggle[i], 0, wx.EXPAND),
                (self.delay_input[i], 0, wx.EXPAND),
                (self.delay_txt[i], 0, wx.EXPAND),
                (self.delay_enable_toggle[i], 0, wx.EXPAND),
                (self.delay_reset_toggle[i], 0, wx.EXPAND)])


        # Logger
        logger_title = wx.StaticText(self, label="LOGGER", style=wx.ALIGN_CENTER)
        logger_title.SetFont(wx.Font(15, wx.DECORATIVE, wx.NORMAL, wx.BOLD))
        logger_title.SetBackgroundColour('GRAY')
        self.logger = wx.TextCtrl(self, style=wx.TE_MULTILINE|wx.TE_READONLY)

        # Setting up the menu.
        console_menu = wx.Menu()
        config_filter_menu = console_menu.Append(wx.ID_ANY, "Start Replay", "Start Replay")
   
        # Creating the menubar.
        menuBar = wx.MenuBar()
        menuBar.Append(console_menu, "&Console")
        self.SetMenuBar(menuBar)  # Adding the MenuBar to the Frame content.
   
        # Use some sizers to see layout options
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(pcap_title, 0.5, wx.EXPAND)
        self.sizer.Add(pcap_panel, 4, wx.EXPAND)
        self.sizer.Add(rate_limiter_title, 0.5, wx.EXPAND)
        self.sizer.Add(rate_limiter_panel, 4, wx.EXPAND)
        self.sizer.Add(delay_title, 0.5, wx.EXPAND)
        self.sizer.Add(delay_panel, 4, wx.EXPAND)
        self.sizer.Add(logger_title, 0.5, wx.EXPAND)
        self.sizer.Add(self.logger, 2, wx.EXPAND)
   
        #Layout sizers
        self.SetSizer(self.sizer)
        self.SetAutoLayout(1)
        self.sizer.Fit(self)
        self.Show()


app = wx.App(False)
frame = MainWindow()
app.MainLoop()

