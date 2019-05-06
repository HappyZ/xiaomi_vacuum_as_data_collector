rawdata = readtable('./example/20190505_170223_sig/98fc11691fc5.csv');
data = table2array(rawdata(:, [1,2,4,5,9]));
unique_types = unique(data(:,5));

figure(1); clf;
for j = 1:size(unique_types, 1)
    logistics = data(:,5) == unique_types(j);
    tmpdata = data(logistics, :);
    unique_xys = unique(tmpdata(:, 1:2), 'row');
    tmpdata_avg = [];
    for i = size(unique_xys, 1):-1:1
        xy_logistics = unique_xys(i, 1:2) == tmpdata(:, 1:2);
        xy_logistics = xy_logistics(:,1) & xy_logistics(:,2);
        tmpdata_avg(i, :) = [unique_xys(i, 1:2), mean(tmpdata(xy_logistics, 3:end), 1)];
    end
    ax1 = subplot(size(unique_types, 1), 2, 2 * j - 1);
    scatter3(tmpdata_avg(:,1), tmpdata_avg(:,2), tmpdata_avg(:,3), 100, tmpdata_avg(:,4), '.');
    caxis([-85, -20]); view([0, 90]);
    xlabel('loc x (m)'); ylabel('loc y (m)'); zlabel('time (s)'); 
    title(['packet type: ', num2str(unique_types(j))])
    ax2 = subplot(size(unique_types, 1), 2, 2 * j);
    scatter3(tmpdata_avg(:,1), tmpdata_avg(:,2), tmpdata_avg(:,4), 100, tmpdata_avg(:,4), '.');
    caxis([-85, -20]);
    xlabel('loc x (m)'); ylabel('loc y (m)'); zlabel('RSS (dB)'); 
    title(['packet type: ', num2str(unique_types(j))])
    colorbar;
end