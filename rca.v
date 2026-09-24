module rca(s,c,a,b,cin);
input[4:0]a,b;
input cin;
output[4:0]s;
output c;
wire c0,c1,c2,c3;
fa g1(s[0],c0,a[0],b[0],cin);
fa g2(s[1],c1,a[1],b[1],c0);
fa g3(s[2],c2,a[2],b[2],c1);
fa g4(s[3],c3,a[3],b[3],c2);
fa g5(s[4],c,a[4],b[4],c3);
endmodule
