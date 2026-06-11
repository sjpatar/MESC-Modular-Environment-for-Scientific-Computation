% পৰীক্ষামূলক স্ক্ৰিপ্ট: ডাম্পড হাৰমনিক অচিলেটৰ (Damped Harmonic Oscillator)
মচিদিয়া
দেখুওৱা('বিজ্ঞান পৰীক্ষাগাৰলৈ স্বাগতম!')
ৰৈযোৱা(1)

% চলক আৰু মেট্ৰিক্স (Core Mathematics - Standard Notation)
t = linspace(0, 10, 500);
damping = 0.5;
frequency = 2;

% গাণিতিক সূত্ৰ (Mathematical Formula)
y = exp(-damping * t) .* sin(2 * pi * frequency * t);

% লেখচিত্ৰ অংকন (Plotting - Assamese Syntax)
আকা(t, y);
শিৰোনামা('ডাম্পড হাৰমনিক অচিলেটৰ (Damped Harmonic Oscillator)');
xলেবেল('সময় (ছেকেণ্ড)');
yলেবেল('প্ৰসাৰ (Amplitude)');
সংকেত('তৰংগ');
গ্ৰিড(True);

দেখুওৱা('লেখচিত্ৰ সফলতাৰে অংকন কৰা হৈছে।')