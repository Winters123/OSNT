/*******************************************************************************
 *
 *  NetFPGA-10G http://www.netfpga.org
 *
 *  File:
 *        axis_to_fifo.v
 *
 *  Library:
 *        hw/contrib/pcores/nf10_pcap_replay_uengine_v1_00_a
 *
 *  Module:
 *        axis_to_fifo
 *
 *  Author:
 *        Muhammad Shahbaz
 *
 *  Description:
 *
 *
 *  Copyright notice:
 *        Copyright (C) 2010, 2011 The Board of Trustees of The Leland Stanford
 *                                 Junior University
 *
 *  Licence:
 *        This file is part of the NetFPGA 10G development base package.
 *
 *        This file is free code: you can redistribute it and/or modify it under
 *        the terms of the GNU Lesser General Public License version 2.1 as
 *        published by the Free Software Foundation.
 *
 *        This package is distributed in the hope that it will be useful, but
 *        WITHOUT ANY WARRANTY; without even the implied warranty of
 *        MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 *        Lesser General Public License for more details.
 *
 *        You should have received a copy of the GNU Lesser General Public
 *        License along with the NetFPGA source package.  If not, see
 *        http://www.gnu.org/licenses/.
 *
 */

module axis_to_fifo
#(
    //Master AXI Stream Data Width
    parameter C_S_AXIS_DATA_WIDTH  = 256,
    parameter C_S_AXIS_TUSER_WIDTH = 128,
    parameter FIFO_DATA_WIDTH      = 72
)
(
    // Global Ports
    input                                           axi_aclk,
    input                                           rst,
    input                                           fifo_clk,

    // AXI Stream Ports
    input [C_S_AXIS_DATA_WIDTH-1:0]                 s_axis_tdata,
    input [(C_S_AXIS_DATA_WIDTH/8)-1:0]             s_axis_tstrb,
    input [C_S_AXIS_TUSER_WIDTH-1:0]                s_axis_tuser,
    input                                           s_axis_tvalid,
    output reg                                      s_axis_tready,
    input                                           s_axis_tlast,

    // FIFO Ports
    input                                           fifo_rd_en,
    output [FIFO_DATA_WIDTH-1:0]                    fifo_dout,
    output                                          fifo_empty,

    // Misc
    input                                           sw_rst
);

  // -- Local Functions
  function integer log2;
    input integer number;
    begin
       log2=0;
       while(2**log2<number) begin
          log2=log2+1;
       end
    end
  endfunction

  // -- Internal Parameters
  localparam WR_TUSER_BITS = 0;
  localparam WR_PKT_BITS   = 1;
	
	localparam C_S_AXIS_PACKED_DATA_WIDTH = C_S_AXIS_DATA_WIDTH+C_S_AXIS_DATA_WIDTH/8; 

  // -- Signals
	genvar																		i;
	
  reg                                       state;
  reg                                       next_state;

  reg                                       ififo_rd_en;
  reg                                       ififo_wr_en;
  wire                                      ififo_nearly_full;
  wire                                      ififo_empty;
  wire  [C_S_AXIS_DATA_WIDTH-1:0]           ififo_tdata;
  wire  [C_S_AXIS_TUSER_WIDTH-1:0]          ififo_tuser;
  wire  [C_S_AXIS_DATA_WIDTH/8-1:0]         ififo_tstrb;
  wire                                      ififo_tlast;

  reg                                       fifo_wr_en;
  reg   [C_S_AXIS_DATA_WIDTH-1:0]           fifo_din;
  reg   [C_S_AXIS_DATA_WIDTH/8-1:0]         fifo_din_strb;
  wire                                      fifo_full;
	wire  [C_S_AXIS_PACKED_DATA_WIDTH-1:0]    fifo_din_packed;
	
	// -- Assignments
	generate
		for (i=0; i<C_S_AXIS_DATA_WIDTH/8; i=i+1) begin: _pack_data
			assign fifo_din_packed[9*(i+1)-1:9*i] = {fifo_din_strb[i], fifo_din[8*(i+1)-1:8*i]};
		end
  endgenerate
	
  // -- Modules and Logic
  fallthrough_small_fifo #(.WIDTH(C_S_AXIS_DATA_WIDTH+C_S_AXIS_TUSER_WIDTH+C_S_AXIS_DATA_WIDTH/8+1), .MAX_DEPTH_BITS(2))
    input_fifo_inst
      ( .din         ({s_axis_tlast, s_axis_tuser, s_axis_tstrb, s_axis_tdata}),
        .wr_en       (ififo_wr_en),
        .rd_en       (ififo_rd_en),
        .dout        ({ififo_tlast, ififo_tuser, ififo_tstrb, ififo_tdata}),
        .full        (),
        .prog_full   (),
        .nearly_full (ififo_nearly_full),
        .empty       (ififo_empty),
        .reset       (rst || sw_rst),
        .clk         (axi_aclk)
      );

  // ---- AXI (Side) State Machine [Combinational]
  always @ * begin
    next_state = state;

    s_axis_tready = !ififo_nearly_full /*&& !rst*/; //Note: needed only for correct simulation
    ififo_wr_en = s_axis_tready && s_axis_tvalid;
    ififo_rd_en = 0;

    fifo_din = ififo_tdata;
    fifo_din_strb = ififo_tstrb;
    fifo_wr_en = 0;

    case (state)
      WR_TUSER_BITS: begin // TDATA_WIDTH > TUSER_WIDTH
        if (!ififo_empty && !fifo_full) begin
          fifo_din = {{(C_S_AXIS_DATA_WIDTH-128){1'b0}}, ififo_tuser};
          fifo_din_strb = {(C_S_AXIS_DATA_WIDTH/8){1'b1}};
          fifo_wr_en = 1;

          next_state = WR_PKT_BITS;
        end
      end
      WR_PKT_BITS: begin
        if (!ififo_empty && !fifo_full) begin
          fifo_wr_en = 1;
          ififo_rd_en = 1;

          if (ififo_tlast)
            next_state = WR_TUSER_BITS;
        end
      end
    endcase
  end

  // ---- Primary State Machine [Sequential]
  always @ (posedge axi_aclk) begin
    if(rst || sw_rst) begin
      state <= WR_TUSER_BITS;
    end
    else begin
      state <= next_state;
    end
  end

  // --- Async FIFO
  xil_async_fifo #(.DIN_WIDTH(C_S_AXIS_PACKED_DATA_WIDTH), .DOUT_WIDTH(FIFO_DATA_WIDTH), .DEPTH(16))
    async_fifo_inst
      ( .din          (fifo_din_packed),
        .wr_en        (fifo_wr_en),
        .rd_en        (fifo_rd_en),
        .dout         (fifo_dout),
        .full         (fifo_full),
        .empty        (fifo_empty),
        .rst          (rst || sw_rst),
        .wr_clk       (axi_aclk),
        .rd_clk       (fifo_clk)
      );

endmodule

