% English chemistry-themed numerical smoke test
clc
disp('--- English Chemistry Test ---')

t = linspace(0, 20, 250);
k = 0.18;
C0 = 1.0;
C = C0 * exp(-k * t);
half_life = log(2) / k;

T = linspace(280, 360, 200);
A = 2.5e7;
Ea = 5.5e4;
R = 8.314;
inv_T = exp(-log(T));
kT = A * exp(-(Ea / R) * inv_T);

H = [1e-1 1e-3 1e-7 1e-11];
pH = -log10(H);
sample_id = [1 2 3 4];

disp('First-order half-life:')
disp(half_life)
disp('Representative pH values:')
disp(pH)

figure(10);
clf;
plot(t, C, 'b-');
title('First-Order Concentration Decay');
xlabel('Time');
ylabel('Concentration');
grid(True);

figure(11);
clf;
plot(T, kT, 'r-');
title('Arrhenius Rate Constant');
xlabel('Temperature (K)');
ylabel('k(T)');
grid(True);

figure(12);
clf;
plot(sample_id, pH, 'ko-');
title('Representative pH Values');
xlabel('Sample Index');
ylabel('pH');
grid(True);

disp('Chemistry test completed.')
