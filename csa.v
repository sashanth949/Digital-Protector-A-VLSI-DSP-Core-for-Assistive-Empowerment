module csa(
    output [5:0] s,
    output cout,
    input  [3:0] a, b, c
);
    wire [3:0] sum, carry;

    // Stage 1: Parallel Full Adders
    fa fa1(sum[0], carry[0], a[0], b[0], c[0]);
    fa fa2(sum[1], carry[1], a[1], b[1], c[1]);
    fa fa3(sum[2], carry[2], a[2], b[2], c[2]);
    fa fa4(sum[3], carry[3], a[3], b[3], c[3]);

    // Stage 2: 5-Bit Ripple Carry Adder
    rca rca1(
        .s(s[4:0]), 
        .c(s[5]), 
        .a({1'b0, sum}), 
        .b({carry, 1'b0}), 
        .cin(1'b0)
    ); // <-- Added missing closing parenthesis and semicolon

    // Assign the top carry-out bit to cout
    assign cout = s[5];
endmodule
