% English 3D plotting smoke test
clc
disp('--- English 3D Plot Test ---')

t = linspace(0, 6*pi, 250);
x = sin(t);
y = cos(t);
z = t / (2*pi);

figure(3);
clf;
plot3(x, y, z, 'm-');
title('3D Helix');
xlabel('x');
ylabel('y');
zlabel('Turns');
grid(True);

figure(4);
clf;
[X, Y] = meshgrid(-3:0.2:3, -3:0.2:3);
R = sqrt(X.^2 + Y.^2) + 1e-6;
Z = sin(R) ./ R;
surf(X, Y, Z);
title('3D Surface');
xlabel('x');
ylabel('y');
zlabel('z');
colormap('jet');
grid(True);

disp('3D plot test completed.')
