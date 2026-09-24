module fa(
output sum,
output cout,
input a,
input b,
input cin
);
assign sum=a^b^cin;
assign cout=(a & b) | (b & cin) | (a & cin);
endmodule
