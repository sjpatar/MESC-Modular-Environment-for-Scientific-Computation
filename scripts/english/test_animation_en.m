% English animation smoke test
clc
disp('--- English Animation Test ---')

t = linspace(0, 4*pi, 120);

figure(5);
clf;
h = animatedline('Color', 'g', 'LineWidth', 2);
for k = 1:length(t)
    addpoints(h, t(k), sin(t(k)));
    drawnow;
end
title('Animated Sine Build-Up');
xlabel('t');
ylabel('sin(t)');
grid(True);

figure(6);
clf;
comet3(sin(t), cos(t), t);
title('Comet3 Helix');
xlabel('x');
ylabel('y');
zlabel('z');
grid(True);

disp('Animation test completed.')
