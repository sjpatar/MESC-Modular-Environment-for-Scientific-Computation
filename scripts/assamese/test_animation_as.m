% অসমীয়া এনিমেচন স্মোক টেষ্ট
মচিদিয়া
দেখুওৱা('--- অসমীয়া এনিমেচন টেষ্ট ---')

t = linspace(0, 4*pi, 120);

figure(5);
clf;
h = animatedline('Color', 'g', 'LineWidth', 2);
বাবে k = 1:দৈৰ্ঘ্য(t)
    addpoints(h, t(k), sin(t(k)));
    drawnow;
সমাপ্ত
শিৰোনামা('এনিমেটেড সাইন গঠন');
xলেবেল('t');
yলেবেল('sin(t)');
গ্ৰিড(True);

figure(6);
clf;
comet3(sin(t), cos(t), t);
শিৰোনামা('Comet3 হেলিক্স');
xলেবেল('x');
yলেবেল('y');
zlabel('z');
গ্ৰিড(True);

দেখুওৱা('এনিমেচন টেষ্ট সম্পূৰ্ণ হ’ল।')
