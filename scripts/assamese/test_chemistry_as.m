% অসমীয়া ৰসায়ন-ধর্মী সাংখ্যিক স্মোক টেষ্ট
মচিদিয়া
দেখুওৱা('--- অসমীয়া ৰসায়ন টেষ্ট ---')

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

দেখুওৱা('First-order half-life:')
দেখুওৱা(half_life)
দেখুওৱা('উদাহৰণ স্বৰূপ pH মানসমূহ:')
দেখুওৱা(pH)

figure(10);
clf;
আকা(t, C, 'b-');
শিৰোনামা('First-Order Concentration Decay');
xলেবেল('সময়');
yলেবেল('Concentration');
গ্ৰিড(True);

figure(11);
clf;
আকা(T, kT, 'r-');
শিৰোনামা('Arrhenius Rate Constant');
xলেবেল('Temperature (K)');
yলেবেল('k(T)');
গ্ৰিড(True);

figure(12);
clf;
আকা(sample_id, pH, 'ko-');
শিৰোনামা('উদাহৰণ স্বৰূপ pH মান');
xলেবেল('Sample Index');
yলেবেল('pH');
গ্ৰিড(True);

দেখুওৱা('ৰসায়ন টেষ্ট সম্পূৰ্ণ হ’ল।')
