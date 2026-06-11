% অসমীয়া পদাৰ্থবিজ্ঞান স্মোক টেষ্ট
মচিদিয়া
দেখুওৱা('--- অসমীয়া পদাৰ্থবিজ্ঞান টেষ্ট ---')

g0 = g;
c0 = physconst('LightSpeed');
theta = 45 * pi / 180;
v0 = 25;
damping = 0.12;
omega = 4.0;
t = linspace(0, 12, 200);
y = exp(-damping * t) .* sin(omega * t);
pendulum_period = 2 * pi * sqrt(1.5 / g0);
temp_c = convtemp(451, 'F', 'C');

দেখুওৱা('আলোৰ বেগ (m/s):')
দেখুওৱা(c0)
দেখুওৱা('Reference damping ratio:')
দেখুওৱা(damping)
দেখুওৱা('L = 1.5 m হলে দোলকৰ কাল (s):')
দেখুওৱা(pendulum_period)
দেখুওৱা('451 F ৰ Celsius মান:')
দেখুওৱা(temp_c)

figure(8);
clf;
আকা(t, y, 'b-');
শিৰোনামা('Damped Oscillation');
xলেবেল('সময় (s)');
yলেবেল('Displacement');
গ্ৰিড(True);

figure(9);
clf;
[X, Y] = meshgrid(-2:0.4:2, -2:0.4:2);
U = -Y ./ (X.^2 + Y.^2 + 0.5);
V = X ./ (X.^2 + Y.^2 + 0.5);
quiver(X, Y, U, V);
শিৰোনামা('ঘূৰ্ণন ক্ষেত্ৰ');
xলেবেল('x');
yলেবেল('y');
গ্ৰিড(True);

দেখুওৱা('পদাৰ্থবিজ্ঞান টেষ্ট সম্পূৰ্ণ হ’ল।')
