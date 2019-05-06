rawdata = readtable('./test/20190505_170223_sig/98fc11691fc5.csv');
data = table2array(rawdata(:, [1,2,4,5,9]));
unique_types = unique(data(:,5));

for j = 1:size(unique_types, 1)
    figure(j); clf;
    logistics = data(:,5) == unique_types(j);
    tmpdata = data(logistics, :);
    unique_xys = unique(tmpdata(:, 1:2), 'row');
    tmpdata_avg = [];
    for i = size(unique_xys, 1):-1:1
        xy_logistics = unique_xys(i, 1:2) == tmpdata(:, 1:2);
        xy_logistics = xy_logistics(:,1) & xy_logistics(:,2);
        tmpdata_avg(i, :) = [unique_xys(i, 1:2), mean(tmpdata(xy_logistics, 3:end), 1)];
    end
    scatter3(tmpdata_avg(:,1), tmpdata_avg(:,2), tmpdata_avg(:,3), 100, tmpdata_avg(:,4), '.');
    colorbar;
end