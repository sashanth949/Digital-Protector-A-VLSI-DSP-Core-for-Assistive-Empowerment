`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 07.09.2026 06:14:08
// Design Name: 
// Module Name: tb_mac_unit_signed
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


module tb_mac_unit_signed;
    reg        clk;
    reg        rst_n;
    reg [3:0]  a;
    reg [3:0]  b;

    wire [11:0] accum_out;

    integer expected;
    integer errors;

    // -----------------------------------------------
    // DUT
    // -----------------------------------------------
    mac_unit_signed1 uut (
        .clk       (clk),
        .rst_n     (rst_n),
        .a         (a),
        .b         (b),
        .accum_out (accum_out)
    );

    // -----------------------------------------------
    // Clock: 10 ns period
    // -----------------------------------------------
    initial begin
        clk = 1'b0;
        forever #5 clk = ~clk;
    end

    // -----------------------------------------------
    // Test procedure
    // -----------------------------------------------
    initial begin

        errors   = 0;
        expected = 0;

        a = 4'b0000;
        b = 4'b0000;

        // -------------------------------------------
        // Reset
        // -------------------------------------------
        rst_n = 1'b0;

        #12;

        if (accum_out !== 12'b0) begin
            $display("ERROR: Reset failed. accum_out = %0d",
                     $signed(accum_out));
            errors = errors + 1;
        end
        else begin
            $display("PASS : Reset -> accum_out = 0");
        end

        rst_n = 1'b1;

        // -------------------------------------------
        // Test 1: 3 × 2 = +6
        // -------------------------------------------
        a = 4'b0011;
        b = 4'b0010;

        expected = expected + (3 * 2);

        @(posedge clk);
        #1;

        if ($signed(accum_out) !== expected) begin
            $display("ERROR: 3 x 2 -> Accum = %0d, Expected = %0d",
                     $signed(accum_out), expected);
            errors = errors + 1;
        end
        else begin
            $display("PASS : 3 x 2 -> Accum = %0d",
                     $signed(accum_out));
        end

        // -------------------------------------------
        // Test 2: -3 × 2 = -6
        // Accum = 6 - 6 = 0
        // -------------------------------------------
        a = 4'b1101;     // -3
        b = 4'b0010;     // +2

        expected = expected + (-3 * 2);

        @(posedge clk);
        #1;

        if ($signed(accum_out) !== expected) begin
            $display("ERROR: -3 x 2 -> Accum = %0d, Expected = %0d",
                     $signed(accum_out), expected);
            errors = errors + 1;
        end
        else begin
            $display("PASS : -3 x 2 -> Accum = %0d",
                     $signed(accum_out));
        end

        // -------------------------------------------
        // Test 3: -2 × -3 = +6
        // Accum = 0 + 6 = 6
        // -------------------------------------------
        a = 4'b1110;     // -2
        b = 4'b1101;     // -3

        expected = expected + (-2 * -3);

        @(posedge clk);
        #1;

        if ($signed(accum_out) !== expected) begin
            $display("ERROR: -2 x -3 -> Accum = %0d, Expected = %0d",
                     $signed(accum_out), expected);
            errors = errors + 1;
        end
        else begin
            $display("PASS : -2 x -3 -> Accum = %0d",
                     $signed(accum_out));
        end

        // -------------------------------------------
        // Test 4: 4 × -2 = -8
        // Accum = 6 - 8 = -2
        // -------------------------------------------
        a = 4'b0100;     // +4
        b = 4'b1110;     // -2

        expected = expected + (4 * -2);

        @(posedge clk);
        #1;

        if ($signed(accum_out) !== expected) begin
            $display("ERROR: 4 x -2 -> Accum = %0d, Expected = %0d",
                     $signed(accum_out), expected);
            errors = errors + 1;
        end
        else begin
            $display("PASS : 4 x -2 -> Accum = %0d",
                     $signed(accum_out));
        end

        // -------------------------------------------
        // Test 5: -4 × -4 = +16
        // Accum = -2 + 16 = 14
        // -------------------------------------------
        a = 4'b1100;     // -4
        b = 4'b1100;     // -4

        expected = expected + (-4 * -4);

        @(posedge clk);
        #1;

        if ($signed(accum_out) !== expected) begin
            $display("ERROR: -4 x -4 -> Accum = %0d, Expected = %0d",
                     $signed(accum_out), expected);
            errors = errors + 1;
        end
        else begin
            $display("PASS : -4 x -4 -> Accum = %0d",
                     $signed(accum_out));
        end

        // -------------------------------------------
        // Test 6: -8 × 7 = -56
        // Accum = 14 - 56 = -42
        // -------------------------------------------
        a = 4'b1000;     // -8
        b = 4'b0111;     // +7

        expected = expected + (-8 * 7);

        @(posedge clk);
        #1;

        if ($signed(accum_out) !== expected) begin
            $display("ERROR: -8 x 7 -> Accum = %0d, Expected = %0d",
                     $signed(accum_out), expected);
            errors = errors + 1;
        end
        else begin
            $display("PASS : -8 x 7 -> Accum = %0d",
                     $signed(accum_out));
        end

        // -------------------------------------------
        // Test 7: 7 × 7 = +49
        // Accum = -42 + 49 = 7
        // -------------------------------------------
        a = 4'b0111;     // +7
        b = 4'b0111;     // +7

        expected = expected + (7 * 7);

        @(posedge clk);
        #1;

        if ($signed(accum_out) !== expected) begin
            $display("ERROR: 7 x 7 -> Accum = %0d, Expected = %0d",
                     $signed(accum_out), expected);
            errors = errors + 1;
        end
        else begin
            $display("PASS : 7 x 7 -> Accum = %0d",
                     $signed(accum_out));
        end

        // -------------------------------------------
        // Final result
        // -------------------------------------------
        $display("==============================================");

        if (errors == 0)
            $display("ALL MAC TESTS PASSED!");
        else
            $display("MAC TEST FAILED! Number of errors = %0d",
                     errors);

        $display("Final Accumulator = %0d",
                 $signed(accum_out));

        $display("==============================================");

        #20;
        $finish;

    end

endmodule
