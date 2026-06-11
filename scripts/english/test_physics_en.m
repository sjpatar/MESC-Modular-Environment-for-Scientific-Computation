% English physics smoke test
clc
disp('--- English Physics Test ---')

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

disp('Speed of light (m/s):')
disp(c0)
disp('Reference damping ratio:')
disp(damping)
disp('Small-angle pendulum period for L = 1.5 m (s):')
disp(pendulum_period)
disp('451 F in Celsius:')
disp(temp_c)

figure(8);
clf;
plot(t, y, 'b-');
title('Damped Oscillation');
xlabel('Time (s)');
ylabel('Displacement');
grid(True);

figure(9);
clf;
[X, Y] = meshgrid(-2:0.4:2, -2:0.4:2);
U = -Y ./ (X.^2 + Y.^2 + 0.5);
V = X ./ (X.^2 + Y.^2 + 0.5);
quiver(X, Y, U, V);
title('Rotational Field');
xlabel('x');
ylabel('y');
grid(True);

disp('Physics test completed.')
