`timescale 1ns/1ps
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 15.02.2026 11:16:37
// Design Name: 
// Module Name: w_m
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
module w_m(
    output wire [7:0] p,   // Changed from reg to wire
    input [3:0] a,
    input [3:0] b
    // removed clk input since it's now purely combinational
);
    wire [6:1] s;
    wire [11:1] c;
    wire [14:0] x;
    wire [7:0] P_comb;

    // Direct assignment removes the clock cycle delay bottleneck
    assign p = P_comb;

    assign P_comb[0] = a[0] & b[0];
    assign x[0]  = a[0] & b[1];
    assign x[1]  = a[1] & b[0];
    assign x[2]  = a[0] & b[2];
    assign x[3]  = a[1] & b[1];
    assign x[4]  = a[2] & b[0];
    assign x[5]  = a[0] & b[3];
    assign x[6]  = a[1] & b[2];
    assign x[7]  = a[2] & b[1];
    assign x[8]  = a[3] & b[0];
    assign x[9]  = a[1] & b[3];
    assign x[10] = a[2] & b[2];
    assign x[11] = a[3] & b[1];
    assign x[12] = a[2] & b[3];
    assign x[13] = a[3] & b[2];
    assign x[14] = a[3] & b[3];

    ha ha1(s[1], c[1], x[8], x[7]);
    ha ha2(s[2], c[2], x[10], x[11]);
    ha ha3(s[3], c[3], x[3], x[4]);
    fa fa4(s[4], c[4], s[1], x[6], x[5]);
    fa fa5(s[5], c[5], c[1], s[2], x[9]);
    fa fa6(s[6], c[6], c[2], x[12], x[13]);
    ha ha7(P_comb[1], c[7], x[0], x[1]);
    fa fa8(P_comb[2], c[8], s[3], x[2], c[7]);
    fa fa9(P_comb[3], c[9], c[3], s[4], c[8]);
    fa fa10(P_comb[4], c[10], c[4], s[5], c[9]);
    fa fa11(P_comb[5], c[11], c[5], s[6], c[10]);
    fa fa12(P_comb[6], P_comb[7], c[6], x[14], c[11]);

endmodule

