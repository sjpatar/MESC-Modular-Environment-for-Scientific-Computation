% English calculus and symbolic smoke test
clc
disp('--- English Calculus Test ---')

syms x
f = exp(-x/3) * sin(2*x);
df = diff(f, x);
F = int(f, x);
area_val = int(f, x, 0, pi);
limit_val = limit(sin(x)/x, x, 0);

sample_x = linspace(0, 2*pi, 200);
sample_y = sin(sample_x).^2;
trap_est = int(sin(x)^2, x, 0, 2*pi);

disp('Derivative:')
disp(df)
disp('Indefinite integral:')
disp(F)
disp('Definite integral from 0 to pi:')
disp(area_val)
disp('Limit of sin(x)/x as x -> 0:')
disp(limit_val)
disp('Integral of sin(x)^2 over [0, 2*pi]:')
disp(trap_est)

figure(7);
clf;
plot(sample_x, sample_y, 'b-');
title('Calculus Sample: sin(x)^2');
xlabel('x');
ylabel('sin(x)^2');
grid(True);

disp('Calculus test completed.')
