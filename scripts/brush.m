% test_brush_selection.m
% Tests the Plotly backend's interactive scatter and 2-way data binding.

disp('Generating 150 data points across 3 clusters...');

% 1. Generate 3 distinct clusters of data
x1 = randn(50, 1) - 3; y1 = randn(50, 1) + 3;
x2 = randn(50, 1) + 3; y2 = randn(50, 1) + 3;
x3 = randn(50, 1);     y3 = randn(50, 1) - 3;

X = [x1; x2; x3];
Y = [y1; y2; y3];

% 2. Open a detached window to give the interactive plot maximum screen space
figure(2);

% 3. Draw the interactive scatter plot
% The Smart Router should automatically detect this and send it to plotly_backend.py
scatter(X, Y, 40, 'filled');

% 4. Format the plot
title('Data Clustering: Drag a rectangle to select points');
xlabel('Feature X');
ylabel('Feature Y');
grid on;

% 5. EXPLICITLY activate brush selection
% This tells Mathex to set the Plotly dragmode to 'select' (rectangle box)
brush on; 

disp('Plot ready!');
disp('ACTION: Click and drag a box over one of the clusters.');
disp('EXPECTED: The selected points should highlight, and your IDE Variable Inspector should update.');