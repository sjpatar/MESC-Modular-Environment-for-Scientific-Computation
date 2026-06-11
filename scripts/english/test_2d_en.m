% English 2D plotting smoke test
clc
disp('--- English 2D Plot Test ---')

t = linspace(0, 2*pi, 400);
y1 = sin(t);
y2 = cos(t);

figure(1);
clf;
plot(t, y1, 'b-');
hold(True);
plot(t, y2, 'r--');
title('2D Trigonometric Curves');
xlabel('Angle (rad)');
ylabel('Amplitude');
legend('sin(t)', 'cos(t)');
grid(True);
hold(False);

figure(2);
clf;
[X, Y] = meshgrid(-2:0.25:2, -2:0.25:2);
U = -Y;
V = X;
quiver(X, Y, U, V);
title('2D Vector Field');
xlabel('x');
ylabel('y');
grid(True);

disp('2D plot test completed.')
