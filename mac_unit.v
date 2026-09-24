`timescale 1ns/1ps
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 08.06.2026 14:41:47
// Design Name: 
// Module Name: mac_unit
// Project Name: 
// Target Devices: 
// Tool Versions: 
// Description: 
// 
// Dependencies: 
// 
// Revision:
// Revision 0.01 - File Created
// Additional Comments:
// 
//////////////////////////////////////////////////////////////////////////////////
module mac_unit (
    input  wire        clk,
    input  wire        rst_n,
    input  wire [3:0]  a,
    input  wire [3:0]  b,
    output reg  [11:0] accum_out
);

    // -------------------------------------------------
    // 1. Wallace Tree Multiplier
    // -------------------------------------------------
    wire [7:0] product;

    w_m multiplier_inst (
        .p (product),
        .a (a),
        .b (b)
    );

    // -------------------------------------------------
    // 2. CSA for lower 4 bits
    //    (your CSA already produces the full numeric sum)
    // -------------------------------------------------
    wire [5:0] csa_sum;
    wire       csa_cout;   // = csa_sum[5], can be left unused

    csa csa_inst (
        .s   (csa_sum),
        .cout(csa_cout),
        .a   (product[3:0]),
        .b   (accum_out[3:0]),
        .c   (4'b0000)
    );

    // -------------------------------------------------
    // 3. Reconstruct full 12-bit next value
    //    Because csa_sum is already a complete sum,
    //    we just add the higher parts + the whole csa_sum
    // -------------------------------------------------
    wire [11:0] next_accum;

    assign next_accum = {accum_out[11:4], 4'b0000}   // higher bits of accum
                      + {4'b0000, product[7:4], 4'b0000} // higher bits of product
                      + {6'b000000, csa_sum};           // full lower sum (incl. its carries)

    // -------------------------------------------------
    // 4. Sequential Accumulator
    // -------------------------------------------------
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            accum_out <= 12'b0;
        else
            accum_out <= next_accum;
    end

endmodule

